# CICCCD Checklist

> Product: **HATH0R Control Tower** · Subsystem: **Governance & Calibration Engine**  
> Status: **Active Checklist** · Updated: 2026-10-04

---

## Pre-Merge & Pre-PR Gate Checklist

- [ ] `hath0r cicccd validate` returns `Overall Status: VALID`.
- [ ] Schema contracts verified (`hath0r contracts validate`).
- [ ] AgentGraph policy valid (`hath0r agentgraph validate`).
- [ ] Calibration freshness age is $\le 24.0\text{ hours}$.
- [ ] DSPy compiled signatures updated in `.hath0r/cccd/compiled_prompts/`.
- [ ] Artifact Hexad documentation verified (Strategy, Procedure, Playbook, Runbook, Checklist, Bot Spec).
- [ ] Pytest test suite passing (`pytest tests/unit/test_cicccd.py`).
