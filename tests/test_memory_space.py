"""Tests for Local Memory Space, MemoryGraph compounding, and pre-announcement gate (CR-MEMORY-COMPOUND-001)."""

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from click.testing import CliRunner

from hath0r_cli.bots import TaskAnnouncerBot
from hath0r_cli.bots.memory_manager import MemoryManagerBot
from hath0r_cli.cli import main


def test_memory_manager_bot_init_and_read(tmp_path: Path) -> None:
    bot = MemoryManagerBot(cwd=tmp_path)
    init_res = bot.init_memory()
    assert init_res["success"] is True

    rules_content = bot.read_topic("rules")
    assert rules_content is not None
    assert "CR-CLI-ENTRY-001" in rules_content
    assert "CR-MEMORY-COMPOUND-001" in rules_content

    arch_content = bot.read_topic("architecture")
    assert arch_content is not None
    assert "HATH0R" in arch_content


def test_memory_manager_bot_update(tmp_path: Path) -> None:
    bot = MemoryManagerBot(cwd=tmp_path)
    bot.init_memory()

    update_res = bot.update_topic("custom_topic", "custom content for testing")
    assert update_res["success"] is True

    read_back = bot.read_topic("custom_topic")
    assert read_back == "custom content for testing"


def test_memory_compounding_and_pre_announcement_gate(tmp_path: Path) -> None:
    bot = MemoryManagerBot(cwd=tmp_path)
    bot.initialize_memory()
    announcer = TaskAnnouncerBot(cwd=tmp_path)

    # Gate fails before any task knowledge is compounded
    ver_before = bot.verify_compounded()
    assert ver_before["compounded"] is False
    ann_blocked = announcer.announce_complete(task_id="issue-472", dry_run=False)
    assert ann_blocked["success"] is False
    assert "CR-MEMORY-COMPOUND-001" in str(ann_blocked.get("error"))

    # Compound first episode
    c1 = bot.compound_memory(
        label="Enforce .hath0r/memory across all repos",
        content="Added compound, verify, reflect, and ensure-all to MemoryManagerBot.",
        node_type="episode",
        tags=["memorygraph", "governance"],
        sync_agentgraph=False,
    )
    assert c1["success"] is True

    # Gate now passes and TaskAnnouncerBot succeeds
    ver_after = bot.verify_compounded()
    assert ver_after["compounded"] is True
    ann_passed = announcer.announce_complete(task_id="issue-472", dry_run=False)
    assert ann_passed["success"] is True

    # Compound second decision sharing tag 'memorygraph' -> synthesizes insight node
    c2 = bot.compound_memory(
        label="Pre-Announcement Gate Decision",
        content="TaskAnnouncerBot blocks announcement until verify_compounded passes.",
        node_type="decision",
        tags=["memorygraph", "governance"],
        sync_agentgraph=False,
    )
    assert c2["success"] is True
    assert c2["reflection"]["insights_generated"] >= 1


def test_ensure_all_repos(tmp_path: Path) -> None:
    repo_a = tmp_path / "repo-alpha"
    repo_b = tmp_path / "repo-beta"
    (repo_a / ".git").mkdir(parents=True)
    (repo_b / ".git").mkdir(parents=True)
    (repo_a / "README.md").write_text("# Repo Alpha\nAlpha service repository.", encoding="utf-8")

    bot = MemoryManagerBot(cwd=tmp_path)
    res = bot.ensure_all_repos(root_dir=tmp_path, sync_agentgraph=False)
    assert res["success"] is True
    assert res["repos_count"] == 2
    assert (repo_a / ".hath0r" / "memory" / "graph.json").is_file()
    assert (repo_b / ".hath0r" / "memory" / "graph.json").is_file()


def test_memory_cli_commands(tmp_path: Path) -> None:
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        res_init = runner.invoke(main, ["memory", "init"])
        assert res_init.exit_code == 0
        assert "Initialized" in res_init.output or "Local Memory Space" in res_init.output

        # Verify fails before compounding
        res_ver_fail = runner.invoke(main, ["memory", "verify"])
        assert res_ver_fail.exit_code != 0

        # Compound via CLI
        res_comp = runner.invoke(
            main,
            [
                "memory",
                "compound",
                "--label",
                "CLI Compounding Test",
                "--content",
                "Verified CLI memory compound command.",
                "--type",
                "episode",
                "--tags",
                "cli,memorygraph",
                "--no-sync",
            ],
        )
        assert res_comp.exit_code == 0

        # Verify passes after compounding
        res_ver_ok = runner.invoke(main, ["memory", "verify"])
        assert res_ver_ok.exit_code == 0
        assert "PASSED" in res_ver_ok.output or '"compounded":' in res_ver_ok.output

        res_read = runner.invoke(main, ["memory", "read", "rules"])
        assert res_read.exit_code == 0
        assert "Rules" in res_read.output or "CR-CLI-ENTRY-001" in res_read.output


def test_micro_memory_session_lifecycle_and_budget(tmp_path: Path) -> None:
    bot = MemoryManagerBot(cwd=tmp_path)
    bot.initialize_memory()

    # Start first session
    s1 = bot.session_start(
        focus="Micro Memory Session Implementation",
        session_id="session:test-001",
        task_id="issue-474",
        role="developer",
        force_new=True,
    )
    assert s1["success"] is True
    assert s1["session"]["session_id"] == "session:test-001"
    assert s1["session"]["read_count"] >= 1

    # Read session
    r1 = bot.session_read(note="Reading micro session capsule")
    assert r1["success"] is True
    assert r1["session"]["read_count"] >= 2

    # Write multiple micro entries to exercise <2KB budget enforcement
    for idx in range(18):
        w_res = bot.session_write(
            kind="finding",
            summary=f"Finding #{idx}: verifying micro-session capsule stays under 2048 bytes budget.",
            tags=["session", f"item-{idx}"],
        )
        assert w_res["success"] is True
        assert w_res["session"]["capsule_bytes"] <= bot.MAX_SESSION_CAPSULE_BYTES

    # End first session
    e1 = bot.session_end(summary="Completed first micro session", sync_agentgraph=False)
    assert e1["success"] is True
    assert e1["session"]["status"] == "completed"

    # Start second session and verify parent_session_id + PRECEDES edge in graph.json
    s2 = bot.session_start(
        focus="Follow-up Micro Session",
        session_id="session:test-002",
        force_new=True,
    )
    assert s2["success"] is True
    assert s2["session"]["parent_session_id"] == "session:test-001"
    bot.session_write(kind="decision", summary="Verified PRECEDES lineage edge between sessions.")

    graph = bot._load_graph()
    precedes_edges = [
        e
        for e in graph.get("edges", [])
        if e.get("relation") == "PRECEDES"
        and e.get("source") == "session:test-001"
        and e.get("target") == "session:test-002"
    ]
    assert len(precedes_edges) == 1

    st = bot.session_status()
    assert st["success"] is True
    assert st["read_verified"] is True
    assert st["write_verified"] is True


def test_memory_cli_session_subcommands(tmp_path: Path) -> None:
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        res_start = runner.invoke(
            main,
            ["memory", "session", "start", "--focus", "CLI Session Test", "--id", "session:cli-1", "--new"],
        )
        assert res_start.exit_code == 0

        res_read = runner.invoke(main, ["memory", "session", "read", "--note", "CLI session read check"])
        assert res_read.exit_code == 0

        res_write = runner.invoke(
            main,
            [
                "memory",
                "session",
                "write",
                "--kind",
                "decision",
                "--summary",
                "Recorded micro-session write via CLI",
                "--tags",
                "cli,session",
            ],
        )
        assert res_write.exit_code == 0

        res_status = runner.invoke(main, ["memory", "session", "status"])
        assert res_status.exit_code == 0

        res_end = runner.invoke(
            main,
            ["memory", "session", "end", "--summary", "Finished CLI session test", "--no-sync"],
        )
        assert res_end.exit_code == 0


def test_file_hashing_source_staleness_and_cas_conflict(tmp_path: Path) -> None:
    src_file = tmp_path / "src" / "service.py"
    src_file.parent.mkdir(parents=True)
    src_file.write_text("def handle():\n    return 1\n", encoding="utf-8")

    bot = MemoryManagerBot(cwd=tmp_path)
    bot.initialize_memory()

    # Compound knowledge referencing src/service.py
    comp = bot.compound_memory(
        node_id="episode:hash-test",
        label="Hash Test Episode",
        content="Verified source_files SHA-256 tracking.",
        source_files=["src/service.py"],
        sync_agentgraph=False,
    )
    assert comp["success"] is True
    assert (tmp_path / ".hath0r" / "memory" / "hashes.json").is_file()

    # Hashes and pre-announcement gate verify cleanly
    h_ok = bot.verify_file_hashes()
    assert h_ok["verified"] is True
    ver_ok = bot.verify_compounded()
    assert ver_ok["compounded"] is True
    assert ver_ok["hashes_verified"] is True

    # Mutate src/service.py on disk -> verify_file_hashes & verify_compounded detect stale source file
    src_file.write_text("def handle():\n    return 2\n", encoding="utf-8")
    h_stale = bot.verify_file_hashes()
    assert h_stale["verified"] is False
    assert len(h_stale["stale_source_files"]) == 1
    assert h_stale["stale_source_files"][0]["file"] == "src/service.py"
    ver_stale = bot.verify_compounded()
    assert ver_stale["compounded"] is False
    assert ver_stale["hashes_verified"] is False

    # Sync file hashes with refresh_source_files=True -> restores valid state
    bot.sync_file_hashes(refresh_source_files=True)
    assert bot.verify_file_hashes()["verified"] is True
    assert bot.verify_compounded()["compounded"] is True

    # Concurrent non-conflicting additions from two bot instances auto-merge cleanly
    bot_a = MemoryManagerBot(cwd=tmp_path)
    bot_b = MemoryManagerBot(cwd=tmp_path)
    bot_a._load_graph()
    bot_b._load_graph()

    res_a = bot_a.compound_memory(
        node_id="fact:concurrent-a",
        node_type="fact",
        label="Concurrent Fact A",
        content="Added by bot A.",
        sync_agentgraph=False,
    )
    res_b = bot_b.compound_memory(
        node_id="fact:concurrent-b",
        node_type="fact",
        label="Concurrent Fact B",
        content="Added by bot B.",
        sync_agentgraph=False,
    )
    assert res_a["success"] is True
    assert res_b["success"] is True
    merged_ids = {n["id"] for n in bot._load_graph()["nodes"]}
    assert "fact:concurrent-a" in merged_ids
    assert "fact:concurrent-b" in merged_ids

    # Explicit stale expected_hash fails with HASH_CONFLICT
    bad_cas = bot.compound_memory(
        node_id="fact:bad-cas",
        node_type="fact",
        label="Bad CAS",
        content="Should fail CAS check.",
        expected_hash="sha256:0000000000000000000000000000000000000000000000000000000000000000",
        sync_agentgraph=False,
    )
    assert bad_cas["success"] is False
    assert bad_cas.get("error_code") == "HASH_CONFLICT"


def test_memory_cli_hash_subcommand(tmp_path: Path) -> None:
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        Path("README.md").write_text("# Test Repo\n", encoding="utf-8")
        runner.invoke(main, ["memory", "init"])
        res_comp = runner.invoke(
            main,
            [
                "memory",
                "compound",
                "--label",
                "Hash CLI Test",
                "--content",
                "Testing hath0r memory hash CLI.",
                "--source-file",
                "README.md",
                "--no-sync",
            ],
        )
        assert res_comp.exit_code == 0

        res_check = runner.invoke(main, ["memory", "hash", "--check"])
        assert res_check.exit_code == 0

        # Modify README.md -> hash --check fails
        Path("README.md").write_text("# Test Repo Updated\n", encoding="utf-8")
        res_check_fail = runner.invoke(main, ["memory", "hash", "--check"])
        assert res_check_fail.exit_code != 0

        # Sync hashes -> hash --check passes again
        res_sync = runner.invoke(main, ["memory", "hash", "--sync"])
        assert res_sync.exit_code == 0
        res_check_ok = runner.invoke(main, ["memory", "hash", "--check"])
        assert res_check_ok.exit_code == 0


def test_memory_manager_unignores_graph_folders_in_gitignore(tmp_path: Path) -> None:
    import subprocess

    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    gitignore = tmp_path / ".gitignore"
    gitignore.write_text(
        ".hath0r/state/\n"
        ".hath0r/agentgraph/\n"
        ".hath0r/*.json\n",
        encoding="utf-8",
    )

    bot = MemoryManagerBot(cwd=tmp_path)
    bad = bot.verify_graphs_not_gitignored()
    assert bad["graphs_not_ignored"] is False
    assert len(bad["ignored_paths"]) > 0

    bot.initialize_memory()
    good = bot.verify_graphs_not_gitignored()
    assert good["graphs_not_ignored"] is True
    assert good["ignored_paths"] == []


def test_hashes_manifest_monotonic_revisions_and_cas(tmp_path: Path) -> None:
    src_file = tmp_path / "src" / "svc.py"
    src_file.parent.mkdir(parents=True)
    src_file.write_text("x = 1\n", encoding="utf-8")

    bot = MemoryManagerBot(cwd=tmp_path)
    bot.initialize_memory()
    bot.sync_file_hashes(track_files=["src/svc.py"])
    first = bot.sync_file_hashes()
    manifest = first["manifest"]
    rules_rev = manifest["files"][".hath0r/memory/core_rules.md"]["revision"]
    src_rev = manifest["source_files"]["src/svc.py"]["revision"]
    assert manifest["files"][".hath0r/memory/core_rules.md"]["sha256"].startswith("sha256:")

    # Unchanged files keep their revision; changed files bump it monotonically
    again = bot.sync_file_hashes()["manifest"]
    assert again["files"][".hath0r/memory/core_rules.md"]["revision"] == rules_rev
    (tmp_path / ".hath0r" / "memory" / "core_rules.md").write_text("# Changed\n", encoding="utf-8")
    src_file.write_text("x = 2\n", encoding="utf-8")
    bumped = bot.sync_file_hashes(refresh_source_files=True)["manifest"]
    assert bumped["files"][".hath0r/memory/core_rules.md"]["revision"] == rules_rev + 1
    assert bumped["source_files"]["src/svc.py"]["revision"] == src_rev + 1

    # CAS on hashes.json: correct expected_revision succeeds, stale one is refused untouched
    current_rev = bumped["revision"]
    ok = bot.sync_file_hashes(expected_revision=current_rev)
    assert ok["success"] is True
    assert ok["revision"] == current_rev + 1
    stale = bot.sync_file_hashes(expected_revision=current_rev)
    assert stale["success"] is False
    assert stale["error_code"] == "HASH_CONFLICT"
    assert stale["actual_revision"] == current_rev + 1
    on_disk = json.loads((tmp_path / ".hath0r" / "memory" / "hashes.json").read_text(encoding="utf-8"))
    assert on_disk["revision"] == current_rev + 1


def test_update_memory_topic_cas(tmp_path: Path) -> None:
    bot = MemoryManagerBot(cwd=tmp_path)
    bot.initialize_memory()

    # New topic: "absent" is the expected hash for a file that does not exist yet
    created = bot.update_memory("ops", "# Ops\nv1\n", expected_hash="absent")
    assert created["success"] is True
    v1_hash = bot.read_memory("ops")["sha256"]
    assert v1_hash == created["sha256"]

    updated = bot.update_memory("ops", "# Ops\nv2\n", expected_hash=v1_hash)
    assert updated["success"] is True

    # A writer still holding the v1 hash is refused and the file is left as v2
    stale = bot.update_memory("ops", "# Ops\nlost update\n", expected_hash=v1_hash)
    assert stale["success"] is False
    assert stale["error_code"] == "HASH_CONFLICT"
    assert "v2" in bot.read_memory("ops")["content"]


def test_concurrent_compounds_across_threads_do_not_lose_nodes(tmp_path: Path) -> None:
    MemoryManagerBot(cwd=tmp_path).initialize_memory()

    def _worker(i: int) -> bool:
        b = MemoryManagerBot(cwd=tmp_path)
        b._load_graph()
        res = b.compound_memory(
            node_id=f"fact:thread-{i}",
            node_type="fact",
            label=f"Thread {i}",
            content=f"Added by thread {i}.",
            sync_agentgraph=False,
        )
        return bool(res.get("success"))

    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(_worker, range(6)))
    assert all(results)

    bot = MemoryManagerBot(cwd=tmp_path)
    ids = {n["id"] for n in bot._load_graph()["nodes"]}
    assert {f"fact:thread-{i}" for i in range(6)} <= ids
    assert bot.verify_file_hashes()["verified"] is True


def test_memory_cli_hash_and_update_cas_flags(tmp_path: Path) -> None:
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        runner.invoke(main, ["memory", "init"])
        rev = json.loads(Path(".hath0r/memory/hashes.json").read_text(encoding="utf-8"))["revision"]

        res_stale = runner.invoke(main, ["memory", "hash", "--sync", "--expected-revision", str(rev - 1)])
        assert res_stale.exit_code != 0
        res_ok = runner.invoke(main, ["memory", "hash", "--sync", "--expected-revision", str(rev)])
        assert res_ok.exit_code == 0

        res_bad = runner.invoke(
            main, ["memory", "update", "notes", "# Notes\n", "--expected-hash", "sha256:" + "0" * 64]
        )
        assert res_bad.exit_code != 0
        assert not Path(".hath0r/memory/notes.md").exists()
        res_new = runner.invoke(main, ["memory", "update", "notes", "# Notes\n", "--expected-hash", "absent"])
        assert res_new.exit_code == 0


def test_gitignore_negations_relocated_after_later_ignore_rule(tmp_path: Path) -> None:
    import subprocess

    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    bot = MemoryManagerBot(cwd=tmp_path)
    bot.ensure_gitignore_unignores_graphs()
    gitignore = tmp_path / ".gitignore"
    gitignore.write_text(gitignore.read_text(encoding="utf-8") + "*.json\n\n", encoding="utf-8")
    assert bot.verify_graphs_not_gitignored()["graphs_not_ignored"] is False

    res = bot.ensure_gitignore_unignores_graphs()
    assert res["relocated_negations"] is True
    lines = [ln.strip() for ln in gitignore.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert lines.index("*.json") < lines.index("!.hath0r/memory/**")
    assert bot.verify_graphs_not_gitignored()["graphs_not_ignored"] is True

    again = bot.ensure_gitignore_unignores_graphs()
    assert again["updated"] is False
    assert again["relocated_negations"] is False


def test_ensure_all_repos_reports_graphs_not_ignored(tmp_path: Path) -> None:
    import subprocess

    for name in ("repo-alpha", "repo-beta"):
        repo = tmp_path / name
        repo.mkdir()
        subprocess.run(["git", "init", str(repo)], check=True, capture_output=True)
        (repo / ".gitignore").write_text(".hath0r/\n.hath0r/agentgraph/\n", encoding="utf-8")

    res = MemoryManagerBot(cwd=tmp_path).ensure_all_repos(root_dir=tmp_path, sync_agentgraph=False)
    assert res["repos_count"] == 2
    assert res["graphs_not_ignored"] is True
    assert res["ignored_repos"] == []
    assert all(r["graphs_not_ignored"] for r in res["repos"])
