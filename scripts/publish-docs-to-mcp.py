#!/usr/bin/env python3
"""Publish group documentation into the proper MCP knowledgebase canonical tree."""
from __future__ import annotations
import argparse, hashlib, json, re, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BUCKETS_DEFAULT = [
    "knowledge", "runbooks", "playbooks", "procedures", "checklists",
    "strategies", "workflows", "rules", "plans", "lessons-learned",
]

def load_config(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def classify(path: Path, rules: list[dict[str, Any]], default: str, force: str | None) -> str:
    if force:
        return force
    hay = str(path).lower().replace("\\", "/")
    name = path.name.lower()
    for rule in rules:
        for m in rule.get("match", []):
            if m.lower() in hay or m.lower() in name:
                return rule["bucket"]
    return default

def should_exclude(path: Path, excludes: list[str]) -> bool:
    s = str(path).replace("\\", "/")
    name = path.name
    if name.startswith(".env") or name.endswith(".env"):
        return True
    for pat in excludes:
        core = pat.strip("*").strip("/")
        if core and core in s:
            return True
    if any(x in s for x in ("/.git/", "/node_modules/", "/.credentials/", "/dist/", "/coverage/")):
        return True
    return False

def stable_name(src: Path, root: Path | None) -> str:
    try:
        if root is not None and (root in src.parents or src.parent == root or src == root):
            rel = src.relative_to(root)
        else:
            rel = Path(src.name)
    except Exception:
        rel = Path(src.name)
    text = str(rel).replace("\\", "/")
    digest = hashlib.sha1(text.encode(), usedforsecurity=False).hexdigest()[:10]
    safe = re.sub(r"[^A-Za-z0-9._-]+", "__", text.replace("/", "__"))
    if not safe.endswith(".md"):
        safe += ".md"
    return f"{safe}__{digest}.md"

def collect_files(source: dict[str, Any]) -> list[tuple[Path, Path | None]]:
    p = Path(source["path"]).expanduser()
    if not p.exists():
        return []
    if p.is_file():
        return [(p, p.parent)]
    glob = source.get("glob") or "**/*.md"
    return [(f, p) for f in sorted(p.glob(glob)) if f.is_file()]

def materialize_group(group_id: str, group: dict[str, Any], cfg: dict[str, Any], dry_run: bool) -> dict[str, Any]:
    mcp = group["mcp"]
    candidates = [Path(mcp["local_path"]).expanduser()]
    for fb in mcp.get("fallback_local_paths", []) or []:
        candidates.append(Path(fb).expanduser())
    target_root = None
    for c in candidates:
        if c.exists():
            target_root = c
            break
    if target_root is None:
        return {"group": group_id, "error": "no MCP local path found", "copied": 0, "skipped": 0}
    if target_root.name == "knowledgebase":
        canonical = target_root / "canonical"
    else:
        canonical = target_root / mcp.get("canonical_root", "knowledgebase/canonical")
    rules = cfg.get("classification", {}).get("rules", [])
    default_bucket = cfg.get("classification", {}).get("default_bucket", "knowledge")
    excludes = cfg.get("excludes", [])
    buckets = cfg.get("policy", {}).get("buckets", BUCKETS_DEFAULT)
    report = {
        "group": group_id, "label": group.get("label"), "mcp_github": mcp.get("github"),
        "target_canonical": str(canonical), "copied": 0, "skipped": 0, "by_bucket": {},
        "missing_sources": [], "files": [],
    }
    if not dry_run:
        for b in buckets:
            (canonical / b).mkdir(parents=True, exist_ok=True)
    for source in group.get("doc_sources", []):
        src_path = Path(source["path"]).expanduser()
        if not src_path.exists():
            report["missing_sources"].append(str(src_path))
            continue
        force = source.get("bucket_force")
        for f, root in collect_files(source):
            if should_exclude(f, excludes):
                report["skipped"] += 1
                continue
            if f.suffix.lower() not in {".md", ".mdx", ".txt"}:
                report["skipped"] += 1
                continue
            low = f.name.lower()
            if "secret" in low or "credential" in low or low.endswith(".pem"):
                report["skipped"] += 1
                continue
            bucket = classify(f, rules, default_bucket, force)
            dest = canonical / bucket / stable_name(f, root)
            entry = {"source": str(f), "bucket": bucket, "dest": str(dest), "sensitivity": source.get("sensitivity", "unknown")}
            report["files"].append(entry)
            report["copied"] += 1
            report["by_bucket"][bucket] = report["by_bucket"].get(bucket, 0) + 1
            if dry_run:
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            body = f.read_text(encoding="utf-8", errors="ignore")
            header = (
                f"<!-- mcp-doc-publish\n  group: {group_id}\n  source: {f}\n"
                f"  sensitivity: {source.get('sensitivity')}\n"
                f"  published_at: {datetime.now(timezone.utc).isoformat()}\n-->\n\n"
            )
            dest.write_text(header + body, encoding="utf-8")
    prov = {
        "published_at": datetime.now(timezone.utc).isoformat(),
        "group": group_id, "mcp": mcp.get("github"), "copied": report["copied"],
        "by_bucket": report["by_bucket"], "missing_sources": report["missing_sources"],
        "tool": "scripts/publish-docs-to-mcp.py", "config": "cfg/mcp-doc-publish.json",
    }
    if not dry_run:
        canonical.mkdir(parents=True, exist_ok=True)
        (canonical / "PUBLISH_MANIFEST.json").write_text(json.dumps(prov, indent=2) + "\n", encoding="utf-8")
        lines = [f"# MCP doc publish — {group.get('label', group_id)}", "", f"Published: `{prov['published_at']}`", f"Files: **{report['copied']}**", "", "## Buckets"]
        for b, n in sorted(report["by_bucket"].items()):
            lines.append(f"- `{b}`: {n}")
        lines += ["", "See `PUBLISH_MANIFEST.json`.", ""]
        (canonical / "INDEX.md").write_text("\n".join(lines), encoding="utf-8")
    report["manifest"] = prov
    return report

def maybe_kb_sync(mcp_path: Path, dry_run: bool) -> dict[str, Any]:
    if dry_run:
        return {"ran": False, "reason": "dry-run"}
    for cmd in (["kb", "sync", "local"], [sys.executable, "-m", "knowledgebase", "sync", "local"]):
        try:
            p = subprocess.run(cmd, cwd=str(mcp_path), capture_output=True, text=True, timeout=120)
            return {"ran": True, "cmd": cmd, "returncode": p.returncode, "stdout_tail": (p.stdout or "")[-500:], "stderr_tail": (p.stderr or "")[-500:]}
        except FileNotFoundError:
            continue
        except Exception as exc:
            return {"ran": False, "error": str(exc)}
    return {"ran": False, "reason": "kb CLI not available; canonical files written only"}

def main() -> int:
    ap = argparse.ArgumentParser(description="Publish docs to group MCP knowledgebases")
    ap.add_argument("--config", default=None)
    ap.add_argument("--group", action="append", dest="groups")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--sync", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    repo_root = Path(__file__).resolve().parent.parent
    cfg_path = Path(args.config) if args.config else repo_root / "cfg" / "mcp-doc-publish.json"
    if not cfg_path.exists():
        print(f"ERROR: config not found: {cfg_path}", file=sys.stderr)
        return 2
    cfg = load_config(cfg_path)
    groups_cfg = cfg.get("groups", {})
    selected = args.groups or list(groups_cfg.keys())
    reports = []
    for gid in selected:
        if gid not in groups_cfg:
            print(f"ERROR: unknown group {gid}", file=sys.stderr)
            return 2
        rep = materialize_group(gid, groups_cfg[gid], cfg, args.dry_run)
        if args.sync and "error" not in rep:
            rep["kb_sync"] = maybe_kb_sync(Path(groups_cfg[gid]["mcp"]["local_path"]).expanduser(), args.dry_run)
        reports.append(rep)
    out = {"ok": True, "dry_run": args.dry_run, "reports": reports}
    if args.json:
        print(json.dumps(out, indent=2))
    else:
        for r in reports:
            print(f"== {r.get('group')} → {r.get('target_canonical')} ==")
            if r.get("error"):
                print("  ERROR:", r["error"]); continue
            print(f"  copied={r['copied']} skipped={r.get('skipped',0)}")
            for b, n in sorted(r.get("by_bucket", {}).items()):
                print(f"  - {b}: {n}")
            if r.get("missing_sources"):
                print("  missing sources:")
                for m in r["missing_sources"]:
                    print(f"    - {m}")
            if r.get("kb_sync"):
                print("  kb_sync:", r["kb_sync"])
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
