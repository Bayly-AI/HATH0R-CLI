# Workflow: Embedded ELT Ingestion and Projection Workflow

> Artifact: **Workflow** · Member of **Artifact Hexad** (`CR-CLI-FEATURE-STANDARD-001`)  
> Identity: `embedded-elt-workflow`  
> Suite: `HATH0R-CLI` Control Tower  
> Issue Reference: Bayly-AI/HATH0R-CLI#431  
> Date: 2026-10-11

## 1. Overview

The Embedded ELT Workflow orchestrates the continuous ingestion of documentation, MCP feeds, git history, and telemetry traces, followed by decoupled projection synchronization.

---

## 2. Declarative Definition

The pipeline is declared in [`cfg/workflows/embedded-elt-workflow.yaml`](file:///Users/raybayly/Development/OpenSource/HATH0R-CLI/cfg/workflows/embedded-elt-workflow.yaml):

```yaml
version: "1.0"
name: "embedded-elt-sync"
description: "Non-destructive raw ingestion and downstream index projection"
triggers:
  - on: "git.push"
  - on: "schedule.cron"
    cron: "0 */4 * * *"
steps:
  - id: "extract-docs"
    command: "hath0r elt extract --source docs/ --type docs"
  - id: "extract-git"
    command: "hath0r elt extract --source git --type git --commits 25"
  - id: "transform-projections"
    command: "hath0r elt transform --projection all"
  - id: "verify-status"
    command: "hath0r elt status"
```
