# Issue Factory & Issue Manager Bot Specification

> Factory ID: **`issue-factory`**  
> Primary Bot: **`issue-manager-bot`**  
> Status: **Canonical Specification**  
> Updated: 2026-09-24

---

## 1. Overview & Purpose

The **Issue Factory** (`issue-factory`) coordinates organization-wide issue management, status validation, detailed description governance, and dependency-aware priority structuring across all repositories in the **Bayly-AI** organization.

It satisfies four mandatory operational requirements:
1. **Organization Scope by Default**: When listing issues, unless a specific repository is explicitly requested (`--repo <repo>`), all active repositories in the `@Bayly-AI` GitHub organization are automatically discovered and included.
2. **Issue Status and Health Validation**: Each issue's state is inspected to ensure it is valid, open/actionable, and properly formatted without missing metadata.
3. **Description Quality Gates**: Issues must feature detailed, actionable descriptions (minimum word counts, structured Markdown sections: `## Summary`, `## Acceptance Criteria`) on both creation and modification.
4. **Dependency-Aware Prioritization**: Issues are analyzed for cross-issue blockers, requirements, and dependencies (`depends on #X`, `blocks #Y`), categorizing issues into structured priority tiers:
   - **P1-Blocker/Core**: Issues that block other tickets or provide foundational APIs.
   - **P2-Foundation/Epic**: Architectural epics and control tower features.
   - **P3-Ready**: Independent issues ready for implementation without blockers.
   - **P4-Blocked-By-Dependencies**: Issues awaiting prerequisites to be completed first.

---

## 2. CLI Usage

### Listing Issues
```bash
# Scan across all 16 BaylyAI repositories with priority ordering:
hath0r issue list

# Target a specific repository:
hath0r issue list --repo Bayly-AI/1-Nation-ATC

# Output structured JSON:
hath0r --output json issue list
```

### Governed Issue Creation
```bash
hath0r issue create \
  --repo Bayly-AI/HATH0R-CLI \
  --title "feat(otel): add custom span processor" \
  --body "## Summary\nAdd custom span processor to enrich telemetry.\n\n## Acceptance Criteria\n- Implements processor interface\n- Unit tests pass"
```

### Factory Workflow Execution
```bash
# Execute the scan-and-prioritize declarative workflow:
hath0r factory run issue-factory --workflow scan-and-prioritize
```

---

## 3. Configuration & Declarative Manifest

Manifest location: `cfg/factories/issue-factory.yaml`
Schema validation: Validated against `contracts/hath0r-factory-manifest-v1.schema.json`.
