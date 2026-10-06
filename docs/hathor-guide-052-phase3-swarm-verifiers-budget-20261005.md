# HATH0R-GUIDE-052: Phase 3 Autonomous Swarm, Verifiers & FinOps Budget Foundations

## Overview
This document serves as the canonical technical guide for **Phase 3: Autonomous Swarm, Verifiers & FinOps Budget Foundations** in `HATH0R-CLI` and the Ray Suite.

Phase 3 delivers four foundational autonomous governance and evaluation capabilities:
1. **FinOps Token Tree Budget Guard & Circuit Breaker** (`TokenTreeBudgetGuard` / `hath0r finops budget check`)
2. **Multi-Agent Consensus Engine & Evaluator Gate** (`MultiAgentConsensusEngine` / `hath0r evals consensus`)
3. **Antagonistic Review Bot & Tech Debt Enforcement** (`AntagonisticReviewBot` / `hath0r pr review --antagonistic`)
4. **Multi-Agent Red-Team / Blue-Team Verification Engine** (`MultiAgentRedTeamEngine` / `hath0r evals redteam`)

---

## Strategy & Architecture
- **Tree-Level Token Budget Circuit Breaker**: Enforces token and USD spending caps on nested subagent execution trees (`max_tokens_budget: 50,000`, `max_usd_budget: $0.25`), raising `TokenBudgetExceeded` exceptions to halt runaway subagent loops automatically.
- **GAIN Peer Consensus Gate**: Evaluates majority-vote agreement across peer subagents; automatically triggers human-in-the-loop fallback when agreement score falls below target threshold (`0.70`).
- **Antagonistic Adversarial Diff Review**: Scans git diffs for swallowed exceptions (`except Exception: pass`) and self-admitted tech debt (`TODO`s, `FIXME`s, stubs), auto-converting tech debt to GitHub issues under **Rule CR-CLI-TECH-DEBT-001**.
- **Red-Team / Blue-Team Survival Gate**: Adversarial Red-Team agent generates stress test suites in `tests/adversarial/`, requiring 100% attack vector survival prior to PR merge.

---

## Command Reference

### `hath0r finops budget check`
Inspects token and USD budget consumption for subagent execution trees.
```bash
hath0r finops budget check --tree-id default_tree
```

### `hath0r evals consensus`
Evaluates agreement and computes consensus scores across peer agent outputs.
```bash
hath0r evals consensus --threshold 0.70
```

### `hath0r pr review --antagonistic`
Executes adversarial code review and auto-creates tech debt issues.
```bash
hath0r pr review --antagonistic
```

### `hath0r evals redteam`
Spawns dual-agent Red-Team / Blue-Team verification loops.
```bash
hath0r evals redteam --component agent_subsystem
```

---

## Verification & Testing
Run unit and integration tests:
```bash
pytest tests/test_phase3_swarm_verifiers.py
```
