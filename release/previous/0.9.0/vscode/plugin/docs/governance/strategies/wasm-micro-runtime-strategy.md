# Capability-Based WASM Micro-Runtime Strategy

> Scope: **Hath0r CLI Zero-Trust Agent Sandboxing Subsystem**  
> Rule Reference: **CR-CLI-ENTRY-001 / CR-SUBSTRATE-001 (Zero-Trust Sandboxing)**  
> Issue: **#241**

---

## 1. Executive Summary

Autonomous agents dynamically executing untrusted user-supplied code or third-party extensions in host shells create unacceptable attack surfaces (arbitrary file read/writes, unauthorized network egress, environmental tampering). Full Linux container virtualization incurs substantial overhead (seconds of startup latency, gigabytes of RAM).

WebAssembly (WASM) micro-sandboxes with WebAssembly System Interface (WASI) provide sub-millisecond execution times, tiny memory footprints, and strict capability-based authorization where host capabilities (filesystem roots, socket addresses, fuel limits) must be explicitly granted.

---

## 2. Architecture & Capability Grants

```
                ┌────────────────────────────────────────────────────────┐
                │          Untrusted Agent Tool / Code Module            │
                │                     (module.wasm)                      │
                └───────────────────────────┬────────────────────────────┘
                                            │
                                            ▼
                ┌────────────────────────────────────────────────────────┐
                │                   WasmRuntimeBot                       │
                │        Capability-Based Deny-By-Default Gate           │
                ├────────────────────────────────────────────────────────┤
                │  • Read Roots:    /path/allowed                        │
                │  • Write Roots:   /tmp/sandbox_out                     │
                │  • Network Hosts: api.approved.org                     │
                │  • Fuel Limit:    100,000,000 instructions             │
                │  • Memory Cap:    64 MB                                │
                └───────────────────────────┬────────────────────────────┘
                                            │
                                            ▼
                ┌────────────────────────────────────────────────────────┐
                │             Isolated Host Kernel Boundary              │
                └────────────────────────────────────────────────────────┘
```

---

## 3. CLI Interfaces

- `hath0r wasm run <module.wasm> [--allow-read <dir>] [--allow-write <dir>] [--allow-net <host>] [--memory-mb 64]`
- `hath0r wasm validate <module.wasm>`
- `hath0r wasm status`
