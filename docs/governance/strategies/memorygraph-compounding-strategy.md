# MemoryGraph Compounding & Pre-Announcement Gate Strategy

> **Rule Binding**: `CR-MEMORY-COMPOUND-001` · `CR-AGENTGRAPH-001`  
> **Subsystem**: `hath0r_engine.memory` · `hath0r_cli.bots.memory_manager` · `hath0r_cli.bots.agentgraph_bot`

## 1. Strategic Objective

Autonomous agents lose institutional context across sessions when task learnings remain trapped in ephemeral chat transcripts or unindexed markdown notes. The **MemoryGraph Compounding Strategy** transforms every repository's `.hath0r/memory/graph.json` into a living, bitemporal semantic network where every completed task compounds institutional knowledge prior to completion announcement.

## 2. Architectural Pillars

1. **Universal Repository Memory Space (`.hath0r/memory/`)**:
   - Every repository in `/Users/raybayly/Development` maintains `.hath0r/memory/graph.json`, `.hath0r/memory/core_rules.md`, and `.hath0r/memory/architecture.md`.
   - Repository initialization (`hath0r init`), orientation (`hath0r orient`), cleanup (`hath0r repo clean`), and suite-wide audits (`hath0r memory ensure-all`) guarantee zero uninitialized repositories.

2. **Dual-Path Knowledge Compounding (Explicit + Automated)**:
   - **Explicit Agent Compounding**: Agents record high-signal architectural decisions (`decision`), episodic task outcomes (`episode`), facts (`fact`), concepts (`concept`), and rules (`rule`) via `hath0r memory compound`.
   - **Automated Lifecycle Compounding**: End-of-Task (`hath0r task finish`, `EndOfTaskBot`) and Clean-Repos (`CleanReposWorkflowBot`) automatically compound task/PR summaries and connect them to governing rules or resolved issues.

3. **Autonomous Reflection & Insight Consolidation (`ReflectionEngine`)**:
   - As episodic and decision nodes accumulate shared tags ($\ge 2$ nodes per tag cluster), `ReflectionEngine.consolidate_sleep_cycle()` synthesizes higher-order `insight` nodes linked via `DERIVES_FROM` edges.

4. **Zero-Lag AgentGraph Synchronization**:
   - Every memory mutation immediately synchronizes `.hath0r/agentgraph/snapshot.json` with normalized node and edge identifiers so `hath0r agentgraph query` retrieves compounded memory across the `memory` plane immediately.

5. **Hard Pre-Announcement Gate (`TaskAnnouncerBot`)**:
   - `TaskAnnouncerBot.announce_complete()` verifies via `MemoryManagerBot.verify_compounded()` that `.hath0r/memory/graph.json` exists and contains compounded task knowledge before emitting completion status.
