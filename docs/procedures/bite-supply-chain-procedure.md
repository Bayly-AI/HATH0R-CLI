# Procedure: Agentic Supply-Chain Security & BITE Audit (`CR-AGENTIC-SEC-001`)

## 1. Entry Gate (`CR-CLI-ENTRY-001`)
Always invoke the operator CLI `hath0r` for supply-chain, telemetry, and knowledge curation audits:

1. **Audit Skills & Rules under BITE**:
   ```bash
   hath0r skills audit
   ```
2. **Audit MCP Server Definitions under BITE**:
   ```bash
   hath0r mcp audit
   ```
3. **Verify Hash-Chained Token Telemetry Ledger**:
   ```bash
   hath0r finops tokens verify-ledger
   ```
4. **Run KB Oversharing Red-Team Probes**:
   ```bash
   hath0r kb redteam --persona developer_agent
   ```
5. **Initialize & Validate Repository Threat Model**:
   ```bash
   hath0r threatmodel init
   hath0r threatmodel validate
   ```
6. **Classify Shadow-AI & Agent Commits**:
   ```bash
   hath0r observe shadow-ai --limit 10
   ```
