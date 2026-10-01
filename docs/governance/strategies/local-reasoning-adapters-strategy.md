# Local Reasoning & Code Adapters Strategy (DeepSeek-R1 & Qwen2.5-Coder)

> Scope: **Hath0r CLI Local Inference & Offline Cognitive Subsystem**  
> Rule Reference: **CR-CLI-ENTRY-001 / CR-SUBSTRATE-001 (Zero-Trust Sandboxing & Reasoning)**  
> Issue: **#240**

---

## 1. Executive Summary

Autonomous agent workflows require local, offline reasoning capabilities for confidential codebases, air-gapped environments, and zero-latency operational guards. Modern reasoning models (e.g. `DeepSeek-R1-Distill-Qwen`) emit extensive internal Chain-of-Thought (CoT) traces enclosed in `<think> ... </think>` delimiters, while coding models (`Qwen2.5-Coder`) require precise markdown block structuring and tool calling schemas.

This strategy establishes `LocalModelBot` to parse, isolate, and stream internal reasoning traces separately from final response artifacts, integrating with Ollama, MLX, llama.cpp, and local runtime sockets.

---

## 2. Architecture & CoT Splitting

```
               ┌────────────────────────────────────────────────────────┐
               │    Local Model Stream (DeepSeek-R1 / Qwen2.5-Coder)     │
               └───────────────────────────┬────────────────────────────┘
                                           │
                                           ▼
               ┌────────────────────────────────────────────────────────┐
               │                  LocalModelBot Parser                  │
               │   Regex / Token Stream Demux: <think> ... </think>     │
               └───────────────────────────┬────────────────────────────┘
                                           │
                    ┌──────────────────────┴──────────────────────┐
                    │                                             │
                    ▼                                             ▼
     ┌─────────────────────────────┐               ┌─────────────────────────────┐
     │    Internal Reasoning CoT   │               │   Final Execution / Code    │
     │  (Telemetry, Trace Log, UI) │               │   (Tool Calls, File Diffs)  │
     └─────────────────────────────┘               └─────────────────────────────┘
```

---

## 3. CLI Interfaces

- `hath0r local reason "<prompt>" [--model deepseek-r1:7b] [--show-cot]`
- `hath0r local code "<prompt>" [--model qwen2.5-coder:7b]`
- `hath0r local models`
