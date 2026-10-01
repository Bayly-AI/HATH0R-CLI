"""Unit tests for SchemaRepairEngine and AssertionGuardrail."""

import pytest
from click.testing import CliRunner

from hath0r_cli.cli import main as cli
from hath0r_cli.schema_repair import AssertionGuardrail, SchemaRepairEngine


def test_markdown_fence_cleaning():
    """Verify markdown code block stripping."""
    engine = SchemaRepairEngine()
    raw = "```json\n{\"key\": \"value\"}\n```"
    assert engine.clean_markdown_fences(raw) == '{"key": "value"}'


def test_trailing_comma_and_bracket_repair():
    """Verify trailing commas and unclosed brackets are repaired."""
    engine = SchemaRepairEngine()
    malformed = '{"success": true, "items": [1, 2, 3,],'
    repaired = engine.repair_json(malformed)
    assert repaired == {"success": True, "items": [1, 2, 3]}


def test_primitive_type_coercion():
    """Verify string boolean and integer coercion based on schema."""
    engine = SchemaRepairEngine()
    schema = {
        "type": "object",
        "properties": {
            "active": {"type": "boolean"},
            "count": {"type": "integer"},
            "ratio": {"type": "number"},
        },
    }

    raw = '{"active": "true", "count": "42", "ratio": "0.99"}'
    repaired = engine.repair_json(raw, schema=schema)
    assert repaired["active"] is True
    assert repaired["count"] == 42
    assert repaired["ratio"] == 0.99


def test_assertion_guardrail_validation():
    """Verify AssertionGuardrail checks custom invariants."""
    guard = AssertionGuardrail()
    data = {"status": "ok", "confidence": 0.92}

    ok, err = guard.validate_assertion(data, lambda d: d["confidence"] > 0.9, "Confidence too low")
    assert ok is True
    assert err is None

    failed, err_msg = guard.validate_assertion(data, lambda d: d["confidence"] > 0.95, "Confidence too low")
    assert failed is False
    assert err_msg == "Confidence too low"


def test_quality_repair_cli():
    """Verify hath0r quality repair CLI execution."""
    runner = CliRunner()
    raw_payload = '```json {"valid": "true", "count": "10",} ```'
    res = runner.invoke(cli, ["-o", "text", "quality", "repair", "-s", raw_payload])
    assert res.exit_code == 0
    assert "Payload Repaired Successfully" in res.output
