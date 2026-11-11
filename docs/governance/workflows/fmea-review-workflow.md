# Workflow: FMEA review (`cfg/factories/fmea-review-factory.yaml`)

> **Workflow ID**: `cfg/factories/fmea-review-factory.yaml` · **Owning Bots**: `fmea-bot`, `issue-manager-bot` · weekly

1. **`review` (`fmea-bot`, end-of-task)**: score, export to AgentGraph, file issues for H rows.
2. **`review` (`fmea-bot`, pr-lifecycle)**: the same for the PR lifecycle.
3. **`report` (`fmea-bot`)**: top rows across worksheets.
