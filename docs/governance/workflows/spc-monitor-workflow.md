# Workflow: Statistical process control (`cfg/factories/spc-monitor-factory.yaml`)

> **Workflow ID**: `cfg/factories/spc-monitor-factory.yaml` · **Owning Bots**: `spc-monitor-bot`, `phoenix-observer-bot`

1. **`gate` (`spc-monitor-bot`)**: chart every metric, compute capability, write `.hath0r/spc/latest.json`.
   Warn mode never fails; block mode fails and raises an Andon stop. Also runs as a `continue` step in
   `end-of-task-factory.yaml` and `local-qgates-factory.yaml`.
