# Hyper Context Runbook

**Reference:** [Hyper Context Strategy](../strategies/hyper-context-strategy.md)

## Execution via CLI
To spread context to a feature folder (e.g., `src/hath0r_cli/bots`):

1. **Run the Spread Command:**
   ```bash
   hath0r context spread --target src/hath0r_cli/bots --feature-name "Bots Subsystem"
   ```
2. **Update Root Index:**
   Manually edit the root `AGENTS.md` (or let the bot append to it) to ensure there is a clear breadcrumb trail:
   `-> For Bots Subsystem rules, see src/hath0r_cli/bots/AGENTS.md`
3. **Commit:** Ensure these context files are version-controlled and subject to the standard PR review process.
