"""#605: the fileset ships the canonical lifecycle factories, and the pre-push hook enforces the verified gate."""

from __future__ import annotations

import importlib.util
import subprocess
import tarfile
from pathlib import Path

from hath0r_cli.bots.task_evaluator_bot import (
    TaskEvaluatorBot,
    _hook_is_replaceable,
    _is_stock_lfs_hook,
    _pre_push_hook_script,
)

ROOT = Path(__file__).resolve().parents[1]
STOCK_LFS_HOOK = (
    "#!/bin/sh\n"
    "command -v git-lfs >/dev/null 2>&1 || { printf >&2 \"\\n%s\\n\\n\" \"missing git-lfs\"; exit 2; }\n"
    'git lfs pre-push "$@"\n'
)


def _load_build_fileset():
    spec = importlib.util.spec_from_file_location("build_fileset", ROOT / "scripts" / "build_fileset.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_fileset_factories_match_canonical(tmp_path: Path) -> None:
    mod = _load_build_fileset()
    tar_path = mod.build(tmp_path, "hath0r-member", None)
    with tarfile.open(tar_path) as tar:
        names = tar.getnames()
        for name in mod.CANONICAL_FACTORIES:
            member = next(n for n in names if n.endswith(f"/cfg/factories/{name}"))
            extracted = tar.extractfile(member)
            assert extracted is not None
            assert extracted.read() == (ROOT / "cfg" / "factories" / name).read_bytes(), name


def test_fileset_templates_hold_no_factory_copies() -> None:
    assert not list((ROOT / "packaging" / "fileset" / "templates" / "cfg").glob("factories/*.yaml"))


def test_hook_runs_evals_and_andon() -> None:
    script = _pre_push_hook_script(lfs=False)
    assert "hath0r evals verify --auto-run" in script
    assert "hath0r andon status" in script
    assert 'git lfs pre-push "$@"' not in script
    assert subprocess.run(["bash", "-n"], input=script, text=True).returncode == 0


def test_hook_chains_lfs() -> None:
    script = _pre_push_hook_script(lfs=True)
    assert 'printf \'%s\\n\' "$refs" | git lfs pre-push "$@"' in script
    assert subprocess.run(["bash", "-n"], input=script, text=True).returncode == 0


def test_replaceable_hooks() -> None:
    assert _is_stock_lfs_hook(STOCK_LFS_HOOK)
    assert _hook_is_replaceable("")
    assert _hook_is_replaceable(STOCK_LFS_HOOK)
    assert _hook_is_replaceable(_pre_push_hook_script(lfs=False))
    assert not _hook_is_replaceable("#!/bin/sh\nnpm test\n")


def _repo(tmp_path: Path, hook: str | None) -> Path:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    if hook is not None:
        (tmp_path / ".git" / "hooks" / "pre-push").write_text(hook, encoding="utf-8")
    return tmp_path


def test_ensure_merges_stock_lfs_hook(tmp_path: Path) -> None:
    repo = _repo(tmp_path, STOCK_LFS_HOOK)
    TaskEvaluatorBot(cwd=repo).ensure_repo_eval_setup(run_eval=False, sync_agents_md=False)
    hook = (repo / ".git" / "hooks" / "pre-push").read_text(encoding="utf-8")
    assert "CR-TASK-EVAL-001" in hook
    assert "hath0r andon status" in hook
    assert "git lfs pre-push" in hook


def test_ensure_leaves_custom_hook(tmp_path: Path) -> None:
    custom = "#!/bin/sh\nnpm test\n"
    repo = _repo(tmp_path, custom)
    TaskEvaluatorBot(cwd=repo).ensure_repo_eval_setup(run_eval=False, sync_agents_md=False)
    assert (repo / ".git" / "hooks" / "pre-push").read_text(encoding="utf-8") == custom
