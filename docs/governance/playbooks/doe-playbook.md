# Playbook: Sequential design of experiments

> **Playbook ID**: `PB-DOE-001` · **Owning Bot**: `doe-bot`

| Situation | Play |
|---|---|
| No significant factors after screening | Widen the ranges, add replicates, or check the gauge (%GRR) before tuning |
| More than three significant factors | doe-bot keeps the three with the largest F; screen again on the rest later |
| Optimum on the edge of the cube | The true optimum is outside the ranges; shift the ranges and run a new rsm |
| Confirmation fails | Do not adopt the optimum. Look for curvature the model missed or a drifting process (`hath0r spc chart`) |
| optuna missing | `bayes` falls back to a CCD response surface; install the `doe` extra for TPE |
| Measurement command fails | The study stops with the command's stderr; nothing is guessed |
