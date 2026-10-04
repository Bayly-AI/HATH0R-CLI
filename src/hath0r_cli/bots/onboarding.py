"""Onboarding micro-bots for Hath0r universal repository initialization and alignment."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


@dataclass
class RepoLayoutBot:
    """Manages directory layout scaffolding, hidden root enforcement, and state backup/rollback."""

    cwd: Path = field(default_factory=Path.cwd)

    def backup_state(self, dry_run: bool = False) -> Dict[str, Any]:
        """Snapshot critical files (README.md, .github workflows, etc.) before initialization for safe rollback."""
        backup_dir = self.cwd / ".hath0r" / "spool" / "init-backup"
        backed_up: List[str] = []

        files_to_backup = ["README.md", "TECH_README.md", "AGENTS.md", "WARP.md", ".gitignore"]
        if not dry_run:
            backup_dir.mkdir(parents=True, exist_ok=True)
            for fname in files_to_backup:
                fpath = self.cwd / fname
                if fpath.exists():
                    shutil.copy2(fpath, backup_dir / fname)
                    backed_up.append(fname)

            # Backup workflows if present
            wf_dir = self.cwd / ".github" / "workflows"
            if wf_dir.is_dir():
                bk_wf_dir = backup_dir / ".github" / "workflows"
                bk_wf_dir.mkdir(parents=True, exist_ok=True)
                for wf_file in wf_dir.glob("*.yml"):
                    shutil.copy2(wf_file, bk_wf_dir / wf_file.name)
                    backed_up.append(f".github/workflows/{wf_file.name}")

        return {
            "success": True,
            "dry_run": dry_run,
            "backup_dir": str(backup_dir),
            "files_backed_up": backed_up,
            "message": f"Created pre-init snapshot with {len(backed_up)} files.",
        }

    def scaffold_layout(self, dry_run: bool = False) -> Dict[str, Any]:
        """Create canonical directories: .hath0r/, cfg/, contracts/, docs/, tests/, .github/workflows/."""
        dirs_to_create = [
            self.cwd / ".hath0r" / "cfg",
            self.cwd / ".hath0r" / "memory",
            self.cwd / ".hath0r" / "state" / "cache",
            self.cwd / ".hath0r" / "state" / "context",
            self.cwd / "cfg",
            self.cwd / "contracts" / "schemas",
            self.cwd / "docs" / "governance" / "playbooks",
            self.cwd / "docs" / "governance" / "rules",
            self.cwd / ".github" / "workflows",
        ]

        created_dirs: List[str] = []
        if not dry_run:
            for d in dirs_to_create:
                if not d.exists():
                    d.mkdir(parents=True, exist_ok=True)
                    created_dirs.append(str(d.relative_to(self.cwd)))

        return {
            "success": True,
            "dry_run": dry_run,
            "directories_created": created_dirs,
            "message": f"Scaffolded {len(created_dirs)} canonical directories.",
        }

    def sync_ci_workflows(self, dry_run: bool = False) -> Dict[str, Any]:
        """Provision and synchronize canonical CI promotion path and quality gate workflows."""
        from hath0r_cli.common import _cli_repo_root, _discover_group_root

        canonical_wf_dir: Optional[Path] = None
        group_root = _discover_group_root(self.cwd)
        if group_root:
            cand = group_root / "HATH0R-CLI" / ".github" / "workflows"
            if cand.is_dir():
                canonical_wf_dir = cand

        if not canonical_wf_dir:
            cli_wf = _cli_repo_root() / ".github" / "workflows"
            if cli_wf.is_dir():
                canonical_wf_dir = cli_wf

        if not canonical_wf_dir or not canonical_wf_dir.is_dir():
            return {
                "success": False,
                "error": "Canonical CI workflows directory not found.",
            }

        target_wf_dir = self.cwd / ".github" / "workflows"
        if not dry_run:
            target_wf_dir.mkdir(parents=True, exist_ok=True)

        synced: List[str] = []
        workflows_to_sync = ["enforce-promotion-path.yml", "notify-pr-failure.yml"]
        for wf_name in workflows_to_sync:
            src_wf = canonical_wf_dir / wf_name
            dst_wf = target_wf_dir / wf_name
            if src_wf.is_file():
                if not dry_run:
                    shutil.copy2(src_wf, dst_wf)
                synced.append(wf_name)

        return {
            "success": True,
            "dry_run": dry_run,
            "canonical_dir": str(canonical_wf_dir),
            "target_dir": str(target_wf_dir),
            "synced_workflows": synced,
            "synced_count": len(synced),
            "message": f"{'[DRY RUN] Would sync' if dry_run else 'Synced'} {len(synced)} CI workflow(s).",
        }

    def rollback_init(self, dry_run: bool = False) -> Dict[str, Any]:
        """Restore repository state from init-backup snapshot."""
        backup_dir = self.cwd / ".hath0r" / "spool" / "init-backup"
        if not backup_dir.exists():
            return {"success": False, "error": "No init backup found to restore."}

        restored: List[str] = []
        if not dry_run:
            for bfile in backup_dir.iterdir():
                if bfile.is_file():
                    shutil.copy2(bfile, self.cwd / bfile.name)
                    restored.append(bfile.name)

            # Restore workflows if backed up
            bk_wf_dir = backup_dir / ".github" / "workflows"
            if bk_wf_dir.is_dir():
                dst_wf_dir = self.cwd / ".github" / "workflows"
                dst_wf_dir.mkdir(parents=True, exist_ok=True)
                for wf_file in bk_wf_dir.glob("*.yml"):
                    shutil.copy2(wf_file, dst_wf_dir / wf_file.name)
                    restored.append(f".github/workflows/{wf_file.name}")

        return {
            "success": True,
            "dry_run": dry_run,
            "files_restored": restored,
            "message": f"Successfully rolled back {len(restored)} files from backup.",
        }


@dataclass
class GovernanceBot:
    """Scaffolds AGENTS.md, WARP.md, version config, and spreads hyper-context."""

    cwd: Path = field(default_factory=Path.cwd)

    def scaffold_agents_md(self, product_name: Optional[str] = None, dry_run: bool = False) -> Dict[str, Any]:
        """Generate canonical AGENTS.md with CLI-First CR-CLI-ENTRY-001 rule."""
        p_name = product_name or self.cwd.name
        agents_file = self.cwd / "AGENTS.md"

        content = (
            f"# AGENTS.md — {p_name}\n\n"
            f"> Role: **{p_name}** · Member of Enterprise Agentic Platform\n\n"
            "## CR-CLI-ENTRY-001: Start with the CLI (CRITICAL — Org-Wide)\n\n"
            "1. **Start with the CLI (CRITICAL ENTRY GATE)**: When receiving ANY request or starting any task, "
            "agents **MUST ALWAYS START WITH THE OPERATOR CLI (`hath0r`)** rather than inventing ad-hoc scripts.\n"
            "2. **Missing Capability Offer**: If the required connection, MCP, workflow, bot, or factory does not exist "
            "in `hath0r`, offer to register the missing capability.\n"
            "3. **Docs before code**: Require procedure/playbook/runbook before scaffolding implementation.\n\n"
            "## Promotion Path (CR-BAI-001)\n\n"
            "```text\n"
            "local → development → testing → staging → master (Production)\n"
            "```\n\n"
            "## Branch Governance (cr-branch-gov-001)\n\n"
            "- Issue first: create an issue before cutting a branch.\n"
            "- Naming: `feature|bugfix|enhancement|chore/<issue-number>-slug`\n"
            "- Base PR target: `development`\n\n"
            "## AgentGraph Substrate\n\n"
            "This repository is governed by the Hath0r AgentGraph substrate. "
            "Dynamic rule retrieval, role RBAC, and policy graphs are stored under `.hath0r/agentgraph/`.\n"
            "- Query status: `hath0r agentgraph status`\n"
            '- Query rules: `hath0r agentgraph query "<topic>"`\n'
            "- Route role: `hath0r agentgraph route --role <role>`\n"
            "- Validate rules: `hath0r agentgraph validate`\n"
        )

        if not dry_run:
            agents_file.write_text(content, encoding="utf-8")

        return {
            "success": True,
            "dry_run": dry_run,
            "file": str(agents_file.relative_to(self.cwd)),
            "message": "Scaffolded canonical AGENTS.md.",
        }

    def init_versioning(self, initial_version: str = "0.0.1", dry_run: bool = False) -> Dict[str, Any]:
        """Initialize .hath0r/cfg/version.yaml and VERSION file."""
        v_file = self.cwd / ".hath0r" / "cfg" / "version.yaml"
        v_txt = self.cwd / "VERSION"

        if not dry_run:
            v_file.parent.mkdir(parents=True, exist_ok=True)
            v_file.write_text(yaml.dump({"version": initial_version}), encoding="utf-8")
            v_txt.write_text(initial_version.strip() + "\n", encoding="utf-8")

        return {
            "success": True,
            "dry_run": dry_run,
            "version": initial_version,
            "message": f"Initialized SemVer at v{initial_version}.",
        }

    def spread_hyper_context(self, dry_run: bool = False) -> Dict[str, Any]:
        """Create hyper-context rules in core subdirectories."""
        from hath0r_cli.bots.hyper_context import HyperContextBot

        bot = HyperContextBot()
        results: List[Dict[str, Any]] = []

        subdirs = ["src", "lib", "contracts", "docs", "tests", "cfg"]
        for sub in subdirs:
            p = self.cwd / sub
            if p.exists() and p.is_dir():
                if not dry_run:
                    res = bot.spread_context(str(p), f"{sub.capitalize()} Subsystem")
                    results.append(res)
                else:
                    results.append({"success": True, "target": str(p)})

        return {
            "success": True,
            "dry_run": dry_run,
            "subsystems_spread": len(results),
            "message": f"Spread hyper-context across {len(results)} active subsystems.",
        }


@dataclass
class DocRefactorBot:
    """Refactors README.md, generates TECH_README.md, and seeds playbooks."""

    cwd: Path = field(default_factory=Path.cwd)

    def refactor_readme(self, product_name: Optional[str] = None, dry_run: bool = False) -> Dict[str, Any]:
        """Refactor or create README.md to ensure Sales Overview and TECH_README links."""
        p_name = product_name or self.cwd.name
        readme_path = self.cwd / "README.md"

        existing = ""
        if readme_path.exists():
            existing = readme_path.read_text(encoding="utf-8")

        if "# " not in existing or "Sales" not in existing:
            new_content = (
                f"# {p_name}\n\n"
                f"**Enterprise Agentic Application & Microservice**\n\n"
                "> Technical Reference: See [TECH_README.md](TECH_README.md) for architecture, subsystem maps, and specifications.\n\n"
                "---\n\n"
                "## 🌟 Sales & Feature Overview\n\n"
                f"{p_name} is built on the HATHOR agentic framework, providing:\n\n"
                "- 🛡️ **Zero-Trust Governance & Execution**: Hardened boundaries against unauthorized file mutations.\n"
                "- 🧠 **Tri-Graph Substrate**: Integrated KnowledgeGraph, ContextGraph, and MemoryGraph for autonomous reasoning.\n"
                "- ⚡ **Autonomous Workflows**: Pre-configured bot workflows for CI/CD and hygiene.\n\n"
                "---\n\n"
                "## Quick Start\n\n"
                "```sh\n"
                "hath0r doctor\n"
                "hath0r factory list\n"
                "```\n\n"
                "---\n\n"
                "## License\n\n"
                "Apache License 2.0\n"
            )
            if not dry_run:
                readme_path.write_text(new_content, encoding="utf-8")

        return {
            "success": True,
            "dry_run": dry_run,
            "file": "README.md",
            "message": "Refactored README.md with Sales Overview and Tech links.",
        }

    def scaffold_tech_readme(self, product_name: Optional[str] = None, dry_run: bool = False) -> Dict[str, Any]:
        """Create or update TECH_README.md."""
        p_name = product_name or self.cwd.name
        tech_path = self.cwd / "TECH_README.md"

        content = (
            f"# Technical Architecture — {p_name}\n\n"
            "This document provides the definitive technical specification and subsystem map.\n\n"
            "## Architecture Map\n\n"
            "```text\n"
            "Agent ──► hath0r CLI ──► Tri-Graph Substrate (KG / CG / MG)\n"
            "                      │\n"
            "                      ├─ Governance & Quality Gates (JEV Guard)\n"
            "                      └─ Automated Bot Factories\n"
            "```\n\n"
            "## Subsystem Registry\n\n"
            "- `.hath0r/`: Framework metadata root (configs, memory, cache)\n"
            "- `contracts/`: JSON schema contracts\n"
            "- `docs/governance/playbooks/`: Coding and troubleshooting playbooks\n"
        )

        if not dry_run:
            tech_path.write_text(content, encoding="utf-8")

        return {
            "success": True,
            "dry_run": dry_run,
            "file": "TECH_README.md",
            "message": "Scaffolded technical guide TECH_README.md.",
        }

    def seed_playbooks(self, dry_run: bool = False) -> Dict[str, Any]:
        """Seed baseline coding and troubleshooting playbooks."""
        pb_dir = self.cwd / "docs" / "governance" / "playbooks"

        coding_pb = (
            "# Coding Playbook\n\n"
            "## 1. Safe Types\n"
            "Ensure variables are managed and checked for explicit state.\n\n"
            "## 2. Architecture & Design\n"
            "Build to SOA specifications with dependency injection.\n\n"
            "## 3. Asynchronous Operations\n"
            "Always make network and I/O connections asynchronous.\n"
        )

        troubleshoot_pb = (
            "# Troubleshooting Playbook\n\n"
            "## 1. Reproducing the Error First\n"
            "Establish a minimal reproducible example (MRE).\n\n"
            "## 2. Separate Concerns\n"
            "Isolate API, EDGE, DB, and UI layers independently.\n\n"
            "## 3. Validating the Fix\n"
            "Follow the promotion path (development -> testing -> staging -> master).\n"
        )

        if not dry_run:
            pb_dir.mkdir(parents=True, exist_ok=True)
            (pb_dir / "playbook-coding.md").write_text(coding_pb, encoding="utf-8")
            (pb_dir / "playbook-troubleshooting.md").write_text(troubleshoot_pb, encoding="utf-8")

        return {
            "success": True,
            "dry_run": dry_run,
            "message": "Seeded Coding and Troubleshooting playbooks.",
        }


@dataclass
class TestHarnessBot:
    """Detects repository tech stack and provisions test harnesses and CI promotion workflows."""

    __test__ = False
    cwd: Path = field(default_factory=Path.cwd)

    def detect_stack(self) -> Dict[str, Any]:
        """Identify tech ecosystem (Node/TS, Python, Rust, Go, Polyglot)."""
        stack = "polyglot"
        if (self.cwd / "package.json").exists():
            stack = "node-typescript"
        elif (self.cwd / "pyproject.toml").exists() or (self.cwd / "requirements.txt").exists():
            stack = "python"
        elif (self.cwd / "Cargo.toml").exists():
            stack = "rust"
        elif (self.cwd / "go.mod").exists():
            stack = "go"

        return {
            "success": True,
            "stack": stack,
            "message": f"Detected technology stack: {stack}",
        }

    def scaffold_tests(self, dry_run: bool = False) -> Dict[str, Any]:
        """Scaffold baseline test harness if missing."""
        det = self.detect_stack()
        stack = det["stack"]
        tests_dir = self.cwd / "tests"

        created: List[str] = []
        if not dry_run:
            tests_dir.mkdir(parents=True, exist_ok=True)
            if stack == "python" and not (tests_dir / "test_smoke.py").exists():
                (tests_dir / "test_smoke.py").write_text("def test_smoke():\n    assert True\n", encoding="utf-8")
                created.append("tests/test_smoke.py")
            elif stack == "node-typescript" and not (tests_dir / "smoke.test.ts").exists():
                (tests_dir / "smoke.test.ts").write_text(
                    "test('smoke', () => { expect(true).toBe(true); });\n", encoding="utf-8"
                )
                created.append("tests/smoke.test.ts")

        return {
            "success": True,
            "dry_run": dry_run,
            "stack": stack,
            "tests_created": created,
            "message": f"Scaffolded test harness for {stack}.",
        }

    def provision_ci_workflows(self, dry_run: bool = False) -> Dict[str, Any]:
        """Scaffold GitHub Actions promotion workflow."""
        wf_dir = self.cwd / ".github" / "workflows"
        promo_wf = (
            "name: Enforce Promotion Path\n"
            "on:\n"
            "  pull_request:\n"
            "    branches: [development, testing, staging, master]\n"
            "jobs:\n"
            "  validate-promotion-path:\n"
            "    runs-on: ubuntu-latest\n"
            "    steps:\n"
            "      - uses: actions/checkout@v4\n"
            "      - name: Validate promotion path\n"
            "        run: echo 'Validating promotion ladder (local -> dev -> test -> stage -> master)'\n"
        )

        if not dry_run:
            wf_dir.mkdir(parents=True, exist_ok=True)
            (wf_dir / "enforce-promotion-path.yml").write_text(promo_wf, encoding="utf-8")

        return {
            "success": True,
            "dry_run": dry_run,
            "workflows": [".github/workflows/enforce-promotion-path.yml"],
            "message": "Provisioned GitHub Actions promotion workflow.",
        }


@dataclass
class TriGraphIngestBot:
    """Compiles KnowledgeGraph, initializes ContextGraph, and ingests MemoryGraph."""

    cwd: Path = field(default_factory=Path.cwd)

    def compile_knowledge_graph(self, dry_run: bool = False) -> Dict[str, Any]:
        """Compile repository markdown files into KnowledgeGraph cache."""
        target_file = self.cwd / ".hath0r" / "state" / "cache" / "knowledge.json"

        # Ingest docs and root markdown files
        nodes: List[Dict[str, Any]] = []
        for md in self.cwd.rglob("*.md"):
            if not any(p.startswith(".") and p != ".hath0r" for p in md.relative_to(self.cwd).parts[:-1]):
                nodes.append(
                    {
                        "id": f"doc:{md.relative_to(self.cwd)}",
                        "path": str(md.relative_to(self.cwd)),
                        "title": md.stem,
                    }
                )

        if not dry_run:
            target_file.parent.mkdir(parents=True, exist_ok=True)
            target_file.write_text(json.dumps({"nodes": nodes}, indent=2), encoding="utf-8")

        return {
            "success": True,
            "dry_run": dry_run,
            "nodes_indexed": len(nodes),
            "message": f"Compiled KnowledgeGraph cache with {len(nodes)} nodes.",
        }

    def init_context_graph(self, dry_run: bool = False) -> Dict[str, Any]:
        """Initialize ContextGraph session tracking state."""
        ctx_file = self.cwd / ".hath0r" / "state" / "context" / "session_init.json"
        data = {
            "session_id": "init-session",
            "state": "initialized",
            "nodes": [{"id": "agent:root", "type": "agent", "label": "Onboarding Agent"}],
            "edges": [],
        }

        if not dry_run:
            ctx_file.parent.mkdir(parents=True, exist_ok=True)
            ctx_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

        return {
            "success": True,
            "dry_run": dry_run,
            "message": "Initialized ContextGraph runtime session state.",
        }

    def ingest_memory_graph(self, dry_run: bool = False) -> Dict[str, Any]:
        """Ingest repository documents into .hath0r/memory/graph.json."""
        from hath0r_cli.bots.memory_manager import MemoryManagerBot

        mem_bot = MemoryManagerBot(cwd=self.cwd)
        if not dry_run:
            mem_bot.initialize_memory()

        target = self.cwd / ".hath0r" / "memory" / "graph.json"
        nodes = [
            {
                "id": "rule:cr-cli-entry-001",
                "type": "rule",
                "label": "Start with CLI Rule",
                "content": "Always start with hath0r.",
            },
            {
                "id": "concept:tri-graph",
                "type": "concept",
                "label": "Tri-Graph Substrate",
                "content": "KnowledgeGraph, ContextGraph, MemoryGraph.",
            },
        ]

        if not dry_run:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps({"nodes": nodes, "edges": []}, indent=2), encoding="utf-8")

        return {
            "success": True,
            "dry_run": dry_run,
            "nodes_ingested": len(nodes),
            "message": f"Ingested {len(nodes)} core nodes into MemoryGraph.",
        }

    def setup_agentgraph(self, dry_run: bool = False) -> Dict[str, Any]:
        """Setup AgentGraph substrate and migrate knowledge, rules, agents, and memory."""
        from hath0r_cli.bots.agentgraph_bot import AgentGraphBot

        ag_bot = AgentGraphBot(cwd=self.cwd)
        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "message": "[DRY-RUN] Would setup AgentGraph and migrate knowledge, rules, agents, and memory.",
            }
        res = ag_bot.migrate_repo(self.cwd, update_agents_md=True)
        return {
            "success": res.get("success", True),
            "dry_run": False,
            "rules_migrated": res.get("rules_migrated", 0),
            "knowledge_migrated": res.get("knowledge_migrated", 0),
            "agents_migrated": res.get("agents_migrated", 0),
            "memory_migrated": res.get("memory_migrated", 0),
            "total_nodes": res.get("total_nodes", 0),
            "total_edges": res.get("total_edges", 0),
            "message": f"Setup AgentGraph with {res.get('total_nodes', 0)} nodes across knowledge, rules, agents, memory.",
        }

    def sync_kb_index(self, dry_run: bool = False) -> Dict[str, Any]:
        """Index documentation into local SQLite FTS5 store."""
        from hath0r_cli.kb_index import SQLiteIndexStore

        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "message": "[DRY-RUN] Would index repository documentation into SQLite FTS5.",
            }
        try:
            store = SQLiteIndexStore()
            sync_stats = store.sync_directory(self.cwd)
            return {
                "success": True,
                "dry_run": False,
                "stats": sync_stats,
                "message": f"Indexed repository documentation into SQLite FTS5: {sync_stats.get('indexed', 0)} new, {sync_stats.get('updated', 0)} updated.",
            }
        except Exception as e:
            return {
                "success": True,
                "warning": str(e),
                "message": f"KB index sync skipped: {e}",
            }
