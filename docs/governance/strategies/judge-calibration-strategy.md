# Strategy: Judge calibration per complexity level (#610)

A Six Sigma reviewer pointed out that Gage R&R assumes a gauge behaves the same across the range it
measures, and that LLM judges often do not: in one calibration of 15 judges, 14 failed fit checks at one
or more complexity levels. Hath0r answers this in two studies.

* **Study A** (`hath0r evals msa run`, `measurement-system-bot`): the deterministic 4-tier eval gauge is
  run over a panel stratified by complexity level L1 to L5 (`cfg/evals/complexity-levels.yaml`), with
  per-level Gage R&R, bias, linearity, attribute agreement and verdict flips.
* **Study B** (`hath0r evals judges calibrate`, `judge-calibration-bot`): every LLM judge, JEV and any
  human or imported rater scores generated item banks with design truth. A many-facet Rasch model
  (`hath0r_cli.qa.rasch`) estimates part quality, criterion difficulty, judge severity and each judge's
  bias at each level, relative to anchor judges.

Decisions (approved by Ray on 2026-11-16): a judge x level cell is certified, removed for noise
(MnSq > 1.5), removed for bias (|psi| >= 0.20 logits, BH q 0.05), or not certified (SE > 0.10). We certify
and remove; we never adjust scores. Scorecards record the change's level and refuse an LLM judge that is
not certified there. ATC shows the panel; HATH0R-MCP exposes it read-only and uses it to decide whether
to trust JEV at a risk level.
