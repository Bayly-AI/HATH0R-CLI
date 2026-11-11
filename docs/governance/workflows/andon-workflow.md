# Workflow: Andon (`cfg/factories/andon-factory.yaml`)

> **Workflow ID**: `cfg/factories/andon-factory.yaml` · **Owning Bots**: `andon-bot`, `decision-radar-bot`

1. **`verify` (`andon-bot`)**: check the ledger hash chain.
2. **`check` (`andon-bot`)**: fail while any stop is active.

Every workflow run by `execute_workflow` also checks for an active stop before each step, and raises an event
when a step marked `andon: stop|warn` fails.
