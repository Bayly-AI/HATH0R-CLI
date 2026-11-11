"""Industrial quality-engineering statistics shared by Hath0r QA bots (epic #580).

Pure-Python implementations (no numpy/scipy runtime dependency) of:

* ``stats``  - descriptive helpers, F-distribution tail, small linear solver
* ``msa``    - Gage R&R (ANOVA method) and attribute agreement for eval gauges
* ``spc``    - I-MR, EWMA, CUSUM charts, Western Electric rules, Cp/Cpk
* ``doe``    - fractional factorial, CCD, Box-Behnken, main-effects ANOVA, quadratic RSM
* ``fmea``   - severity/occurrence/detection scoring, RPN and action priority
"""

from __future__ import annotations

__all__ = ["doe", "fmea", "msa", "spc", "stats"]
