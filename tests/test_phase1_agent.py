"""Unit & Integration Tests for Phase 1 Features: KV Prewarmer, L2WS, HAHP Protocol, and Agent DAG."""

from __future__ import annotations

import json
from click.testing import CliRunner
from hath0r_cli.cli import main
from hath0r_cli.bots.kv_prewarmer import KVCachePrewarmer
from hath0r_cli.cccd.l2ws_predictor import L2WSPredictor
from hath0r_cli.bots.hahp_protocol import HAHPProtocolManager, HAHPEnvelope
from hath0r_cli.bots.agent_dag_runner import AgentDAGRunner
from hath0r_cli.cccd import CCCDCalibrationLoop


def test_kv_prewarmer_prefill():
    prewarmer = KVCachePrewarmer()
    res = prewarmer.prewarm_context("System prompt text", "user prompt text")
    assert res["status"] == "prewarmed"
    assert res["tokens_warmed"] > 0
    assert res["cache_hit_reduction_pct"] >= 40.0

    check = prewarmer.check_prefill_status("System prompt text", "user prompt text")
    assert check["cache_hit"] is True
    assert check["estimated_latency_saved_ms"] > 0


def test_kv_prewarmer_subagent_fanout():
    prewarmer = KVCachePrewarmer()
    fanout = prewarmer.execute_subagent_fanout_with_prewarm(
        shared_system_prompt="Shared System Context",
        subagent_prompts=["Prompt 1", "Prompt 2", "Prompt 3"],
    )
    assert fanout["status"] == "completed"
    assert fanout["subagent_count"] == 3
    assert fanout["latency_reduction_pct"] >= 40.0


def test_l2ws_predictor(tmp_path):
    storage_file = tmp_path / "l2ws.json"
    predictor = L2WSPredictor(storage_path=storage_file)

    pred1 = predictor.predict_warmstart("custom_signature")
    assert pred1["status"] == "fallback_default"

    predictor.save_warmstart("custom_signature", {"temperature": 0.15, "top_p": 0.92}, gradient_residual=0.01)

    pred2 = predictor.predict_warmstart("custom_signature")
    assert pred2["status"] == "hit"
    assert pred2["warmstart_parameters"]["temperature"] == 0.15
    assert pred2["convergence_time_reduction_pct"] >= 50.0


def test_hahp_protocol_manager():
    manager = HAHPProtocolManager()
    env = manager.create_envelope(
        sender_agent="test_sender",
        recipient_agent="test_recipient",
        scratchpad_delta="Working state scratchpad",
        state_variables={"foo": "bar"},
    )
    assert env.handoff_id.startswith("hahp-")
    assert env.sender_agent == "test_sender"

    serialized = manager.serialize(env)
    deserialized = manager.deserialize(serialized)
    assert deserialized.handoff_id == env.handoff_id
    assert deserialized.state_variables["foo"] == "bar"


def test_agent_dag_runner():
    runner = AgentDAGRunner()
    valid_spec = {
        "name": "test_dag",
        "nodes": [
            {"id": "node1", "agent_role": "role1", "depends_on": []},
            {"id": "node2", "agent_role": "role2", "depends_on": []},
            {"id": "barrier_node", "agent_role": "role3", "depends_on": ["node1", "node2"], "type": "barrier"},
        ]
    }
    is_valid, msg = runner.validate_dag(valid_spec)
    assert is_valid is True

    res = runner.execute_dag(valid_spec)
    assert res["status"] == "success"
    assert res["total_nodes"] == 3
    assert "barrier_node" in res["execution_order"]
    assert res["node_outputs"]["barrier_node"]["is_barrier"] is True


def test_agent_cli_commands():
    runner = CliRunner()

    res_prewarm = runner.invoke(main, ["--output", "json", "agent", "prewarm"])
    assert res_prewarm.exit_code == 0

    res_dag = runner.invoke(main, ["--output", "json", "agent", "dag", "--demo"])
    assert res_dag.exit_code == 0

    res_hahp = runner.invoke(main, ["--output", "json", "agent", "hahp"])
    assert res_hahp.exit_code == 0

    res_status = runner.invoke(main, ["--output", "json", "agent", "status"])
    assert res_status.exit_code == 0


def test_cccd_calibration_with_l2ws(tmp_path):
    loop = CCCDCalibrationLoop(state_file=tmp_path / "cccd_state.json")
    res = loop.run_calibration(iterations=1, signature_name="test_l2ws_sig")
    assert res["success"] is True
    assert "updated_parameters" in res
