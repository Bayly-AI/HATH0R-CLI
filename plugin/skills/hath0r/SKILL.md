---
name: hath0r
description: Control tower, governance, AgentGraph + CLAUDE.md sync, BITE supply-chain security, PBAC/RBAC red-teaming, SFT/LoRA/PEFT continuous training, Taguchi optimization, FinOps hash-chained token ledger, and pixel-native vision tools via HATH0R CLI.
---

# HATH0R Operator Skill (`v1.15.0`)

Use this skill when interacting with the Hath0r agentic framework, enforcing multi-repository governance (`CR-CLI-ENTRY-001`, `CR-CLAUDE-SYNC-001`, `CR-AGENTIC-SEC-001`), running clean-repo or git promotion workflows, or executing SFT/LoRA/PEFT training and 4-tier evaluations.

## Canonical Workflows

### 1. Suite Diagnostics, Orientation & Clean Repos
```bash
hath0r doctor
hath0r orient
hath0r clean-repos --all
```

### 2. AgentGraph, `CLAUDE.md` Sync & MemoryGraph Compounding (`CR-CLAUDE-SYNC-001` · `CR-MEMORY-COMPOUND-001`)
```bash
hath0r agentgraph sync
hath0r agentgraph validate --owl
hath0r memory session start --task "<task-id>"
hath0r memory session write --summary "<summary>"
hath0r memory compound --type episode --title "<title>" --content "<summary>"
hath0r memory hash --sync
hath0r memory verify
```

### 3. Agentic Security, Supply-Chain & Threat Model Gates (`CR-AGENTIC-SEC-001`)
```bash
hath0r skills audit
hath0r mcp audit --pin
hath0r threatmodel validate
hath0r kb redteam
hath0r security openant
hath0r observe shadow-ai
```

### 4. FinOps Hash-Chained Token Ledger & Tokenizer Tax Audit
```bash
hath0r finops tokens verify-ledger
hath0r finops budget check
hath0r finops tokenizer-tax "Sample prompt or file path"
```

### 5. Continuous Calibration & SFT/LoRA/PEFT Training (`CR-CICCCDCT-001`)
```bash
hath0r cccd calibrate
hath0r cccd train --base-model hath0r-base-7b --lora-r 16 --lora-alpha 32
```

### 6. Git Branch, PR, Release & Environment Promotion (`CR-BRANCH-GOV-001` · `CR-SEMVER-BUMP-001`)
```bash
hath0r branch start feature <issue> <slug>
hath0r release validate
hath0r pr create --semver patch
hath0r pr review --antagonistic
hath0r pr merge <pr-number>
hath0r promote release <x.y.z>
hath0r promote to testing --gate
```

### 7. 4-Tier Hybrid Evaluation & SonarCloud Pre-Announcement Gate (`CR-TASK-EVAL-001` · `CR-SONAR-PREANNOUNCE-001`)
```bash
hath0r evals run
hath0r evals verify
hath0r quality sonar
```

### 8. Taguchi Optimization & Pixel-Native Vision
```bash
hath0r optimize taguchi --array L9 -f temperature -f top_p --snr 120,115,118
hath0r vision parse-doc invoice.png --pixel-native
hath0r vision ground screenshot.png --target "Submit Form" --playwright
```
