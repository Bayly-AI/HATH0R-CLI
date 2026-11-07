# Local Memory Space Playbook
**Trigger**: A new agent session starts, or global rules need to be updated.
**Actions**:
1. Run `hath0r memory init` to bootstrap the memory space.
2. Agents run `hath0r memory read core` and `hath0r memory read architecture`.
3. To update rules, run `hath0r memory update <topic> <content>`.
