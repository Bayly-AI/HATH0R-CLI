# Strategy: Andon stop-the-line (WS6, #588, #589)

> **Strategy ID**: `ST-ANDON-001` · **Owning Bot**: `andon-bot`

In the Toyota Production System anyone can stop the line when they see a defect, and the line stays stopped
until the cause is dealt with. Hath0r applies this to agent work: a bot that detects a problem it must not
work past (a tripped token budget, a blocking SPC signal, a failed step marked `andon: stop`) raises a stop.
While a stop is active no workflow step or agent DAG starts. A person acknowledges it, fixes the cause and
clears it. Every event is hash-chained so a stop cannot be silently removed.
