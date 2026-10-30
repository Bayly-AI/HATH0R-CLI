# Runbook: Agentic Security Incident & BITE Remediation (`CR-AGENTIC-SEC-001`)

## 1. BITE `DANGEROUS` Verdict Remediation
- **Symptom**: `hath0r skills audit` or `hath0r mcp audit` exits with code `1` and verdict `DANGEROUS`.
- **Root Cause**: Concealed capability (`STEGANOGRAPHIC_UNICODE`, `CONCEALED_PAYLOAD`, or `PROMPT_OVERRIDE`) or undeclared credential/network access.
- **Resolution**: Inspect `.hath0r/security/bite_manifest.json`, strip invisible Unicode variation selectors (`\uFE00-\uFE0F`), remove prompt override directives, or quarantine the skill/MCP server.

## 2. Telemetry Ledger Tamper Recovery
- **Symptom**: `hath0r finops tokens verify-ledger` reports `prev_hash_mismatch` or `record_hash_tampered`.
- **Resolution**: Inspect `tampered_records` line numbers in `.hath0r/finops/token_telemetry.jsonl` and restore from git or signed backup.
