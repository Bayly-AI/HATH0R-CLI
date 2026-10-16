# MemoryGraph Compounding Playbook

> **Rule Binding**: `CR-MEMORY-COMPOUND-001`  
> **Target Audience**: Autonomous Agents, Subagents, and Operators

## 1. When to Use This Playbook

Execute this playbook on **every task** prior to announcing completion, during `clean-repos` (Step 6 & Step 13), and whenever onboarding or auditing repositories across `/Users/raybayly/Development`.

## 2. Node Type Selection Guide

| Node Type | When to Use | Default Importance | Example ID Prefix |
|-----------|-------------|--------------------|-------------------|
| `episode` | Completed feature, bugfix, or clean-repo task outcome | `0.75` | `episode:` |
| `decision` | Architectural Decision Record (ADR) or design tradeoff | `0.90` | `decision:` |
| `fact` | Verified system invariant, endpoint, or configuration truth | `0.80` | `fact:` |
| `insight` | Synthesized pattern across $\ge 2$ episodes/decisions | `0.85` | `insight:` |
| `concept` | Core domain or substrate abstraction | `0.90` | `concept:` |
| `rule` | Governance policy or operational constraint | `1.00` | `rule:` |

## 3. Relational Edge Selection Guide

- `ENFORCES`: A `rule` node enforces a `concept` or `decision`.
- `DERIVES_FROM`: An `episode` or `insight` derives from an existing `concept`, `decision`, or `episode`.
- `RESOLVES`: An `episode` or `decision` resolves an issue or defect node.
- `SUPERSEDES`: A newer `decision` or `fact` bitemporally supersedes an older node.
- `RELATES_TO`: General semantic association between nodes.

## 4. Playbook Execution Recipes

### Recipe A: Compounding Task Knowledge at Task Completion
```bash
hath0r memory compound \
  --id "episode:issue-287-memorygraph-compounding" \
  --type episode \
  --label "Enforced CR-MEMORY-COMPOUND-001 and Suite-Wide MemoryGraph" \
  --content "Provisioned .hath0r/memory/graph.json across all repos and wired pre-announcement memory compounding gates into TaskAnnouncerBot, EndOfTaskBot, and CleanReposWorkflowBot." \
  --importance 0.85 \
  --tags "memorygraph,governance,cr-memory-compound-001" \
  --relates-to "concept:tri-graph" \
  --relation DERIVES_FROM
```

### Recipe B: Provisioning `.hath0r/memory` Across All Repositories
```bash
hath0r memory ensure-all --root /Users/raybayly/Development
```

### Recipe C: Running Sleep-Cycle Reflection Consolidation
```bash
hath0r memory reflect
```
