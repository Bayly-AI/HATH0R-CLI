# Procedure: Andon

> **Procedure ID**: `PR-ANDON-001` · **Owning Bot**: `andon-bot`

1. Mark factory steps whose failure must stop all work with `andon: stop`; use `andon: warn` to record without stopping.
2. Stops appear on the Decision Radar and in `hath0r andon status` (exit code 1 while stopped).
3. Acknowledge (`hath0r andon ack <id> --by <name>`) when someone owns the problem.
4. Fix the cause, then clear with a note (`hath0r andon clear <id> --note "<fix>"`). Clearing a stop without an ack is refused.
5. `hath0r andon verify` checks the ledger; a broken chain is itself a stop-worthy finding.
