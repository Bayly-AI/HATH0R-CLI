"""IaCManagingBot: Orchestrates Infrastructure as Code, Container Hardening, Salting & EKS Fargate."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from hath0r_cli.iac.container_scaffolder import ContainerScaffolder
from hath0r_cli.iac.fargate_generator import FargateGenerator
from hath0r_cli.iac.salting_coordinator import SaltingCoordinator


class IaCManagingBot:
    """Managing bot governing repository infrastructure compliance, containerization, salting, and EKS Fargate."""

    def __init__(self, workspace: Optional[Path] = None) -> None:
        self.workspace = Path(workspace) if workspace else Path.cwd()
        self.scaffolder = ContainerScaffolder()
        self.salter = SaltingCoordinator(self.workspace)
        self.fargate = FargateGenerator()

    def audit_workspace(self, path: Optional[Path] = None, sweep: bool = False) -> Dict[str, Any]:
        """Audit single workspace or sweep entire directory tree for IaC compliance."""
        root = Path(path) if path else self.workspace

        if sweep:
            repos: List[Dict[str, Any]] = []
            for cur_root, dirs, files in os.walk(root):
                # Prune non-project trees
                dirs[:] = [
                    d for d in dirs
                    if d not in ('.git', 'node_modules', '.venv', 'venv', 'target', 'dist', 'build', '.next', '.cache', 'ARCHIVE')
                ]
                rel = os.path.relpath(cur_root, root)
                if os.path.exists(os.path.join(cur_root, '.git')) and rel != '.':
                    repo_audit = self._audit_single_repo(Path(cur_root))
                    repo_audit["relative_path"] = rel
                    repos.append(repo_audit)

            total = len(repos)
            compliant_count = sum(1 for r in repos if r["compliant"])
            return {
                "sweep": True,
                "root": str(root),
                "total_repos": total,
                "compliant_repos": compliant_count,
                "non_compliant_repos": total - compliant_count,
                "compliance_rate": (compliant_count / total) if total > 0 else 1.0,
                "repositories": repos,
            }

        # Single repo audit
        single_res = self._audit_single_repo(root)
        single_res["sweep"] = False
        return single_res

    def _audit_single_repo(self, repo_path: Path) -> Dict[str, Any]:
        """Audit a single repository across Container, Salting, and Fargate pillars."""
        docker_res = self.scaffolder.audit_dockerfile(repo_path)
        salting_res = self.salter.audit_salting(repo_path)
        fargate_res = self.fargate.audit_fargate(repo_path)

        compliant = (
            docker_res.get("compliant", False)
            and salting_res.get("compliant", False)
            and fargate_res.get("compliant", False)
        )

        score = 0.0
        if docker_res.get("compliant"):
            score += 0.34
        elif docker_res.get("exists"):
            score += 0.15

        if salting_res.get("compliant"):
            score += 0.33
        elif salting_res.get("is_salted"):
            score += 0.15

        if fargate_res.get("compliant"):
            score += 0.33
        elif fargate_res.get("has_profile") or fargate_res.get("has_k8s"):
            score += 0.15

        return {
            "workspace": str(repo_path),
            "repo_name": repo_path.name,
            "compliant": compliant,
            "compliance_score": min(round(score, 2), 1.0),
            "container": docker_res,
            "salting": salting_res,
            "fargate": fargate_res,
        }

    def init_iac(
        self,
        path: Optional[Path] = None,
        tech_stack: Optional[str] = None,
        app_name: Optional[str] = None,
        overwrite: bool = False,
    ) -> Dict[str, Any]:
        """Scaffold complete IaC assets: Dockerfile, .dockerignore, fargate profile, and k8s manifests."""
        target = Path(path) if path else self.workspace
        target.mkdir(parents=True, exist_ok=True)
        app_name = app_name or target.name.lower().replace("_", "-")

        # 1. Scaffold container
        c_res = self.scaffolder.scaffold(
            workspace=target,
            tech_stack=tech_stack,
            entrypoint=app_name.replace("-", "_"),
            overwrite=overwrite,
        )

        # 2. Salt container config
        s_res = self.salter.salt_container(
            image_name=app_name,
            workspace=target,
        )

        # 3. Scaffold EKS Fargate profile and k8s manifests with salted image ref
        f_res = self.fargate.scaffold(
            workspace=target,
            app_name=app_name,
            image_ref=s_res["pinned_ref"],
            overwrite=overwrite,
        )

        # 4. Write master .hath0r/iac/spec.yaml
        iac_dir = target / ".hath0r" / "iac"
        iac_dir.mkdir(parents=True, exist_ok=True)
        spec_content = f"""schema_version: "hath0r.iac.spec/1"
service_name: "{app_name}"
container:
  tech_stack: "{c_res['tech_stack']}"
  base_image: "python:3.11-slim"
  multi_stage: true
  non_root_user:
    uid: 10001
    gid: 10001
    username: "hath0r"
  healthcheck:
    enabled: true
    interval_seconds: 30
    timeout_seconds: 5
    retries: 3
  read_only_root_filesystem: true
salting:
  digest_pinning: true
  sha256_digest: "{s_res['pinned_digest']}"
  signature_provider: "cosign"
  attestation_format: "slsa-provenance-v1"
  secret_salting_provider: "aws_secrets_manager"
deployment:
  target_platform: "aws_eks_fargate"
  cluster_name: "hath0r-eks-cluster"
  namespace: "{app_name}"
  fargate_profile: "hath0r-{app_name}-profile"
  replicas: 2
  resources:
    cpu_request: "250m"
    cpu_limit: "500m"
    memory_request: "512Mi"
    memory_limit: "1Gi"
  ingress:
    alb_scheme: "internet-facing"
    target_type: "ip"
  irsa_iam_role_arn: "arn:aws:iam::711387127111:role/hath0r-{app_name}-irsa"
"""
        (iac_dir / "spec.yaml").write_text(spec_content)

        all_written = c_res["files_written"] + f_res["files_written"] + [".hath0r/iac/spec.yaml", ".hath0r/iac/salting-receipt.json"]

        return {
            "success": True,
            "workspace": str(target),
            "app_name": app_name,
            "tech_stack": c_res["tech_stack"],
            "files_scaffolded": all_written,
            "pinned_digest": s_res["pinned_digest"],
            "pinned_ref": s_res["pinned_ref"],
        }

    def validate_iac(self, path: Optional[Path] = None) -> Dict[str, Any]:
        """Perform full validation of repository against CR-IAC-001."""
        target = Path(path) if path else self.workspace
        audit = self._audit_single_repo(target)

        # Collect diagnostics
        diagnostics: List[Dict[str, Any]] = []
        for finding in audit["container"]["findings"]:
            diagnostics.append({"pillar": "container", "level": "error" if not audit["container"]["compliant"] else "warning", "message": finding})
        for finding in audit["fargate"]["findings"]:
            diagnostics.append({"pillar": "fargate", "level": "error", "message": finding})
        if not audit["salting"]["compliant"]:
            diagnostics.append({"pillar": "salting", "level": "error", "message": "Container image is not cryptographically salted or digest pinned."})

        return {
            "workspace": str(target),
            "repo_name": target.name,
            "valid": audit["compliant"],
            "score": audit["compliance_score"],
            "pillars": {
                "container_security": audit["container"],
                "cryptographic_salting": audit["salting"],
                "eks_fargate_readiness": audit["fargate"],
            },
            "diagnostics": diagnostics,
        }

    def salt_container(self, image: str, workspace: Optional[Path] = None) -> Dict[str, Any]:
        """Cryptographically salt container image reference."""
        target = Path(workspace) if workspace else self.workspace
        return self.salter.salt_container(image_name=image, workspace=target)

    def render_manifests(self, path: Optional[Path] = None, environment: str = "development") -> Dict[str, Any]:
        """Render parameterized Kubernetes manifests for target environment."""
        target = Path(path) if path else self.workspace
        return self.fargate.render(workspace=target, environment=environment)
