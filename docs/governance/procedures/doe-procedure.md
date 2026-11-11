# Procedure: Sequential design of experiments

> **Procedure ID**: `PR-DOE-001` · **Owning Bot**: `doe-bot`

1. Write the factor ranges in a spec (`cfg/cccd/doe-spec.yaml`) or pass `--factor name=low:high`.
2. Screen: `hath0r optimize screen --spec <spec>` prints the design (status `awaiting_responses`). Run each
   point at least twice, then add `responses:` to the spec and run again, or let doe-bot measure with `--measure-cmd`.
3. Keep the significant factors. If none are significant, stop: the ranges are too narrow or the
   measurement is too noisy (check the gauge first with `hath0r evals msa run`).
4. Response surface on the kept factors: `hath0r optimize rsm --spec <spec with kept factors and responses>`.
5. Confirm at the predicted optimum: `hath0r optimize confirm <study_id> --observed v1,v2,v3`.
6. Only a confirmed optimum may change calibrated parameters. `hath0r cccd calibrate --strategy sequential`
   runs steps 2 to 5 end to end.
