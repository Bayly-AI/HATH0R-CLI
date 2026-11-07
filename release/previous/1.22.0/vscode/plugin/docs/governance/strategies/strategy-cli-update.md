# Strategy: CLI Update & Release Lifecycle

> Canonical Strategy for HATH0R-CLI updates, validation, knowledge synchronization, and promotion.

---

## 1. Executive Summary & Objective

The **CLI Update Strategy** establishes a deterministic, automated, and zero-defect pipeline for delivering changes to the `hath0r` CLI. Because `hath0r` is the single global operator interface and control plane across all projects in the Enterprise Agentic Platform, any change must strictly validate quality, synchronize documentation, ingest knowledge into Tri-Graph memory, verify release packaging, and automate PR promotion without human friction.

---

## 2. Core Pillars of the Update Lifecycle

1. **Preflight & Clean Tree:** Zero dirty state or uncommitted mutations prior to starting an update.
2. **Quality Gates & Tests:** Automated test suites must pass 100% with no regressions.
3. **SemVer Governance:** Every update must declare and enforce its semantic version impact (`major`, `minor`, `patch`).
4. **Documentation as Code:** `README.md`, `TECH_README.md`, and `CHANGELOG.md` must be synchronized before merging.
5. **Tri-Graph & Knowledge Share:** All updated documentation is ingested into local `MemoryGraph` and synced with canonical KB/MCP.
6. **Packaging Validation:** Python wheel and release artifacts are validated against metadata schemas.
7. **Automated PR & Promotion:** PR targeting `development` is automatically generated and verified.

---

## 3. Autonomous Execution: `update-cli-factory`

The declarative factory `cfg/factories/update-cli-factory.yaml` codifies this strategy into executable bot steps:

```text
PreflightBot ──► QualityGateBot ──► VersionBot ──► DocRefactorBot
      │                                                   │
      ▼                                                   ▼
TaskAnnouncerBot ◄── GitPRBot ◄── ReleaseBot ◄── KnowledgeSync / TriGraph
```
