# Tree-Sitter & AST Code Intelligence Strategy

> Scope: **Hath0r CLI Code Parsing & Context Pruning Subsystem**  
> Rule Reference: **CR-CLI-ENTRY-001 / CR-SUBSTRATE-001**  
> Issue: **#236**

---

## 1. Executive Summary

As repository size grows, injecting entire raw code files into LLM context windows causes severe token exhaustion, latency spikes, and attention dilution. SOTA developer agents parse source code into Concrete Syntax Trees (CST) and Abstract Syntax Trees (AST) to extract compact symbol outlines, function definitions, call hierarchies, and to validate edits prior to disk persistence.

This strategy establishes structural code intelligence inside `hath0r_cli`, providing multi-language symbol extraction (`hath0r code outline`), symbol lookup (`hath0r code symbols`), and pre-commit syntax validation.

---

## 2. Architecture & Design Principles

```
                    ┌──────────────────────────────┐
                    │      Source Code File        │
                    │ (Python, TS, JS, Rust, Go)   │
                    └──────────────┬───────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────────┐
                    │     CodeSymbolExtractor      │
                    │   (AST & Tree-Sitter Core)   │
                    └──────────────┬───────────────┘
                                   │
        ┌──────────────────────────┼──────────────────────────┐
        ▼                          ▼                          ▼
┌────────────────┐        ┌──────────────────┐       ┌─────────────────┐
│ Code Outlining │        │  Symbol Lookup   │       │ Syntax Guardrail│
│ (Compact AST)  │        │ (Calls/Signatures│       │  (Pre-commit)   │
└────────────────┘        └──────────────────┘       └─────────────────┘
```

1. **AST-Based Context Pruning**:
   - Strips internal function implementations and bodies while retaining class names, method signatures, parameter types, return types, and docstrings.
   - Reduces context consumption by 40–60%.
2. **Multi-Language Support**:
   - Python native AST parser.
   - Deterministic structural regex & Tree-Sitter grammars for TypeScript, JavaScript, Rust, Go, and Shell.
3. **Pre-Commit Syntax Validation**:
   - Verifies whether an in-flight LLM diff is syntactically well-formed before writing to the filesystem.

---

## 3. CLI Interfaces

- `hath0r code outline <file>`: Emits concise structural outline of functions, classes, and types.
- `hath0r code symbols <file>`: Extracts indexed list of symbols with line ranges.
- `hath0r code validate <file>`: Verifies syntax integrity across supported languages.
