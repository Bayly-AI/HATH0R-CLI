"""Container hardening and multi-stage Dockerfile scaffolding."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, Optional


class ContainerScaffolder:
    """Scaffolds hardened multi-stage Dockerfiles adhering to CR-IAC-001."""

    DOCKERIGNORE_CONTENT = """# Git and version control
.git/
.gitignore
.gitattributes

# Environment and secrets
.env*
*.pem
*.key
.credentials/

# Python artifacts
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
.venv/
venv/
env/
.pytest_cache/
.coverage
htmlcov/
dist/
build/
*.egg-info/

# Node / Web artifacts
node_modules/
.npm/
.yarn/
.next/
out/
.cache/

# OS artifacts
.DS_Store
Thumbs.db
"""

    PYTHON_DOCKERFILE_TEMPLATE = """# syntax=docker/dockerfile:1
# ------------------------------------------------------------------------------
# Stage 1: Build & Dependencies
# ------------------------------------------------------------------------------
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \\
    PYTHONUNBUFFERED=1 \\
    PIP_NO_CACHE_DIR=1 \\
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \\
    build-essential \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

COPY requirements*.txt pyproject.toml* ./
RUN if [ -f requirements.txt ]; then \\
        pip install --prefix=/install -r requirements.txt; \\
    elif [ -f pyproject.toml ]; then \\
        pip install --prefix=/install .; \\
    fi

# ------------------------------------------------------------------------------
# Stage 2: Hardened Non-Root Runtime
# ------------------------------------------------------------------------------
FROM python:3.11-slim AS runner

ENV PYTHONDONTWRITEBYTECODE=1 \\
    PYTHONUNBUFFERED=1 \\
    PATH="/install/bin:$PATH" \\
    PYTHONPATH="/install/lib/python3.11/site-packages:$PYTHONPATH"

# Create dedicated non-root user (UID/GID 10001)
RUN groupadd -g 10001 hath0r && \\
    useradd -u 10001 -g hath0r -s /bin/sh -m hath0r

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /install

# Copy application source code with non-root ownership
COPY --chown=hath0r:hath0r . /app

# Switch to non-root user
USER 10001:10001

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \\
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health').read()" || exit 1

ENTRYPOINT ["python3", "-m", "{entrypoint}"]
"""

    NODE_DOCKERFILE_TEMPLATE = """# syntax=docker/dockerfile:1
# ------------------------------------------------------------------------------
# Stage 1: Build & Bundle
# ------------------------------------------------------------------------------
FROM node:20-alpine AS builder

WORKDIR /build

RUN apk add --no-cache libc6-compat

COPY package*.json yarn.lock* pnpm-lock.yaml* ./
RUN if [ -f package-lock.json ]; then \\
        npm ci; \\
    else \\
        npm install; \\
    fi

COPY . .
RUN npm run build || true

# ------------------------------------------------------------------------------
# Stage 2: Hardened Non-Root Runtime
# ------------------------------------------------------------------------------
FROM node:20-alpine AS runner

ENV NODE_ENV=production \\
    PORT=3000

# Create dedicated non-root user (UID/GID 10001)
RUN addgroup -g 10001 -S hath0r && \\
    adduser -u 10001 -S hath0r -G hath0r

WORKDIR /app

COPY --from=builder --chown=hath0r:hath0r /build/package*.json ./
COPY --from=builder --chown=hath0r:hath0r /build/dist ./dist 2>/dev/null || true
COPY --from=builder --chown=hath0r:hath0r /build/build ./build 2>/dev/null || true
COPY --from=builder --chown=hath0r:hath0r /build/node_modules ./node_modules

USER 10001:10001

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \\
    CMD wget --no-verbose --tries=1 --spider http://127.0.0.1:3000/ || exit 1

CMD ["node", "dist/index.js"]
"""

    STATIC_DOCKERFILE_TEMPLATE = """# syntax=docker/dockerfile:1
# ------------------------------------------------------------------------------
# Hardened Static Web Server (Nginx Unprivileged)
# ------------------------------------------------------------------------------
FROM nginxinc/nginx-unprivileged:alpine-slim AS runner

USER 10001:10001

WORKDIR /usr/share/nginx/html

COPY --chown=10001:10001 . /usr/share/nginx/html

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \\
    CMD wget --no-verbose --tries=1 --spider http://127.0.0.1:8080/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
"""

    def detect_tech_stack(self, workspace: Path) -> str:
        """Detect the primary technology stack of a repository."""
        workspace = Path(workspace)
        if (workspace / "requirements.txt").exists() or (workspace / "pyproject.toml").exists() or list(workspace.glob("*.py")):
            return "python"
        if (workspace / "package.json").exists() or (workspace / "vite.config.ts").exists() or (workspace / "vite.config.js").exists():
            return "node"
        if (workspace / "go.mod").exists():
            return "go"
        if (workspace / "index.html").exists():
            return "static"
        return "python"

    def scaffold(
        self,
        workspace: Path,
        tech_stack: Optional[str] = None,
        entrypoint: Optional[str] = None,
        overwrite: bool = False,
    ) -> Dict[str, Any]:
        """Scaffold hardened Dockerfile and .dockerignore in the workspace."""
        workspace = Path(workspace)
        workspace.mkdir(parents=True, exist_ok=True)

        if not tech_stack:
            tech_stack = self.detect_tech_stack(workspace)

        entrypoint = entrypoint or workspace.name.replace("-", "_")

        dockerfile_path = workspace / "Dockerfile"
        dockerignore_path = workspace / ".dockerignore"

        files_written = []

        # Scaffolding Dockerfile
        if not dockerfile_path.exists() or overwrite:
            if tech_stack == "python":
                content = self.PYTHON_DOCKERFILE_TEMPLATE.format(entrypoint=entrypoint)
            elif tech_stack == "node":
                content = self.NODE_DOCKERFILE_TEMPLATE
            elif tech_stack == "static":
                content = self.STATIC_DOCKERFILE_TEMPLATE
            else:
                content = self.PYTHON_DOCKERFILE_TEMPLATE.format(entrypoint=entrypoint)

            dockerfile_path.write_text(content)
            files_written.append("Dockerfile")

        # Scaffolding .dockerignore
        if not dockerignore_path.exists() or overwrite:
            dockerignore_path.write_text(self.DOCKERIGNORE_CONTENT)
            files_written.append(".dockerignore")

        return {
            "workspace": str(workspace),
            "tech_stack": tech_stack,
            "files_written": files_written,
            "has_dockerfile": dockerfile_path.exists(),
            "has_dockerignore": dockerignore_path.exists(),
        }

    def audit_dockerfile(self, workspace: Path) -> Dict[str, Any]:
        """Audit an existing Dockerfile for security hardening and multi-stage syntax."""
        dockerfile_path = Path(workspace) / "Dockerfile"
        if not dockerfile_path.exists():
            return {
                "exists": False,
                "multi_stage": False,
                "non_root": False,
                "has_healthcheck": False,
                "compliant": False,
                "findings": ["Dockerfile is missing."],
            }

        content = dockerfile_path.read_text()
        from_matches = re.findall(r"^FROM\s+", content, re.MULTILINE | re.IGNORECASE)
        multi_stage = len(from_matches) >= 2 or "AS " in content.upper()

        user_match = re.search(r"^USER\s+(\w+|\d+)", content, re.MULTILINE | re.IGNORECASE)
        non_root = False
        if user_match:
            val = user_match.group(1).lower()
            if val not in ("root", "0"):
                non_root = True

        has_healthcheck = bool(re.search(r"^HEALTHCHECK\s+", content, re.MULTILINE | re.IGNORECASE))

        findings = []
        if not multi_stage:
            findings.append("Single-stage build detected. Multi-stage build is required.")
        if not non_root:
            findings.append("Container runs as root (0). Non-root user (e.g. UID 10001) required.")
        if not has_healthcheck:
            findings.append("Missing HEALTHCHECK directive.")

        return {
            "exists": True,
            "multi_stage": multi_stage,
            "non_root": non_root,
            "has_healthcheck": has_healthcheck,
            "compliant": multi_stage and non_root and has_healthcheck,
            "findings": findings,
        }
