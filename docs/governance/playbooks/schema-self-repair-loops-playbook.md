# Playbook: Programmatic Assertion & Schema Self-Repair Operations

> Operational Playbook for Automated Payload Repair and Validation Loops  
> Product: `HATH0R-CLI` · Group: `hath0r-opensource` · Issue: #227

---

## 📋 Overview

This playbook describes how to use `SchemaRepairEngine` and `AssertionGuardrail` to sanitize, repair, and validate structured payloads and CLI contracts.

---

## 🛠️ CLI Operations

### 1. Test & Repair Corrupt or Malformed JSON
To repair a malformed JSON file with trailing commas or markdown fences:

```bash
hath0r quality repair --input-file malformed_payload.json --schema contracts/hath0r-vision-response-v1.schema.json
```

### 2. Validate with Programmatic Assertions
```bash
hath0r quality repair --raw-string '```json {"success": "true", "confidence": "0.95",} ```'
```

---

## 💻 Programmatic Integration

```python
from hath0r_cli.schema_repair import SchemaRepairEngine

engine = SchemaRepairEngine()
repaired_dict = engine.repair_json('```json {"active": "true", "count": "42",} ```')
# Returns: {"active": True, "count": 42}
```
