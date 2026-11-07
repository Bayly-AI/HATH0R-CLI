# Strategy: Lazy Command & Telemetry Loading for Zero-Latency CLI Startup

> Canonical Strategy for High-Performance Modular CLI Command Resolution  
> Product: `HATH0R-CLI` · Group: `hath0r-opensource` · Issue: #223

---

## 🎯 Executive Summary & Objectives

Command-line interfaces used in high-frequency automation and agentic tool loops must return results with sub-100ms latency. In early architectures, all command modules, complex schemas, heavy third-party parsers, and telemetry SDKs were imported eagerly during `import hath0r_cli.cli`, producing an unacceptable **~663ms** startup overhead per invocation.

This strategy establishes the **Lazy Command & Telemetry Resolution Architecture** for `HATH0R-CLI`. By replacing eager module evaluation with dynamic attribute dispatch and deferred telemetry initialization, the CLI achieves near-instantaneous startup times (<75ms) while preserving 100% backward compatibility across all 34 command groups.

---

## 🏗️ Architecture: Dynamic Lazy Command Dispatch

```text
hath0r <command> [args]
         │
         ▼
┌─────────────────────────────────┐
│     Hath0rLazyCommandGroup      │  ◄── Lightweight Click Group (no heavy imports)
├─────────────────────────────────┤
│ • list_commands(ctx)            │  ◄── Reads static command name registry
│ • get_command(ctx, cmd_name)    │  ◄── Dynamically imports ONLY requested module
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│ Target Command Module Executed  │  (e.g., hath0r_cli.commands.vision)
└─────────────────────────────────┘
```

### Core Design Invariants
1. **Zero Eager Subcommand Imports**: `hath0r_cli/commands/__init__.py` maintains a lightweight mapping table of `{command_name: (module_path, attribute_name)}` without importing the underlying modules.
2. **Deferred Telemetry Bootstrapping**: OpenTelemetry SDK tracers and exporter threads are initialized on demand upon first span creation rather than on CLI entry.
3. **Full Click Compatibility**: Command help, completions, subcommands, and flags function identically to eager registration.
4. **Performance Threshold**: CLI module import time `python3 -c "import hath0r_cli.cli"` must remain below 100ms.
