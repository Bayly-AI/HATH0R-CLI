"""Deterministic measurement command for CCCD calibration tests: reads a JSON point, prints one response."""

import json
import sys

point = json.load(sys.stdin)
score = 1.0 - (point["temperature"] - 0.2) ** 2 - (point["top_p"] - 0.95) ** 2 - (point["guardrail_threshold"] - 0.85) ** 2
print(round(score, 6))
