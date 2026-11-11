# Strategy: FMEA on the bot and workflow catalogue (WS4, #590)

> **Strategy ID**: `ST-FMEA-001` · **Owning Bot**: `fmea-bot`

Failure Mode and Effects Analysis ranks what can go wrong in a process before it does, so effort goes to the
riskiest failure modes first. Hath0r keeps one worksheet per factory workflow, seeded from the 14 failure modes
of the multi-agent failure taxonomy (MAST, Cemri et al. 2025) and mapped to that workflow's steps.

- Ratings are 1-10 for severity, occurrence and detection. Priority follows a documented reading of the
  AIAG-VDA (2019) action priority table (severity first); RPN is shown as well.
- Occurrence is measured where a row names a data signal (eval gate failures, a tier's pass rate, Andon events,
  the gauge's miss rate), and estimated otherwise.
- Every high-priority row has a GitHub issue. A fix is proven by re-rating and re-scoring the row.
- First studies: `end-of-task` and `pr-lifecycle` (#596, #597, #598).
