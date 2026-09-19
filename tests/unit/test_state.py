"""State aggregation and exit-class conventions."""

from __future__ import annotations

from hath0r_cli.doctor import DoctorCheck, DoctorResult


def test_doctor_overall_ok() -> None:
    result = DoctorResult(
        group_id="g",
        control_tower_product_id="hath0r-cli",
        control_tower_configured=True,
        checks=[DoctorCheck("a", "A", "ok", "fine")],
    )
    assert result.overall_state == "ok"
    assert result.failed_count == 0


def test_doctor_overall_degraded() -> None:
    result = DoctorResult(
        group_id="g",
        control_tower_product_id="hath0r-cli",
        control_tower_configured=True,
        checks=[
            DoctorCheck("a", "A", "ok", "fine"),
            DoctorCheck("b", "B", "unavailable", "missing"),
        ],
    )
    assert result.overall_state == "degraded"
    assert result.ok_count == 1
    assert result.failed_count == 1
    data = result.to_data()
    assert data["counts"]["ok"] + data["counts"]["failed"] == len(data["checks"])
