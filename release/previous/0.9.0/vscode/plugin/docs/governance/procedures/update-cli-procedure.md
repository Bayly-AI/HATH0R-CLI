# Update CLI Procedure
1. Make changes to the CLI source code and test locally.
2. Trigger the `update-cli-factory`.
3. The factory validates tests, updates docs, and publishes the CLI.
4. The Orient Bot synchronizes dependent repos.
5. Control is handed back to the agent for final check, then End-of-Task PR lifecycle completes it.
