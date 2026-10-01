"""Programmatic Assertion & Schema Self-Repair Engine for Hath0r CLI."""

from __future__ import annotations

import json
import re
from typing import Any, Callable, Dict, List, Optional, Tuple, Union


class SchemaRepairEngine:
    """Pre-execution sanitizer and deterministic schema self-repair engine."""

    def __init__(self, auto_coerce: bool = True) -> None:
        self.auto_coerce = auto_coerce

    def clean_markdown_fences(self, text: str) -> str:
        """Strip markdown code block fences and surrounding prose."""
        cleaned = text.strip()
        # Strip ```json ... ``` or ``` ... ```
        fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, re.IGNORECASE)
        if fence_match:
            return fence_match.group(1).strip()
        return cleaned

    def fix_json_syntax(self, text: str) -> str:
        """Fix common LLM JSON syntax corruptions like trailing commas."""
        cleaned = self.clean_markdown_fences(text).strip()

        # 1. Remove trailing commas at end of text
        cleaned = re.sub(r",\s*$", "", cleaned)

        # 2. Repeatedly remove trailing commas before closing braces/brackets
        while True:
            new_cleaned = re.sub(r",\s*([\]}])", r"\1", cleaned)
            if new_cleaned == cleaned:
                break
            cleaned = new_cleaned

        # 3. Fix single quotes to double quotes around keys and strings
        cleaned = re.sub(r"([{,]\s*)'([^']+)'\s*:", r'\1"\2":', cleaned)

        # 4. Handle Python True/False/None
        cleaned = re.sub(r"\bTrue\b", "true", cleaned)
        cleaned = re.sub(r"\bFalse\b", "false", cleaned)
        cleaned = re.sub(r"\bNone\b", "null", cleaned)

        # 5. Check for truncated trailing closing brackets
        open_braces = cleaned.count("{") - cleaned.count("}")
        open_brackets = cleaned.count("[") - cleaned.count("]")
        if open_braces > 0:
            cleaned += "}" * open_braces
        if open_brackets > 0:
            cleaned += "]" * open_brackets

        # 6. Final pass for trailing commas before newly added closing braces
        while True:
            new_cleaned = re.sub(r",\s*([\]}])", r"\1", cleaned)
            if new_cleaned == cleaned:
                break
            cleaned = new_cleaned

        return cleaned

    def coerce_primitive(self, val: Any, expected_type: Optional[str] = None) -> Any:
        """Coerce strings to boolean, integer, or float when unambiguous."""
        if not isinstance(val, str):
            return val

        stripped = val.strip().lower()
        if expected_type == "boolean" or stripped in ("true", "false"):
            if stripped == "true":
                return True
            if stripped == "false":
                return False

        if expected_type == "integer" or re.fullmatch(r"[-+]?\d+", stripped):
            try:
                return int(stripped)
            except ValueError:
                pass

        if expected_type == "number" or re.fullmatch(r"[-+]?\d*\.\d+", stripped):
            try:
                return float(stripped)
            except ValueError:
                pass

        return val

    def coerce_payload(self, data: Any, schema: Optional[Dict[str, Any]] = None) -> Any:
        """Recursively apply type coercion and enum normalization based on schema."""
        if isinstance(data, dict):
            props = (schema or {}).get("properties", {})
            coerced_dict = {}
            for k, v in data.items():
                expected_prop = props.get(k, {}) if isinstance(props, dict) else {}
                expected_type = expected_prop.get("type")
                coerced_val = self.coerce_payload(v, expected_prop)
                coerced_dict[k] = self.coerce_primitive(coerced_val, expected_type)
            return coerced_dict
        elif isinstance(data, list):
            items_schema = (schema or {}).get("items", {}) if isinstance(schema, dict) else {}
            return [self.coerce_payload(item, items_schema) for item in data]
        else:
            return self.coerce_primitive(data, (schema or {}).get("type"))

    def repair_json(
        self,
        raw_text: str,
        schema: Optional[Dict[str, Any]] = None,
    ) -> Union[Dict[str, Any], List[Any]]:
        """Complete deterministic JSON repair pipeline."""
        sanitized = self.fix_json_syntax(raw_text)
        try:
            parsed = json.loads(sanitized)
        except json.JSONDecodeError:
            # Second pass: aggressively extract first valid JSON substring
            match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", sanitized)
            if match:
                parsed = json.loads(match.group(1))
            else:
                raise ValueError(f"Could not repair malformed JSON payload: {raw_text[:100]}...")

        if self.auto_coerce:
            parsed = self.coerce_payload(parsed, schema)

        return parsed


class AssertionGuardrail:
    """Evaluates programmatic assertions and contract invariants on agent payloads."""

    def __init__(self, repair_engine: Optional[SchemaRepairEngine] = None) -> None:
        self.repair_engine = repair_engine or SchemaRepairEngine()

    def validate_assertion(
        self,
        data: Any,
        assertion_fn: Callable[[Any], bool],
        error_message: str,
    ) -> Tuple[bool, Optional[str]]:
        """Evaluate custom assertion function against payload."""
        try:
            passed = bool(assertion_fn(data))
            if passed:
                return True, None
            return False, error_message
        except Exception as exc:
            return False, f"{error_message} (Raised: {exc})"

    def validate_schema_required(
        self,
        data: Dict[str, Any],
        schema: Dict[str, Any],
    ) -> Tuple[bool, List[str]]:
        """Check required fields and report missing keys."""
        missing: List[str] = []
        required = schema.get("required", [])
        if isinstance(required, list):
            for req in required:
                if req not in data:
                    missing.append(req)
        return len(missing) == 0, missing
