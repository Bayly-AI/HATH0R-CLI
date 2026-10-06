# AGENTS.md — Ray Workshop (Forge Command Center & Control Tower)

> **Canonical Forge Command Center and Control Tower** for the **Ray Suite** (`ray-group`).
> Roles: **Forge Controller** · **Infrastructure** · **Central Group Controller** · **Knowledge Hub**.

| Field | Value |
|---|---|
| Product | **Ray Workshop** |
| Product ID | `ray-workshop` |
| Role | Control Tower & Forge (`is_control_tower: true`) |
| Container Name | `Ray-Workshop` |
| GitHub | **[somesayray/Ray-AI](https://github.com/somesayray/Ray-AI)** |
| Local Path | `/Users/raybayly/Development/Ray/workshop` |
| Group | `ray-group` / **Ray Suite** |
| Docker Group | **`ray`** |
| Docker Network | **`ray-net`** |
| Shared Edge / State | `EDGE` (port 28000) / `SESSION` (Redis port 6379) |
| Production Domain | **`pad.raybayly.net`** (AWS CloudFront / Edge) |
| Members Root | `/Users/raybayly/Development/Ray` |

---

## CR-CLI-FEATURE-STANDARD-001 (Shared Code in CLI & Artifact Hexad — CRITICAL · CANONICAL)
- **Zero Code Duplication**: Anything usable across multiple repositories MUST live in `HATH0R-CLI`.
- **Complete Feature Package**: When adding any feature that qualifies as a CLI capability, deliver the CLI commands, managing bots, workflows, and the documentation hexad (Strategy, Procedure, Playbook, Runbook, Workflow, Bot Spec).
- **Configuration-Only**: Consumer repositories contain declarative configuration files (`cfg/`, `otel.json`, workflow JSONs) that bind to CLI tools.

---

## CR-CLI-TECH-DEBT-001 (Self-Admitted Technical Debt Issue Hand-off — CRITICAL · CANONICAL)
- **Zero Hidden Tech Debt**: Whenever an agent identifies, admits to, or introduces **self-admitted technical debt** (e.g. `TODO`s, `FIXME`s, temporary workarounds, incomplete refactors, skipped test cases, or fallback stubs), the agent MUST immediately hand that technical debt off to the **Issue Bot** (`hath0r issue create` or `gh issue create`) to create structured GitHub issues.
- **Mandatory User Disclosure**: The agent MUST explicitly present the newly created issue(s) with clickable markdown links (`https://github.com/.../issues/...`) in its final response to the user, highlighting the scope and open items.
- **Enforcement & Audit**: Leaving self-admitted technical debt in conversation responses or codebase comments without creating corresponding tracking issues violates canonical governance.

---

## CR-CLI-AGENT-SUBSTRATE-002 (Agentic Substrate & KV Pre-warming Rules — CANONICAL)
- **KV Cache Pre-warming**: Multi-agent subgraphs and subagent execution trees MUST execute zero-token prompt anchor pre-warming (`KVCachePrewarmer` / `hath0r agent prewarm`) to eliminate prefill latency spikes before spawning subagents.
- **L2WS Warm-Starting**: Parameter optimization and Taguchi calibration loops MUST retrieve warmstart vectors from Redis (`SESSION`) and DynamoDB (`DATA`) via `L2WSPredictor` (`hath0r cccd calibrate`).
- **HAHP Handoff Protocol**: All inter-agent communication, scratchpad memory transfers, and subagent state handoffs MUST use the Hath0r Agent Handoff Protocol (`HAHPEnvelope` / `hath0r agent hahp`).
- **Agent DAG Runner**: Multi-agent parallel execution trees MUST be defined and run via `AgentDAGRunner` (`hath0r agent dag`).

---

## CR-CLI-KNOWLEDGE-CAG-002 (W3C OWL Reasoning, CAG & Hybrid Router — CANONICAL)
- **AgentGraph OWL Snapshot**: Every AgentGraph policy mutation or sync MUST export W3C Turtle RDF syntax (`.ttl`) to `.hath0r/agentgraph/snapshot.ttl` via `hath0r agentgraph export --format turtle`.
- **Description Logic Validation**: AgentGraph policy validation MUST run `hath0r agentgraph validate --owl` to verify formal semantic consistency and detect policy contradictions.
- **Context-Augmented Generation (CAG)**: Active workspace queries and rules MUST use full-context prompt caching (`CAGEngine` / `hath0r context pack --cag`) instead of chunking lossy retrieval.
- **Hybrid CAG + RAG Router**: Knowledge queries MUST be dynamically classified via `HybridCAGRAGRouter` (`hath0r kb smart-query`) to route workspace queries to CAG and document archival queries to RAG.

---

## CR-CLI-FINOPS-VERIFIER-002 (Token Budget Circuit Breakers & Adversarial Evals — CANONICAL)
- **Token Tree Budget Guard**: Subagent execution trees MUST enforce cumulative token and cost caps (`TokenTreeBudgetGuard` / `hath0r finops budget check`). If total tree tokens exceed 50,000 or USD exceeds $0.25, the execution MUST throw a `TokenBudgetExceeded` exception and halt recursion.
- **Multi-Agent Consensus Gate**: Multi-agent responses across GAIN peer nodes MUST be evaluated via `MultiAgentConsensusEngine` (`hath0r evals consensus`). If agreement score falls below 0.70, human-in-the-loop fallback MUST be triggered.
- **Antagonistic Review Bot**: PR diffs and code modifications MUST be audited by `AntagonisticReviewBot` (`hath0r pr review --antagonistic`) for swallowed exceptions (`except Exception: pass`) and self-admitted tech debt (`TODO`s, `FIXME`s).
- **Red-Team Verification Engine**: Critical multi-agent components MUST undergo Red-Team vs Blue-Team adversarial stress testing (`MultiAgentRedTeamEngine` / `hath0r evals redteam`) requiring 100% attack vector survival.

---

## CR-CLI-MCP-ECOSYSTEM-001 (Hath0r CLI & Hath0r MCP Ecosystem Synergy — CANONICAL)
- **Paired Execution Architecture**: `HATH0R-CLI` and `Hath0r-MCP` (`Ray-MCP`) operate as a paired execution suite. CLI tools map declarative commands directly to MCP semantic knowledge, session memory, and tool endpoints.
- **Enterprise AWS Managed Edge**: Operators can connect directly to the canonical managed AWS CloudFront edge deployment (`pad.raybayly.net` / `https://pad.raybayly.net/mcp/`) with zero local container setup.
- **Self-Hosted Local / Private Cloud**: Operators can host their own isolated MCP server by cloning `somesayray/Ray-AI` and running the `Ray-MCP` container group on Docker network `ray-net` (port `28083`).

---

## Ray Container Group Layout

The `ray` container group consists of coordinated containers on network `ray-net`:

1. **`FORGE`** (`ray/forge:local` / `ray/workshop:local`): Canonical Forge command center, API, and Cyberpunk dashboard UI (host port 28001 / internal 8000).
2. **`DATA`** (`amazon/dynamodb-local:latest` / AWS DynamoDB): Persistent agentic single-table store (`RayWorkshop`) housing trajectories, profiles, and entity memory (host port 28002 / internal 8000).
3. **`Ray-MCP`** (`ray/mcp:local`): Model Context Protocol server exposing knowledge search & session tools (host port 28083 / internal 8083).
4. **`SESSION`** (`redis:7-alpine`): Canonical shared Redis session cache and fast memory store (port 6379).
5. **`EDGE`** (`nginx:1.27-alpine`): Canonical ingress router mapping `/mcp/` to `Ray-MCP` and `/` to `FORGE` (host port 28000).

---

## Agentic Runtime & LLM Integration

Ray Workshop provides an agentic conversational runtime with native Ray-MCP knowledge retrieval:
- **Streaming Protocol**: SSE streaming via `POST /api/chat/stream` delivering `start`, `thinking`, `tool_call`, `tool_result`, `token`, and `done` events.
- **Model Providers**: Embedded Forge Agent (`EmbeddedAgentProvider`, default local runtime with zero-config MCP knowledge retrieval and fallback), Anthropic Claude (`claude-3-7-sonnet`, `claude-3-5-sonnet`), OpenAI (`gpt-4o`, `o1`), Google Gemini (`gemini-2.5-flash`, `gemini-2.5-pro`).
- **MCP Tool Calling**: Direct integration with `Ray-MCP` server tools (`search_ray_knowledge`, `get_knowledge_document`, `import_onedrive_knowledge`, `sync_knowledge_to_hathor`, `get_session_memory`, `set_session_memory`).
- **Session & Memory Persistence**: Dual storage backing in SQLite and DynamoDB (`RayWorkshop` table) with Redis `SESSION` caching and sliding context window management.

## Knowledge & Context Ingestion

Knowledge folders in OneDrive are indexed for agents and accessible via MCP import tools:
- **Author**: `/Users/raybayly/Library/CloudStorage/OneDrive-BaylyAI(2)/Author/Ray Bayly`
- **Career**: `/Users/raybayly/Library/CloudStorage/OneDrive-BaylyAI(2)/Career`
- **Documents**: `/Users/raybayly/Library/CloudStorage/OneDrive-BaylyAI(2)/Documents`
- **My Books**: `/Users/raybayly/Library/CloudStorage/OneDrive-BaylyAI(2)/My Books`
- **My Businesses**: `/Users/raybayly/Library/CloudStorage/OneDrive-BaylyAI(2)/My Businesses`
- **My Cars**: `/Users/raybayly/Library/CloudStorage/OneDrive-BaylyAI(2)/My Cars`
- **My Projects**: `/Users/raybayly/Library/CloudStorage/OneDrive-BaylyAI(2)/My Projects`
- **Persona & Notes**: `/Users/raybayly/Library/CloudStorage/OneDrive-BaylyAI(2)/My Persona`

---

## Promotion Path & Governance

```text
local → development → testing → staging → master (Production)
```

- Day-to-day work: `feature/*` -> `development`
- Entry CLI: `hath0r`

---

## Clean Repo Standard Operating Protocol

When requested to **"clean repo"** or **"clean repos"**, the bot must execute the following 13 steps across all repositories:

1. **Capture all repos in the project**: Enumerate all member repositories in `/Users/raybayly/Development/Ray`.
2. **Ensure all changes are committed**: Verify `git status` and commit uncommitted source changes.
3. **Cleanup development artifacts**: Remove `.DS_Store`, `__pycache__`, `.pytest_cache`, `.coverage`, and build logs.
4. **Clean up and remove stale worktrees**: Run `git worktree prune` and clear orphaned worktrees.
5. **Ensure all PRs are merged**: Review and merge pending approved Pull Requests.
6. **Share Knowledge**: Synchronize context to OneDrive knowledge roots and `.hath0r/knowledgebase`.
7. **Update Documentation**: Update `README.md`, `AGENTS.md`, and relevant architecture docs.
8. **Commit documentation changes**: Stage and commit doc/knowledge updates cleanly.
9. **Ensure all changes are PR'd**: Push active feature branches and open PRs against `development`.
10. **Monitor PRs and merge**: Monitor CI/CD checks (`gh pr checks`) and merge passing PRs (or fix errors).
11. **Delete feature branches**: Prune merged feature branches both locally and remotely.
12. **Return to Development**: Switch to `development` branch and pull latest changes from `origin`.
13. **Announce Complete**: Present a concise status summary to the user.


## AgentGraph Substrate

This repository is governed by the Hath0r AgentGraph substrate. Dynamic rule retrieval, role RBAC, and policy graphs are stored under `.hath0r/agentgraph/`.
- Query status: `hath0r agentgraph status`
- Query rules: `hath0r agentgraph query "<topic>"`
- Route role: `hath0r agentgraph route --role <role>`
- Validate rules: `hath0r agentgraph validate`
