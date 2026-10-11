"""AWS EKS Fargate profile and Kubernetes manifest synthesis and validation."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional


class FargateGenerator:
    """Generates and validates AWS EKS Fargate profiles and Kubernetes manifests."""

    DEPLOYMENT_TEMPLATE = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: {app_name}
  namespace: {namespace}
  labels:
    app.kubernetes.io/name: {app_name}
    app.kubernetes.io/managed-by: hath0r
    fargate: "true"
spec:
  replicas: 2
  selector:
    matchLabels:
      app.kubernetes.io/name: {app_name}
  template:
    metadata:
      labels:
        app.kubernetes.io/name: {app_name}
        fargate: "true"
    spec:
      serviceAccountName: {app_name}-sa
      securityContext:
        runAsNonRoot: true
        runAsUser: 10001
        runAsGroup: 10001
        fsGroup: 10001
      containers:
        - name: {app_name}
          image: {image_ref}
          imagePullPolicy: IfNotPresent
          securityContext:
            readOnlyRootFilesystem: true
            allowPrivilegeEscalation: false
            capabilities:
              drop:
                - ALL
          resources:
            requests:
              cpu: "250m"
              memory: "512Mi"
            limits:
              cpu: "500m"
              memory: "1Gi"
          ports:
            - containerPort: {port}
              protocol: TCP
          volumeMounts:
            - name: tmp-volume
              mountPath: /tmp
          livenessProbe:
            httpGet:
              path: {health_path}
              port: {port}
            initialDelaySeconds: 15
            periodSeconds: 20
          readinessProbe:
            httpGet:
              path: {health_path}
              port: {port}
            initialDelaySeconds: 5
            periodSeconds: 10
      volumes:
        - name: tmp-volume
          emptyDir: {{}}
"""

    SERVICE_TEMPLATE = """apiVersion: v1
kind: Service
metadata:
  name: {app_name}
  namespace: {namespace}
  labels:
    app.kubernetes.io/name: {app_name}
spec:
  type: ClusterIP
  ports:
    - port: {port}
      targetPort: {port}
      protocol: TCP
      name: http
  selector:
    app.kubernetes.io/name: {app_name}
"""

    INGRESS_TEMPLATE = """apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {app_name}-ingress
  namespace: {namespace}
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/listen-ports: '[{{"HTTP": 80}}, {{"HTTPS": 443}}]'
spec:
  rules:
    - host: {app_name}.bayly.ai
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: {app_name}
                port:
                  number: {port}
"""

    SERVICEACCOUNT_TEMPLATE = """apiVersion: v1
kind: ServiceAccount
metadata:
  name: {app_name}-sa
  namespace: {namespace}
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::711387127111:role/hath0r-{app_name}-irsa
"""

    FARGATE_PROFILE_TEMPLATE = """schema_version: "hath0r.fargate.profile/1"
fargate_profile_name: "hath0r-{app_name}-profile"
cluster_name: "hath0r-eks-cluster"
pod_execution_role_arn: "arn:aws:iam::711387127111:role/AmazonEKSFargatePodExecutionRole"
subnets:
  - "subnet-0a1b2c3d4e5f67890"
  - "subnet-0f9e8d7c6b5a43210"
selectors:
  - namespace: "{namespace}"
    labels:
      fargate: "true"
tags:
  ManagedBy: "hath0r"
  Service: "{app_name}"
"""

    def scaffold(
        self,
        workspace: Path,
        app_name: Optional[str] = None,
        namespace: Optional[str] = None,
        port: int = 8000,
        health_path: str = "/health",
        image_ref: Optional[str] = None,
        overwrite: bool = False,
    ) -> Dict[str, Any]:
        """Scaffold AWS EKS Fargate profile and Kubernetes manifests."""
        workspace = Path(workspace)
        k8s_dir = workspace / "k8s"
        k8s_dir.mkdir(parents=True, exist_ok=True)

        app_name = app_name or workspace.name.lower().replace("_", "-")
        namespace = namespace or app_name
        image_ref = image_ref or f"711387127111.dkr.ecr.us-east-1.amazonaws.com/{app_name}:latest"

        files_written = []

        # 1. fargate-profile.yaml
        profile_path = workspace / "fargate-profile.yaml"
        if not profile_path.exists() or overwrite:
            content = self.FARGATE_PROFILE_TEMPLATE.format(app_name=app_name, namespace=namespace)
            profile_path.write_text(content)
            files_written.append("fargate-profile.yaml")

        # 2. k8s/deployment.yaml
        dep_path = k8s_dir / "deployment.yaml"
        if not dep_path.exists() or overwrite:
            content = self.DEPLOYMENT_TEMPLATE.format(
                app_name=app_name,
                namespace=namespace,
                image_ref=image_ref,
                port=port,
                health_path=health_path,
            )
            dep_path.write_text(content)
            files_written.append("k8s/deployment.yaml")

        # 3. k8s/service.yaml
        svc_path = k8s_dir / "service.yaml"
        if not svc_path.exists() or overwrite:
            content = self.SERVICE_TEMPLATE.format(app_name=app_name, namespace=namespace, port=port)
            svc_path.write_text(content)
            files_written.append("k8s/service.yaml")

        # 4. k8s/ingress.yaml
        ing_path = k8s_dir / "ingress.yaml"
        if not ing_path.exists() or overwrite:
            content = self.INGRESS_TEMPLATE.format(app_name=app_name, namespace=namespace, port=port)
            ing_path.write_text(content)
            files_written.append("k8s/ingress.yaml")

        # 5. k8s/serviceaccount.yaml
        sa_path = k8s_dir / "serviceaccount.yaml"
        if not sa_path.exists() or overwrite:
            content = self.SERVICEACCOUNT_TEMPLATE.format(app_name=app_name, namespace=namespace)
            sa_path.write_text(content)
            files_written.append("k8s/serviceaccount.yaml")

        return {
            "workspace": str(workspace),
            "app_name": app_name,
            "namespace": namespace,
            "files_written": files_written,
        }

    def audit_fargate(self, workspace: Path) -> Dict[str, Any]:
        """Audit repository for AWS EKS Fargate readiness."""
        workspace = Path(workspace)
        profile_path = workspace / "fargate-profile.yaml"
        k8s_dir = workspace / "k8s"

        has_profile = profile_path.exists()
        has_k8s = k8s_dir.exists() and bool(list(k8s_dir.glob("*.yaml")))

        findings: List[str] = []
        if not has_profile:
            findings.append("fargate-profile.yaml is missing.")
        if not has_k8s:
            findings.append("k8s/ directory or manifests missing.")

        compliant = has_profile and has_k8s
        privileged_detected = False
        target_type_ip = False

        if has_k8s:
            for manifest in k8s_dir.glob("*.yaml"):
                content = manifest.read_text()
                if "privileged: true" in content:
                    privileged_detected = True
                    findings.append(f"Privileged container detected in {manifest.name} (disallowed on Fargate).")
                    compliant = False
                if "hostPath:" in content:
                    findings.append(f"hostPath volume detected in {manifest.name} (disallowed on Fargate).")
                    compliant = False
                if "target-type: ip" in content:
                    target_type_ip = True

            if not target_type_ip and (k8s_dir / "ingress.yaml").exists():
                findings.append("ALB Ingress missing 'alb.ingress.kubernetes.io/target-type: ip' annotation.")
                compliant = False

        return {
            "has_profile": has_profile,
            "has_k8s": has_k8s,
            "target_type_ip": target_type_ip,
            "privileged_detected": privileged_detected,
            "compliant": compliant,
            "findings": findings,
        }

    def render(self, workspace: Path, environment: str = "development") -> Dict[str, Any]:
        """Render parameterized manifests into build/iac/<environment>/."""
        workspace = Path(workspace)
        k8s_dir = workspace / "k8s"
        out_dir = workspace / "build" / "iac" / environment
        out_dir.mkdir(parents=True, exist_ok=True)

        rendered_files = []
        if k8s_dir.exists():
            for src in k8s_dir.glob("*.yaml"):
                raw = src.read_text()
                # Environment namespace override
                rendered = re.sub(
                    r"namespace:\s*([a-zA-Z0-9-_]+)",
                    f"namespace: \\1-{environment}",
                    raw,
                )
                dest = out_dir / src.name
                dest.write_text(rendered)
                rendered_files.append(str(dest))

        return {
            "environment": environment,
            "output_directory": str(out_dir),
            "rendered_files": rendered_files,
            "count": len(rendered_files),
        }
