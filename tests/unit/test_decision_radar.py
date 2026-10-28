"""Comprehensive unit and integration tests for Hath0r Decision Radar (Epic #499, Tasks #500-#506)."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path

import jsonschema
import pytest
from click.testing import CliRunner

from hath0r_cli.bots.decision_radar_bot import (
    CANONICAL_CATEGORIES,
    CASConflictError,
    DecisionGraph,
    DecisionRadarBot,
)
from hath0r_cli.bots.memory_manager import MemoryManagerBot
from hath0r_cli.commands.decision import decision_cmd
from hath0r_cli.server.decision_radar_server import HathorDecisionRadarServer, render_radar_tui


def test_decision_contract_schema_validation(tmp_path: Path) -> None:
    """Task 1 (#500): Verify generated decision records conform to hath0r-decision-spec-v1.schema.json."""
    schema_path = Path(__file__).resolve().parents[2] / "contracts" / "hath0r-decision-spec-v1.schema.json"
    assert schema_path.is_file()
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    bot = DecisionRadarBot(cwd=tmp_path)
    res = bot.request_decision(
        question="Confirm Parts-API build order: Widget search before index",
        category="set_product_rule",
        agent_id="@a3740",
        unblocks=["@a6440", "@a9094", "search-indexer"],
        options=["Widget search first", "Index first"],
        wait_for_fact="git.pr.merged:Bayly-AI/HATH0R-CLI#499",
        criticality=2.0,
    )
    assert res["success"] is True
    decision = res["decision"]
    jsonschema.validate(instance=decision, schema=schema)


def test_decision_graph_transitive_unblocking_and_cycles() -> None:
    """Task 2 (#501): Verify DAG transitive closure, impact scoring U(d), topological sort, and cycle detection."""
    graph = DecisionGraph()
    graph.add_task_dependency("task-a", "task-b", weight=1.5, criticality=2.0)
    graph.add_task_dependency("task-b", "task-c", weight=2.0, criticality=1.5)
    graph.add_decision("dec-root", "@a1", unblocks=["task-a"], criticality=2.0)
    graph.add_decision("dec-leaf", "@a2", unblocks=["task-c"], criticality=1.0)

    assert graph.has_cycle() is False
    topo = graph.topological_order()
    assert topo.index("task-a") < topo.index("task-b") < topo.index("task-c")

    root_trans = graph.get_transitive_unblocked("dec-root")
    assert root_trans == {"task-a", "task-b", "task-c"}

    root_impact = graph.compute_unblock_impact("dec-root", base_criticality=2.0)
    leaf_impact = graph.compute_unblock_impact("dec-leaf", base_criticality=1.0)
    assert root_impact["unblock_weight"] > leaf_impact["unblock_weight"]
    assert root_impact["transitive_unblocked_count"] == 3
    assert root_impact["priority_tier"] in ("P0", "P1")
    assert DecisionGraph.classify_priority_tier(0.5, 0) == "P3"

    # Introduce cycle and verify detection
    graph.add_task_dependency("task-c", "task-a")
    assert graph.has_cycle() is True
    assert graph.topological_order() == []


def test_cas_concurrency_conflict_prevention(tmp_path: Path) -> None:
    """Task 1 (#500): Verify optimistic Compare-And-Swap raises CASConflictError on stale expected_hash."""
    bot = DecisionRadarBot(cwd=tmp_path)
    bot.request_decision(question="Initial question", agent_id="@a1")
    with pytest.raises(CASConflictError):
        bot.request_decision(
            question="Conflicting question",
            agent_id="@a2",
            expected_hash="0000000000000000000000000000000000000000000000000000000000000000",
        )


def test_fact_settlement_engine_probes_and_auto_settle(tmp_path: Path) -> None:
    """Task 3 (#502): Verify declarative fact predicates auto-settle waiting decisions without human input."""
    mem_bot = MemoryManagerBot(cwd=tmp_path)
    mem_bot.initialize_memory()
    mem_bot.compound_memory(
        label="Database Schema V2 Approved",
        content="Canonical schema v2 finalized.",
        node_type="fact",
        node_id="fact:db-schema-v2",
    )

    bot = DecisionRadarBot(cwd=tmp_path)

    # 1. File existence fact
    marker = tmp_path / "artifact_ready.txt"
    r1 = bot.request_decision(
        question="Wait for build artifact file",
        category="accept_delivered_work",
        agent_id="@a101",
        wait_for_fact="file.exists:artifact_ready.txt",
    )
    # 2. Memory fact asserted
    r2 = bot.request_decision(
        question="Wait for DB schema v2 memory fact",
        category="set_product_rule",
        agent_id="@a102",
        wait_for_fact="memory.fact.asserted:fact:db-schema-v2",
    )
    # 3. PR merged fact
    r3 = bot.request_decision(
        question="Wait for PR #499 merge",
        category="start_hold_work",
        agent_id="@a103",
        wait_for_fact="git.pr.merged:Bayly-AI/HATH0R-CLI#499",
    )
    # 4. Dependent on agent @a102 completion
    r4 = bot.request_decision(
        question="Wait for @a102 completion",
        category="keep_ledger_true",
        agent_id="@a104",
        wait_for_fact="agent.task.completed:@a102",
    )

    # Create the file so r1, r2, and cascading r4 settle
    marker.write_text("ready\n", encoding="utf-8")
    settle_res = bot.evaluate_and_settle_facts(live_probes=False)
    settled_ids = {it["decision_id"] for it in settle_res["settled"]}
    assert r1["decision"]["decision_id"] in settled_ids
    assert r2["decision"]["decision_id"] in settled_ids
    assert r4["decision"]["decision_id"] in settled_ids
    assert r3["decision"]["decision_id"] not in settled_ids

    # Now assert PR merged fact via event bus and verify r3 auto-settles
    assert_res = bot.assert_fact("git.pr.merged:Bayly-AI/HATH0R-CLI#499", reason="Merged by CI")
    assert assert_res["settled_count"] == 1
    assert assert_res["settled"][0]["decision_id"] == r3["decision"]["decision_id"]
    assert assert_res["settled"][0]["status"] == "SETTLED_BY_EVENT"

    # Custom probe registration test
    bot.fact_engine.register_probe("custom.probe", lambda arg: (arg == "ready", f"Custom probe {arg}"))
    ok, msg = bot.fact_engine.evaluate_predicate("custom.probe:ready")
    assert ok is True
    assert "Custom probe ready" in msg

    # Test additional built-in probes
    bot.assert_fact("ci.workflow.passed:main-ci", auto_settle=False)
    bot.assert_fact("endpoint.health.ok:https://mcp.hath0r-cli.com/health", auto_settle=False)
    assert bot.fact_engine.evaluate_predicate("ci.workflow.passed:main-ci")[0] is True
    assert bot.fact_engine.evaluate_predicate("endpoint.health.ok:https://mcp.hath0r-cli.com/health")[0] is True
    assert bot.fact_engine.evaluate_predicate("git.commit.exists:HEAD", live_probes=False)[0] is False


def test_bidirectional_work_boundary_gates_and_hmac(tmp_path: Path) -> None:
    """Task 4 (#503): Verify Input ('what goes in') and Output ('what comes out') approval gates & HMAC tokens."""
    bot = DecisionRadarBot(cwd=tmp_path)

    in_req = bot.create_input_gate(
        agent_id="@p4010",
        intent="Parts-API v3 GraphQL migration",
        token_budget=50000,
        tools=["read_file", "edit_file"],
        unblocks=["gql-schema", "gql-resolvers"],
    )
    in_id = in_req["decision"]["decision_id"]
    assert in_req["decision"]["category"] == "start_hold_work"
    assert in_req["decision"]["work_boundary"] == "INPUT"

    ans_in = bot.answer_decision(in_id, answer="Approve Input Gate", operator="Mark")
    assert ans_in["success"] is True
    in_dec = ans_in["decision"]
    in_sig = in_dec["boundary_payload"]["hmac_signature"]
    assert in_sig is not None
    assert bot.gate.verify_gate_signature(
        decision_id=in_id,
        agent_id="@p4010",
        boundary="INPUT",
        operator="Mark",
        payload={k: v for k, v in in_dec["boundary_payload"].items() if k != "hmac_signature"},
        signature=in_sig,
    )

    out_req = bot.create_output_gate(
        agent_id="drv-c9cdf6d8",
        summary="Widget proof & contract tests",
        diff_summary="+140 -12 lines across 4 files",
        pr_draft="feat: widget proof",
        unblocks=["release-1.8"],
    )
    out_id = out_req["decision"]["decision_id"]
    assert out_req["decision"]["category"] == "accept_delivered_work"
    assert out_req["decision"]["work_boundary"] == "OUTPUT"

    ans_out = bot.answer_decision(out_id, answer="Accept & Sign Off", operator="Mark")
    assert ans_out["success"] is True
    assert ans_out["decision"]["boundary_payload"]["hmac_signature"] is not None
    assert (tmp_path / ".hath0r" / "decisions" / "ledger.json").is_file()


def test_radar_snapshot_and_tui_rendering(tmp_path: Path) -> None:
    """Task 6 (#505): Verify polar radial sunburst geometry, 7 canonical wedges, and Rich TUI output."""
    bot = DecisionRadarBot(cwd=tmp_path)
    snap = bot.seed_demo_radar()
    assert snap["operator"]["name"] == "Mark"
    assert snap["operator"]["open_count"] == 16
    assert len(snap["wedges"]) == len(CANONICAL_CATEGORIES)

    for wedge in snap["wedges"]:
        assert wedge["decision_count"] >= 1
        for node in wedge["nodes"]:
            assert "polar" in node
            assert 200.0 <= node["polar"]["radius"] <= 400.0

    tui_text = render_radar_tui(snap)
    assert "HATH0R DECISION RADAR" in tui_text
    assert "Only you can do this" in tui_text
    assert "@a11062" in tui_text


def test_decision_radar_http_and_sse_server(tmp_path: Path) -> None:
    """Task 6 (#505): Verify embedded HTTP server endpoints and SSE stream."""
    server = HathorDecisionRadarServer(host="127.0.0.1", port=0, cwd=tmp_path, operator_name="Mark")
    port = server.start(daemon=True)
    base_url = f"http://127.0.0.1:{port}"

    try:
        # 1. GET /radar HTML
        with urllib.request.urlopen(f"{base_url}/radar", timeout=3) as resp:
            html = resp.read().decode("utf-8")
            assert resp.status == 200
            assert "HATH0R DECISION RADAR" in html

        # 2. POST /api/decisions/request
        req_data = json.dumps(
            {
                "question": "Approve production deploy?",
                "category": "only_you_can_do_this",
                "agent_id": "@a9999",
                "unblocks": ["prod-deploy", "smoke-verify"],
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            f"{base_url}/api/decisions/request",
            data=req_data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=3) as resp:
            created = json.loads(resp.read().decode("utf-8"))
            assert created["success"] is True
            dec_id = created["decision"]["decision_id"]

        # 3. POST /api/decisions/snooze
        snooze_data = json.dumps({"decision_id": dec_id, "fact_predicate": "ci.workflow.passed:deploy"}).encode("utf-8")
        s_req = urllib.request.Request(
            f"{base_url}/api/decisions/snooze",
            data=snooze_data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(s_req, timeout=3) as resp:
            s_res = json.loads(resp.read().decode("utf-8"))
            assert s_res["decision"]["status"] == "WAITING_FACT"

        # 4. GET /api/decisions/stream (SSE)
        with urllib.request.urlopen(f"{base_url}/api/decisions/stream", timeout=3) as resp:
            raw_sse = resp.read().decode("utf-8")
            assert "data: " in raw_sse

        # 5. POST /api/decisions/assert-fact
        fact_data = json.dumps({"fact_predicate": "ci.workflow.passed:deploy"}).encode("utf-8")
        f_req = urllib.request.Request(
            f"{base_url}/api/decisions/assert-fact",
            data=fact_data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(f_req, timeout=3) as resp:
            f_res = json.loads(resp.read().decode("utf-8"))
            assert f_res["settled_count"] == 1

        # 6. POST /api/decisions/seed, answer, reject, settle
        seed_req = urllib.request.Request(f"{base_url}/api/decisions/seed", data=b"{}", method="POST")
        with urllib.request.urlopen(seed_req, timeout=3) as resp:
            seed_payload = json.loads(resp.read().decode("utf-8"))
            first_id = seed_payload["snapshot"]["decisions"][0]["decision_id"]
            second_id = seed_payload["snapshot"]["decisions"][1]["decision_id"]

        ans_req = urllib.request.Request(
            f"{base_url}/api/decisions/answer",
            data=json.dumps({"decision_id": first_id, "answer": "Proceed"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(ans_req, timeout=3) as resp:
            assert json.loads(resp.read().decode("utf-8"))["success"] is True

        rej_req = urllib.request.Request(
            f"{base_url}/api/decisions/reject",
            data=json.dumps({"decision_id": second_id, "reason": "Out of scope"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(rej_req, timeout=3) as resp:
            assert json.loads(resp.read().decode("utf-8"))["success"] is True

        settle_req = urllib.request.Request(f"{base_url}/api/decisions/settle", data=b"{}", method="POST")
        with urllib.request.urlopen(settle_req, timeout=3) as resp:
            assert json.loads(resp.read().decode("utf-8"))["success"] is True

    finally:
        server.stop()


def test_cli_decision_commands(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 5 (#504): Verify all hath0r decision CLI subcommands in text and --json modes."""
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    # 1. dep
    res_dep = runner.invoke(decision_cmd, ["dep", "--from", "t1", "--to", "t2", "--json"])
    assert res_dep.exit_code == 0
    assert json.loads(res_dep.output)["success"] is True

    # 2. ask
    res_ask = runner.invoke(
        decision_cmd,
        [
            "ask",
            "-q",
            "Approve Parts-API v2 schema",
            "-c",
            "set_product_rule",
            "-a",
            "@a500",
            "-u",
            "t1",
            "--json",
        ],
    )
    assert res_ask.exit_code == 0
    dec_id = json.loads(res_ask.output)["decision"]["decision_id"]

    # 3. list
    res_list = runner.invoke(decision_cmd, ["list"])
    assert res_list.exit_code == 0
    assert dec_id in res_list.output

    # 4. snooze on fact
    res_snooze = runner.invoke(decision_cmd, ["snooze", dec_id, "--fact", "git.pr.merged:500", "--json"])
    assert res_snooze.exit_code == 0
    assert json.loads(res_snooze.output)["decision"]["status"] == "WAITING_FACT"

    # 5. assert-fact -> auto-settles dec_id
    res_fact = runner.invoke(decision_cmd, ["assert-fact", "git.pr.merged:500", "--json"])
    assert res_fact.exit_code == 0
    assert json.loads(res_fact.output)["settled_count"] == 1

    # 6. wait (timeout path + immediate fact resolution path)
    res_wait_timeout = runner.invoke(
        decision_cmd,
        ["wait", "-q", "Wait for human", "-a", "@a501", "--timeout", "0.05", "--json"],
    )
    assert res_wait_timeout.exit_code == 0
    wait_dec_id = json.loads(res_wait_timeout.output)["decision"]["decision_id"]

    # Answer it via CLI
    res_ans = runner.invoke(decision_cmd, ["answer", wait_dec_id, "-r", "Confirmed", "--json"])
    assert res_ans.exit_code == 0
    assert json.loads(res_ans.output)["decision"]["status"] == "RESOLVED_HUMAN"

    # 7. approve-in & approve-out
    res_in = runner.invoke(decision_cmd, ["approve-in", "@a600", "--intent", "Run migration", "--json"])
    assert res_in.exit_code == 0
    assert json.loads(res_in.output)["decision"]["status"] == "RESOLVED_HUMAN"

    res_out = runner.invoke(decision_cmd, ["approve-out", "@a600", "--summary", "Migration complete", "--json"])
    assert res_out.exit_code == 0
    assert json.loads(res_out.output)["decision"]["status"] == "RESOLVED_HUMAN"

    # 8. tui & radar --no-serve
    res_tui = runner.invoke(decision_cmd, ["tui", "--seed-demo"])
    assert res_tui.exit_code == 0
    assert "HATH0R DECISION RADAR" in res_tui.output

    res_radar = runner.invoke(decision_cmd, ["radar", "--no-serve", "--json"])
    assert res_radar.exit_code == 0
    snap = json.loads(res_radar.output)
    assert len(snap["wedges"]) == 7


def test_cli_text_modes_and_edge_cases(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify text-mode outputs, error branches, and live probe paths for >90% coverage."""
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    # Text mode ask, dep, list --json
    assert runner.invoke(decision_cmd, ["ask", "-q", "Text mode question", "-a", "@t1"]).exit_code == 0
    assert runner.invoke(decision_cmd, ["dep", "--from", "node-1", "--to", "node-2"]).exit_code == 0
    assert runner.invoke(decision_cmd, ["dep", "--from", "node-2", "--to", "node-1"]).exit_code != 0
    assert runner.invoke(decision_cmd, ["dep", "--from", "node-2", "--to", "node-1", "--json"]).exit_code != 0
    assert runner.invoke(decision_cmd, ["list", "--json"]).exit_code == 0

    # Wait text mode (timeout + immediate fact resolve)
    assert runner.invoke(decision_cmd, ["wait", "-q", "Wait text", "--timeout", "0.02"]).exit_code == 0
    (tmp_path / "done.flag").write_text("ok", encoding="utf-8")
    assert (
        runner.invoke(
            decision_cmd,
            ["wait", "-q", "Wait file", "--fact", "file.exists:done.flag", "--timeout", "0.2"],
        ).exit_code
        == 0
    )

    # Answer & Reject text modes + not-found error branches
    req = runner.invoke(decision_cmd, ["ask", "-q", "To answer", "--json"])
    d1 = json.loads(req.output)["decision"]["decision_id"]
    assert runner.invoke(decision_cmd, ["snooze", d1, "--fact", "fact.custom:1"]).exit_code == 0
    assert runner.invoke(decision_cmd, ["answer", d1, "-r", "Done in text"]).exit_code == 0
    assert runner.invoke(decision_cmd, ["answer", "nonexistent-id"]).exit_code != 0
    assert runner.invoke(decision_cmd, ["answer", "nonexistent-id", "--json"]).exit_code != 0

    req2 = runner.invoke(decision_cmd, ["ask", "-q", "To reject", "--json"])
    d2 = json.loads(req2.output)["decision"]["decision_id"]
    assert runner.invoke(decision_cmd, ["reject", d2, "-r", "No longer needed"]).exit_code == 0
    assert runner.invoke(decision_cmd, ["reject", "nonexistent-id"]).exit_code != 0
    assert runner.invoke(decision_cmd, ["reject", "nonexistent-id", "--json"]).exit_code != 0
    assert runner.invoke(decision_cmd, ["snooze", "nonexistent-id", "--fact", "x:y"]).exit_code != 0
    assert runner.invoke(decision_cmd, ["snooze", "nonexistent-id", "--fact", "x:y", "--json"]).exit_code != 0

    # assert-fact, settle, approve-in, approve-out, tui --json, radar --no-serve in text mode
    assert runner.invoke(decision_cmd, ["assert-fact", "fact.custom:1"]).exit_code == 0
    assert runner.invoke(decision_cmd, ["settle"]).exit_code == 0
    assert runner.invoke(decision_cmd, ["settle", "--json"]).exit_code == 0
    assert runner.invoke(decision_cmd, ["approve-in", "@a700"]).exit_code == 0
    assert runner.invoke(decision_cmd, ["approve-out", "@a700"]).exit_code == 0
    assert runner.invoke(decision_cmd, ["tui", "--json"]).exit_code == 0
    assert runner.invoke(decision_cmd, ["radar", "--no-serve"]).exit_code == 0

    # Server GET /api/decisions and 404 endpoints
    server = HathorDecisionRadarServer(host="127.0.0.1", port=0, cwd=tmp_path)
    port = server.start(daemon=True)
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/decisions", timeout=3) as resp:
            assert resp.status == 200
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/unknown-route", timeout=3)
        assert exc_info.value.code == 404
    finally:
        server.stop()

