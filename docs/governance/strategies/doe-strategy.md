# Strategy: Sequential design of experiments (WS8, #593)

> **Strategy ID**: `ST-DOE-001` · **Owning Bot**: `doe-bot`

Taguchi arrays tell us which levels look best for many factors at once. They do not tell us where the
optimum sits between levels, or whether two factors interact. Hath0r now tunes in the classic sequence
(Montgomery, *Design and Analysis of Experiments*; NIST/SEMATECH 5.3):

1. **Screen**: a 2-level full or fractional factorial (2^(k-p)) with replicates, analysed by main-effects
   ANOVA. Only factors significant at alpha (default 0.05) go forward, at most three.
2. **Response surface**: a central composite (CCD) or Box-Behnken (BBD) design on the kept factors, a
   quadratic fit, and the predicted optimum inside the coded cube.
3. **Confirm**: runs at the predicted optimum must land inside the model's interval. Only a confirmed
   optimum is compounded as a `fact` memory node and treated as the new calibration.

- Bayesian optimisation (TPE) is an **optional dependency** (`pip install 'hath0r-cli[doe]'`, validated
  2026-11-11). Without optuna, `bayes` falls back to a CCD response surface and says so.
- Nothing is simulated. A study either receives measured responses or runs a real measurement command.
- Goal: the response is normally R_task, and the target is as close to 1.0 as possible.
