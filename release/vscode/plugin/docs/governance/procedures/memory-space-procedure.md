# Local Memory Space Procedure
1. The developer configures the app to invoke `hath0r memory read` when an agent session begins.
2. The agent reads the output to gather context.
3. If rules change, the `memory-management-factory` updates the memory space using the `MemoryManagerBot`.
