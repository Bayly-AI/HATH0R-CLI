# Playbook: DMAIC

> **Playbook ID**: `PB-DMAIC-001` · **Owning Bot**: `dmaic-project-bot`

| Situation | Play |
|---|---|
| Close refused: too few points | Keep working; the CTQ accrues a point per eval |
| Close refused: out of control | The change is not stable yet; find the signal with `hath0r spc chart` |
| Baseline is out of control | Note it; the process was already shifting, so judge Control on the post-change chart only |
| Improvement is negative | Revert or rethink; record what you learned with `hath0r rca why` |
| Gain held | Add a control: a guard (poka-yoke), an FMEA re-rating, or SPC block mode for the CTQ |
