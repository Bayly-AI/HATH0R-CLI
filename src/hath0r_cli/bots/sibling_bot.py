"""Sibling Manager Bot: detect, download, and install suite sibling repositories."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, cast

from hath0r_cli.common import _cli_repo_root, _group_root

Runner = Callable[..., Tuple[int, str, str]]
HttpGet = Callable[[str, Dict[str, str]], bytes]


def _default_runner(cmd: List[str], cwd: Optional[Path] = None, timeout: int = 120) -> Tuple[int, str, str]:
    """Execute command in child subprocess."""
    proc = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _default_http_get(url: str, headers: Dict[str, str]) -> bytes:
    """HTTP GET via standard library."""
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=10) as resp:
        return cast(bytes, resp.read())


SUITE_SIBLINGS: Dict[str, Dict[str, Any]] = {
    "hath0r-atc": {
        "product_id": "hath0r-atc",
        "name": "HATH0R ATC",
        "repo": "Bayly-AI/HATH0R-ATC",
        "default_dir": "hath0r-atc",
        "aliases": ["atc", "hathor-atc", "HATH0R-ATC"],
        "role": "control-tower-infrastructure",
        "description": "OpenSource Project control tower for infrastructure, observation, and Docker-group membership.",
        "canonical": True,
        "is_python": False,
        "bootstrap_cmd": ["./bin/hath0r-bootstrap.sh"],
        "has_container": True,
        "container_name": "hath0r-nginx",
        "compose_file": "deploy/docker/docker-compose.yml",
        "default_image": "nginx:1.27-alpine",
        "build_cmd": ["docker", "compose", "-f", "deploy/docker/docker-compose.yml", "up", "-d", "redis", "nginx", "phoenix", "mlflow"],
    },
    "hath0r-mcp": {
        "product_id": "hath0r-mcp",
        "name": "HATH0R MCP",
        "repo": "Bayly-AI/HATH0R-MCP",
        "default_dir": "hath0r-mcp",
        "aliases": ["mcp", "hathor-mcp", "HATH0R-MCP"],
        "role": "mcp-knowledge-server",
        "description": "Standalone Model Context Protocol knowledge engine and tools server.",
        "canonical": True,
        "is_python": True,
        "bootstrap_cmd": [sys.executable, "-m", "pip", "install", "-e", "."],
        "has_container": True,
        "container_name": "hath0r-mcp",
        "compose_file": "docker-compose.yml",
        "default_image": "hath0r/mcp:local",
        "build_cmd": ["docker", "compose", "up", "-d", "--build", "--wait", "hath0r-mcp"],
    },
    "hath0r-framework": {
        "product_id": "hath0r-framework",
        "name": "HATHOR Framework",
        "repo": "Bayly-AI/HATH0R-Agentic-Framework",
        "default_dir": "hath0r",
        "aliases": ["framework", "hath0r", "hath0r-framework"],
        "role": "agentic-application-framework",
        "description": "Agentic application framework and OpenSource documentation corpus.",
        "canonical": True,
        "is_python": True,
        "bootstrap_cmd": [sys.executable, "-m", "pip", "install", "-e", "."],
    },
    "hath0r-poc": {
        "product_id": "hath0r-poc",
        "name": "HATHOR POC",
        "repo": "Bayly-AI/HATH0R-Agentic-POC",
        "default_dir": "hath0r-poc",
        "aliases": ["poc", "hathor-poc"],
        "role": "integration-test-bed",
        "description": "Archived optional test fixture.",
        "canonical": False,
        "is_python": False,
    },
}


@dataclass
class SiblingManagerBot:
    """Detects, inspects, downloads, and installs suite sibling repositories."""

    group_root: Optional[Path] = None
    runner: Runner = field(default=_default_runner)
    http_get: HttpGet = field(default=_default_http_get)

    def resolve_group_root(self) -> Path:
        """Resolve the group root directory containing sibling checkouts."""
        if self.group_root:
            return self.group_root.resolve()
        try:
            return _group_root()
        except Exception:
            # Fallback to parent of hath0r-cli repository
            return _cli_repo_root().parent.resolve()

    def resolve_product_spec(self, product_or_alias: str) -> Optional[Dict[str, Any]]:
        """Resolve a product ID or alias to its canonical suite specification."""
        key = (product_or_alias or "").strip().lower()
        if key in SUITE_SIBLINGS:
            return dict(SUITE_SIBLINGS[key])
        for spec in SUITE_SIBLINGS.values():
            if key == spec["product_id"].lower():
                return dict(spec)
            for alias in spec.get("aliases", []):
                if key == alias.lower():
                    return dict(spec)
        return None

    def locate_sibling(self, product_id: str, group_root: Optional[Path] = None) -> Optional[Path]:
        """Locate a sibling repository directory if it exists."""
        root = group_root or self.resolve_group_root()
        spec = self.resolve_product_spec(product_id)
        if not spec:
            return None

        candidates = [spec["default_dir"], *spec.get("aliases", [])]
        for name in candidates:
            candidate_path = root / name
            if candidate_path.is_dir():
                return cast(Path, candidate_path)
        return None

    def get_local_version(self, path: Path) -> Optional[str]:
        """Read version string from VERSION file or pyproject.toml."""
        v_file = path / "VERSION"
        if v_file.is_file():
            try:
                ver = v_file.read_text(encoding="utf-8").strip()
                if ver:
                    return ver
            except OSError:
                pass

        pyproject = path / "pyproject.toml"
        if pyproject.is_file():
            try:
                content = pyproject.read_text(encoding="utf-8")
                match = re.search(r'^version\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
                if match:
                    return match.group(1).strip()
            except OSError:
                pass

        return None

    def get_remote_latest_version(self, repo: str) -> Optional[str]:
        """Fetch latest release tag from GitHub API."""
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "HATH0R-CLI-SiblingManagerBot",
        }
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"

        # 1. Try releases/latest
        try:
            url = f"https://api.github.com/repos/{repo}/releases/latest"
            raw = self.http_get(url, headers)
            data = json.loads(raw.decode("utf-8"))
            tag = data.get("tag_name")
            if tag:
                return str(tag)
        except Exception:
            pass

        # 2. Fallback to tags list
        try:
            url = f"https://api.github.com/repos/{repo}/tags"
            raw = self.http_get(url, headers)
            data = json.loads(raw.decode("utf-8"))
            if isinstance(data, list) and data:
                tag = data[0].get("name")
                if tag:
                    return str(tag)
        except Exception:
            pass

        return None

    def scan_siblings(
        self,
        group_root: Optional[Path] = None,
        check_remote: bool = False,
    ) -> Dict[str, Any]:
        """Inspect all suite siblings for presence and versions."""
        root = group_root or self.resolve_group_root()
        products = {}
        all_canonical_present = True

        for pid, spec in SUITE_SIBLINGS.items():
            loc = self.locate_sibling(pid, root)
            present = loc is not None
            if spec.get("canonical") and not present:
                all_canonical_present = False

            local_ver = self.get_local_version(loc) if loc else None
            remote_ver = self.get_remote_latest_version(spec["repo"]) if check_remote else None

            products[pid] = {
                "product_id": pid,
                "name": spec["name"],
                "role": spec["role"],
                "canonical": spec["canonical"],
                "repo": spec["repo"],
                "present": present,
                "path": str(loc) if loc else str(root / spec["default_dir"]),
                "local_version": local_ver,
                "remote_version": remote_ver,
            }

        return {
            "group_root": str(root),
            "all_canonical_present": all_canonical_present,
            "products": products,
        }

    def download_and_install(
        self,
        product_or_alias: str,
        group_root: Optional[Path] = None,
        version: Optional[str] = None,
        install_dependencies: bool = True,
    ) -> Dict[str, Any]:
        """Download latest release/repo from GitHub and install as a sibling of CLI."""
        spec = self.resolve_product_spec(product_or_alias)
        if not spec:
            return {
                "success": False,
                "error": f"Unknown product or alias '{product_or_alias}'.",
                "known_products": list(SUITE_SIBLINGS.keys()),
            }

        root = group_root or self.resolve_group_root()
        target_dir = root / spec["default_dir"]

        # Check if already present
        existing = self.locate_sibling(spec["product_id"], root)
        if existing:
            loc_ver = self.get_local_version(existing)
            return {
                "success": True,
                "already_installed": True,
                "product_id": spec["product_id"],
                "name": spec["name"],
                "path": str(existing),
                "version": loc_ver,
                "message": f"{spec['name']} is already installed at {existing} (v{loc_ver or 'unknown'}).",
            }

        # 1. Determine tag/version to download
        remote_tag = version
        if not remote_tag:
            remote_tag = self.get_remote_latest_version(spec["repo"])

        # 2. Clone repository
        repo_url = f"https://github.com/{spec['repo']}.git"
        clone_cmd = ["git", "clone"]
        if remote_tag:
            clone_cmd.extend(["--branch", remote_tag, "--depth", "1"])
        clone_cmd.extend([repo_url, str(target_dir)])

        rc, stdout, stderr = self.runner(clone_cmd, cwd=root)
        if rc != 0:
            # Fallback: clone without branch/tag restriction (e.g. if tag format differed)
            fallback_cmd = ["git", "clone", repo_url, str(target_dir)]
            rc, stdout, stderr = self.runner(fallback_cmd, cwd=root)
            if rc != 0:
                return {
                    "success": False,
                    "error": f"Failed to clone {spec['repo']}: {stderr.strip() or stdout.strip()}",
                    "cmd": clone_cmd,
                }

        # 3. Post-clone installation
        installed_deps = False
        install_output = ""
        if install_dependencies and target_dir.is_dir():
            # If python package and pyproject.toml present: pip install -e .
            if spec.get("is_python") and (target_dir / "pyproject.toml").is_file():
                inst_cmd = [sys.executable, "-m", "pip", "install", "-e", "."]
                irc, iout, ierr = self.runner(inst_cmd, cwd=target_dir)
                installed_deps = (irc == 0)
                install_output = iout if irc == 0 else ierr

            # If bootstrap script present
            bootstrap_script = target_dir / "bin" / "hath0r-bootstrap.sh"
            if bootstrap_script.is_file() and os.access(bootstrap_script, os.X_OK):
                brc, bout, berr = self.runner(["./bin/hath0r-bootstrap.sh"], cwd=target_dir)
                if brc == 0:
                    installed_deps = True
                    install_output += f"\n{bout}"

        # 4. Verify installation
        installed_version = self.get_local_version(target_dir)

        return {
            "success": True,
            "installed": True,
            "already_installed": False,
            "product_id": spec["product_id"],
            "name": spec["name"],
            "path": str(target_dir),
            "version": installed_version or remote_tag or "unknown",
            "installed_deps": installed_deps,
            "install_output": install_output.strip(),
            "message": f"Successfully downloaded and installed {spec['name']} at {target_dir}.",
        }

    def ensure_siblings(
        self,
        group_root: Optional[Path] = None,
        product_ids: Optional[List[str]] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Ensure that requested or canonical siblings are downloaded and installed."""
        root = group_root or self.resolve_group_root()
        target_ids = product_ids or ["hath0r-atc", "hath0r-mcp"]

        results = []
        all_ok = True

        for pid in target_ids:
            spec = self.resolve_product_spec(pid)
            if not spec:
                all_ok = False
                results.append({"product_id": pid, "success": False, "error": f"Unknown product '{pid}'"})
                continue

            existing = self.locate_sibling(spec["product_id"], root)
            if existing:
                loc_ver = self.get_local_version(existing)
                results.append({
                    "product_id": spec["product_id"],
                    "name": spec["name"],
                    "success": True,
                    "action": "already_present",
                    "path": str(existing),
                    "version": loc_ver,
                })
            else:
                if dry_run:
                    results.append({
                        "product_id": spec["product_id"],
                        "name": spec["name"],
                        "success": True,
                        "action": "would_install",
                        "path": str(root / spec["default_dir"]),
                        "repo": spec["repo"],
                    })
                else:
                    res = self.download_and_install(spec["product_id"], group_root=root)
                    if not res.get("success"):
                        all_ok = False
                    results.append(res)

        return {
            "success": all_ok,
            "dry_run": dry_run,
            "group_root": str(root),
            "results": results,
        }

    def install_container(
        self,
        product_key: str,
        container_url: Optional[str] = None,
        group_root: Optional[Path] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Install or run container for product.

        If container_url is provided, pulls and tags the remote container image.
        If container_url is None or empty, builds and installs locally from the latest git version.
        """
        root = group_root or self.resolve_group_root()
        spec = self.resolve_product_spec(product_key)
        if not spec:
            return {"success": False, "error": f"Unknown product '{product_key}'"}

        if not spec.get("has_container"):
            return {
                "success": False,
                "error": f"Product '{spec['name']}' does not define container deployment support.",
            }

        target_dir = self.locate_sibling(spec["product_id"], root)
        if not target_dir or not target_dir.is_dir():
            if dry_run:
                target_dir = root / spec["default_dir"]
            else:
                dl_res = self.download_and_install(spec["product_id"], group_root=root)
                if not dl_res.get("success"):
                    return {
                        "success": False,
                        "error": f"Failed to acquire repository for container setup: {dl_res.get('error')}",
                    }
                target_dir = Path(dl_res["path"])

        container_name = spec.get("container_name", spec["product_id"])
        default_image = spec.get("default_image", f"{spec['product_id']}:local")

        # 1. Operator supplied container URL
        if container_url and container_url.strip():
            url = container_url.strip()
            if dry_run:
                return {
                    "success": True,
                    "dry_run": True,
                    "product_id": spec["product_id"],
                    "name": spec["name"],
                    "source": "remote_url",
                    "container_url": url,
                    "container_name": container_name,
                    "action": f"Would pull {url} and start container {container_name}",
                }

            prc, pout, perr = self.runner(["docker", "pull", url])
            if prc != 0:
                return {
                    "success": False,
                    "error": f"Failed to pull container image '{url}': {perr or pout}",
                }

            # Tag remote image to expected local image name
            self.runner(["docker", "tag", url, default_image])

            # Start container via compose without local build
            raw_cmd = list(spec.get("build_cmd", ["docker", "compose", "up", "-d"]))
            run_cmd = [arg for arg in raw_cmd if arg not in ("--build", "build")]
            rrc, rout, rerr = self.runner(run_cmd, cwd=target_dir)
            if rrc != 0:
                return {
                    "success": False,
                    "error": f"Failed to start container with image '{url}': {rerr or rout}",
                }

            return {
                "success": True,
                "product_id": spec["product_id"],
                "name": spec["name"],
                "source": "remote_url",
                "container_url": url,
                "image": default_image,
                "container_name": container_name,
                "message": f"Successfully pulled {url} and started container {container_name}.",
            }

        # 2. Operator cannot supply container URL -> install locally from latest git version
        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "product_id": spec["product_id"],
                "name": spec["name"],
                "source": "local_git_build",
                "container_name": container_name,
                "action": f"Would build locally from latest git repository at {target_dir}",
            }

        build_cmd = spec.get("build_cmd", ["docker", "compose", "up", "-d", "--build"])
        brc, bout, berr = self.runner(build_cmd, cwd=target_dir)
        if brc != 0:
            return {
                "success": False,
                "error": f"Failed to build and start container locally: {berr or bout}",
                "output": bout,
            }

        irc, iout, _ = self.runner(
            [
                "docker",
                "inspect",
                "-f",
                "health={{if .State.Health}}{{.State.Health.Status}}{{else}}n/a{{end}} status={{.State.Status}}",
                container_name,
            ]
        )
        status_str = iout.strip() if irc == 0 else "running"

        return {
            "success": True,
            "product_id": spec["product_id"],
            "name": spec["name"],
            "source": "local_git_build",
            "image": default_image,
            "container_name": container_name,
            "status": status_str,
            "output": bout.strip(),
            "message": f"Successfully built and started {container_name} locally from latest git version.",
        }

