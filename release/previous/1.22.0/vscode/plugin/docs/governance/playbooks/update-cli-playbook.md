# Update CLI Playbook
**Trigger**: A feature or bugfix modifying HATH0R-CLI is ready for completion.
**Actions**:
1. Developer runs `hath0r task start` for the CLI issue.
2. Code is committed to the feature branch.
3. Developer runs `hath0r execute update-cli-factory` (or equivalent hook) to trigger propagation.
4. The factory coordinates bots to publish and orient repos before triggering `end-of-task`.
