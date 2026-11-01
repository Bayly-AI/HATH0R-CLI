# Update CLI Runbook
**Execution**:
When executing an update to the CLI:
1. Verify `cfg/factories/update-cli-factory.yaml` is active.
2. Ensure the `orient-bot` has cross-repo permissions.
3. Validate tests pass locally (`make test`).
4. Execute factory to propagate and merge.
