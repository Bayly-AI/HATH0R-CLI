# syntax=docker/dockerfile:1
# ------------------------------------------------------------------------------
# Stage 1: Build & Dependencies
# ------------------------------------------------------------------------------
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements*.txt pyproject.toml* README.md* ./
COPY src ./src
RUN if [ -f requirements.txt ]; then \
        pip install --prefix=/install -r requirements.txt; \
    fi && \
    if [ -f pyproject.toml ]; then \
        pip install --prefix=/install .; \
    fi

# ------------------------------------------------------------------------------
# Stage 2: Hardened Non-Root Runtime
# ------------------------------------------------------------------------------
FROM python:3.11-slim AS runner

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/install/bin:$PATH" \
    PYTHONPATH="/app/src:/install/lib/python3.11/site-packages"

# Create dedicated non-root user (UID/GID 10001)
RUN groupadd -g 10001 hath0r && \
    useradd -u 10001 -g hath0r -s /bin/sh -m hath0r

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /install

# Copy application source code with non-root ownership
COPY --chown=hath0r:hath0r . /app

# Switch to non-root user
USER 10001:10001

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD ["hath0r", "--version"]

ENTRYPOINT ["hath0r"]
CMD ["--help"]
