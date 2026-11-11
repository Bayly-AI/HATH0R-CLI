# Strategy: Root cause with Pareto, Ishikawa and 5 Whys (WS9, #591)

> **Strategy ID**: `ST-RCA-001` · **Owning Bot**: `root-cause-bot`

Most failures come from a few causes. Every failed gate is tagged with one of six cause categories (the 6M
of an Ishikawa diagram adapted to agents, `cfg/quality/cause-categories.yaml`): Method, Model, Material,
Measurement, Machine and Operator. A monthly Pareto names the vital few; the top cause gets a fishbone, a 5 Whys
record and a DMAIC project. Each 5 Whys becomes an insight node in memory.
