"""Complexity levels for code changes (#611, #612).

A deterministic classifier proposes a level L1 to L5 for a change from diff metrics. The rubric that
defines the levels lives in ``cfg/evals/complexity-levels.yaml``; line counts here are proxies for that
rubric, not its definition. ``cohen_kappa`` checks the classifier (or a second rater) against labels.

==== ============ ==============================================================
L1   Trivial      Docs, config or version-only; no source or test change
L2   Local        One function plus its test; small
L3   Module       Several functions in one module; about 50 to 250 added lines
L4   Cross-module Several modules or a public interface; about 250 to 600 lines
L5   System       Contracts, schemas or migrations across modules; over 600 lines
==== ============ ==============================================================
"""

from __future__ import annotations

import ast
import re
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

LEVELS: Tuple[str, ...] = ("L1", "L2", "L3", "L4", "L5")
SOURCE_EXTS = {".py", ".ts", ".tsx", ".js", ".go", ".rs", ".java"}
IGNORED_PREFIXES = (".hath0r/", ".git/")
IGNORED_FILES = {"CLAUDE.md", "AGENTS.md"}
_DEF_RE = re.compile(r"^\s*(?:async\s+)?def\s+\w+|^\s*(?:export\s+)?function\s+\w+")


@dataclass
class ChangeMetrics:
    """Diff metrics a level is derived from."""

    files: List[str] = field(default_factory=list)
    source_files: List[str] = field(default_factory=list)
    test_files: List[str] = field(default_factory=list)
    added_lines: int = 0
    modules: List[str] = field(default_factory=list)
    new_functions: int = 0
    contract_touched: bool = False
    interface_touched: bool = False
    max_complexity: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def is_test_path(path: str) -> bool:
    """True for test files (tests/ directories, test_*.py, *_test.py)."""
    name = Path(path).name
    return path.startswith(("tests/", "test/")) or "/tests/" in path or name.startswith("test_") or name.endswith("_test.py")


def _module_of(path: str) -> str:
    """Module = first directory below the package root, or the file stem for top-level package files."""
    parts = Path(path).parts
    if parts and parts[0] == "src":
        parts = parts[1:]
    if len(parts) >= 3:
        return "/".join(parts[:2])
    if len(parts) == 2:
        return f"{parts[0]}/{Path(parts[1]).stem}"
    return parts[0] if parts else path


def _cognitive_complexity(source: str) -> int:
    try:
        from hath0r_cli.bots.local_quality_gate_bot import _ast_cognitive_complexity
    except Exception:  # pragma: no cover - optional dependency chain
        return 0
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return 0
    funcs = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    return max((_ast_cognitive_complexity(f) for f in funcs), default=0)


def metrics_from_changes(changes: Mapping[str, Sequence[str]], contents: Optional[Mapping[str, str]] = None) -> ChangeMetrics:
    """Build metrics from ``{path: [added lines]}`` (and optional full contents of changed files)."""
    m = ChangeMetrics()
    for path in sorted(changes):
        if path.startswith(IGNORED_PREFIXES) or path in IGNORED_FILES:
            continue
        added = list(changes[path])
        m.files.append(path)
        m.added_lines += len(added)
        p = Path(path)
        if "contracts/" in path or path.endswith(".schema.json") or "/migrations/" in f"/{path}":
            m.contract_touched = True
        if p.suffix not in SOURCE_EXTS:
            continue
        if is_test_path(path):
            m.test_files.append(path)
            continue
        m.source_files.append(path)
        if p.name in ("__init__.py", "index.ts", "index.js"):
            m.interface_touched = True
        m.new_functions += sum(1 for ln in added if _DEF_RE.match(ln))
        mod = _module_of(path)
        if mod not in m.modules:
            m.modules.append(mod)
        if contents and p.suffix == ".py" and path in contents:
            m.max_complexity = max(m.max_complexity, _cognitive_complexity(contents[path]))
    return m


def classify(m: ChangeMetrics) -> str:
    """Propose a level for a change from its metrics."""
    if not m.source_files and not m.test_files:
        return "L1"
    n_mod = len(m.modules)
    if m.added_lines > 600 or (m.contract_touched and (n_mod >= 2 or m.added_lines > 250)):
        return "L5"
    if n_mod >= 2 or m.added_lines > 250 or (m.interface_touched and m.new_functions >= 3):
        return "L4"
    if m.new_functions >= 3 or m.added_lines > 50 or m.max_complexity >= 10:
        return "L3"
    return "L2"


def _git(cwd: Path, *args: str) -> str:
    res = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=False)
    return res.stdout if res.returncode == 0 else ""


def workspace_changes(cwd: Path, base: Optional[str] = None) -> Tuple[Dict[str, List[str]], Dict[str, str]]:
    """Added lines per changed file in a git workspace: committed branch changes since ``base`` (default
    ``development`` when it exists), uncommitted edits, and untracked files."""
    cwd = Path(cwd)
    changes: Dict[str, List[str]] = {}
    contents: Dict[str, str] = {}
    ref = base
    if ref is None and _git(cwd, "rev-parse", "--verify", "--quiet", "development").strip():
        merge_base = _git(cwd, "merge-base", "HEAD", "development").strip()
        ref = merge_base or None
    diff = _git(cwd, "diff", "--no-color", "-U0", ref) if ref else _git(cwd, "diff", "--no-color", "-U0", "HEAD")
    current: Optional[str] = None
    for line in diff.splitlines():
        if line.startswith("+++ "):
            target = line[4:]
            current = None if target == "/dev/null" else target[2:] if target.startswith("b/") else target
            if current:
                changes.setdefault(current, [])
        elif current and line.startswith("+") and not line.startswith("+++"):
            changes[current].append(line[1:])
    for path in _git(cwd, "ls-files", "--others", "--exclude-standard").splitlines():
        try:
            text = (cwd / path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        changes[path] = text.splitlines()
    for path in changes:
        fp = cwd / path
        if fp.suffix == ".py" and fp.is_file():
            try:
                contents[path] = fp.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                pass
    return changes, contents


def classify_workspace(cwd: Path, base: Optional[str] = None) -> Dict[str, Any]:
    """Level and metrics for the change in a git workspace."""
    changes, contents = workspace_changes(Path(cwd), base)
    m = metrics_from_changes(changes, contents)
    return {"level": classify(m), "metrics": m.to_dict()}


def cohen_kappa(labels_a: Iterable[str], labels_b: Iterable[str]) -> Dict[str, Any]:
    """Cohen's kappa (unweighted) and linear-weighted kappa for two raters over the same items."""
    a, b = list(labels_a), list(labels_b)
    if len(a) != len(b) or not a:
        raise ValueError("kappa needs two equal, non-empty label lists")
    cats = sorted(set(a) | set(b), key=lambda c: (LEVELS.index(c) if c in LEVELS else 99, c))
    n = len(a)
    idx = {c: i for i, c in enumerate(cats)}
    k = len(cats)
    obs = [[0.0] * k for _ in range(k)]
    for x, y in zip(a, b):
        obs[idx[x]][idx[y]] += 1.0 / n
    pa = [sum(obs[i]) for i in range(k)]
    pb = [sum(obs[i][j] for i in range(k)) for j in range(k)]
    po = sum(obs[i][i] for i in range(k))
    pe = sum(pa[i] * pb[i] for i in range(k))
    kappa = 1.0 if pe >= 1.0 else (po - pe) / (1.0 - pe)
    if k > 1:
        w = [[1.0 - abs(i - j) / (k - 1) for j in range(k)] for i in range(k)]
        pow_ = sum(w[i][j] * obs[i][j] for i in range(k) for j in range(k))
        pew = sum(w[i][j] * pa[i] * pb[j] for i in range(k) for j in range(k))
        kw = 1.0 if pew >= 1.0 else (pow_ - pew) / (1.0 - pew)
    else:
        kw = 1.0
    disagreements = [i for i, (x, y) in enumerate(zip(a, b)) if x != y]
    return {"n": n, "kappa": round(kappa, 4), "weighted_kappa": round(kw, 4), "agreement": round(po, 4), "disagreements": disagreements}
