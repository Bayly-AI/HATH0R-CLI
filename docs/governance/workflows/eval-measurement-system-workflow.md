# Workflow: Eval measurement system analysis (`cfg/factories/msa-study-factory.yaml`)

> **Workflow ID**: `cfg/factories/msa-study-factory.yaml` · **Owning Bots**: `measurement-system-bot`, `task-evaluator-bot`

1. **`run-study` (`measurement-system-bot`)**: replay the panel, compute Gage R&R and attribute agreement, save the study. Abort on failure.
2. **`report` (`measurement-system-bot`)**: report the latest study and whether the current judge fingerprint is qualified.
