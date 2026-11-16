# Playbook: Judge calibration results

| Result | Meaning | Action |
|---|---|---|
| `certified` at a level | Precise, unbiased within 0.20 logits, fits the model | Use the judge at that level |
| `removed_bias` | Significant lean of 0.20 logits or more (positive = harsher) | Do not use at that level. Try a different prompt or model, then recalibrate |
| `removed_noise` | Misfit above 1.5 MnSq, or the judge alone separates items less than its own error | Do not use. Check for parse errors, temperature, truncated input |
| `not_certified` | Not enough information (SE above 0.10, too few items, all ratings in one category, no anchor) | Add items or replicates at that level; check `agreement_with_truth` for extreme cells |
| Study incomplete | Budget cap reached or a judge dropped after repeated errors | Nothing is certified; resume or raise the cap with approval |

Psi is relative to the anchors at the same level and centred within each judge (overall severity is in the
judge's main measure), so read the per-level pattern and the swing, not one number in isolation.
