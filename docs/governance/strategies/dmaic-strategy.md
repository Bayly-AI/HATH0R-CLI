# Strategy: DMAIC improvement projects (WS7, #592)

> **Strategy ID**: `ST-DMAIC-001` · **Owning Bot**: `dmaic-project-bot`

A quality fix without a baseline and a control check cannot show it worked or that it lasted. Each fix that
matters runs as a Define-Measure-Analyze-Improve-Control project tied to one GitHub issue
(`.github/ISSUE_TEMPLATE/dmaic-improvement.yml`) and one CTQ metric from `hath0r spc`. A project closes only
when the CTQ chart shows 20 or more in-control points after the change. First project: #599 (Tier 4 discrimination).
