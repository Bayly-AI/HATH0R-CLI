"""Unit tests for TemporalLogicPlannerBot (TLP Temporal Logic Planning & Automata)."""

from __future__ import annotations

import pytest

from hath0r_cli.bots.temporal_logic_planner_bot import (
    TemporalLogicPlannerBot,
)


@pytest.fixture
def tlp_verifier() -> TemporalLogicPlannerBot:
    return TemporalLogicPlannerBot()


def test_cr_bai_001_valid_promotion(tlp_verifier: TemporalLogicPlannerBot) -> None:
    trace = ["local", "development", "testing", "staging", "master"]
    report = tlp_verifier.verify_trace(trace=trace, policy_name="cr-bai-001")
    assert report["valid"] is True
    res = report["results"]["cr-bai-001"]
    assert res["valid"] is True
    assert res["states_visited"][-1] == "S_PROD"


def test_cr_bai_001_invalid_skip_promotion(tlp_verifier: TemporalLogicPlannerBot) -> None:
    # Skipping testing directly into staging
    trace = ["local", "development", "staging", "master"]
    report = tlp_verifier.verify_trace(trace=trace, policy_name="cr-bai-001")
    assert report["valid"] is False
    res = report["results"]["cr-bai-001"]
    assert res["valid"] is False
    assert "S_TRAP" in res["states_visited"]
    assert "rejecting trap state" in res["rejection_reason"]


def test_cr_hathor_init_001_valid_order(tlp_verifier: TemporalLogicPlannerBot) -> None:
    # check_playbook then check_runbook then scaffold
    trace1 = ["check_playbook", "check_runbook", "scaffold_layout"]
    report1 = tlp_verifier.verify_trace(trace=trace1, policy_name="cr-hathor-init-001")
    assert report1["valid"] is True

    # Reversed order: check_runbook then check_playbook then scaffold
    trace2 = ["check_runbook", "check_playbook", "scaffold_layout"]
    report2 = tlp_verifier.verify_trace(trace=trace2, policy_name="cr-hathor-init-001")
    assert report2["valid"] is True


def test_cr_hathor_init_001_premature_scaffolding(tlp_verifier: TemporalLogicPlannerBot) -> None:
    trace = ["scaffold_layout"]
    report = tlp_verifier.verify_trace(trace=trace, policy_name="cr-hathor-init-001")
    assert report["valid"] is False
    res = report["results"]["cr-hathor-init-001"]
    assert res["valid"] is False
    assert "S_TRAP" in res["states_visited"]


def test_cr_cicccd_001_calibration(tlp_verifier: TemporalLogicPlannerBot) -> None:
    # Valid: calibrate then deploy
    trace_valid = ["calibrate", "deploy"]
    report_v = tlp_verifier.verify_trace(trace=trace_valid, policy_name="cr-cicccd-001")
    assert report_v["valid"] is True

    # Invalid: deploy without calibrate
    trace_invalid = ["deploy"]
    report_inv = tlp_verifier.verify_trace(trace=trace_invalid, policy_name="cr-cicccd-001")
    assert report_inv["valid"] is False
