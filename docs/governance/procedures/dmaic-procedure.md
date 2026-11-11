# Procedure: DMAIC

> **Procedure ID**: `PR-DMAIC-001` · **Owning Bot**: `dmaic-project-bot`

1. **Define**: open an issue from the DMAIC template; `hath0r dmaic start <issue> --ctq <metric> --target <t> --problem "..."`.
2. **Measure**: taken at start from the SPC chart (and Cpk for `r_task`).
3. **Analyze**: `hath0r rca why <issue> ...`, then `hath0r dmaic analyze <issue>`.
4. **Improve**: land the change, then `hath0r dmaic improve <issue> --change "<PR>"`.
5. **Control**: `hath0r dmaic status <issue>` until 20 in-control points; `hath0r dmaic close <issue>`.
6. Each phase gate is a decision node in memory.
