# Playbook: Registering and Benchmarking Modular Lazy Commands

> Operational Playbook for Hath0r CLI Lazy Command Architecture  
> Product: `HATH0R-CLI` · Group: `hath0r-opensource` · Issue: #223

---

## 📋 Overview

This playbook provides operational procedures for adding new modular commands to `HATH0R-CLI` while maintaining sub-100ms startup latency.

---

## 🛠️ Adding a New Command to the Lazy Registry

When implementing a new command group (e.g., `hath0r foo` in `src/hath0r_cli/commands/foo.py`), register it in `src/hath0r_cli/commands/__init__.py`:

```python
# In src/hath0r_cli/commands/__init__.py
COMMAND_REGISTRY: Dict[str, Tuple[str, str]] = {
    # ... existing commands ...
    "foo": ("hath0r_cli.commands.foo", "foo"),
}
```

Do **not** import `from hath0r_cli.commands.foo import foo` at the top level of `commands/__init__.py`.

---

## ⏱️ Benchmarking Startup Latency

To verify that new commands or dependencies do not regress CLI startup latency:

```bash
# Benchmark module import latency
python3 -c "import time; t0 = time.perf_counter(); import hath0r_cli.cli; print(f'Import time: {(time.perf_counter()-t0)*1000:.2f}ms')"

# Benchmark command execution latency
time hath0r --version
```
