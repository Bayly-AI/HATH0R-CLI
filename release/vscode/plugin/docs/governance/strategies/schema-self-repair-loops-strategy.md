# Strategy: Programmatic Assertion & Schema Self-Repair Loops for Agent Workflows

> Canonical Strategy for Cognitive Self-Correction and Schema Repair  
> Product: `HATH0R-CLI` · Group: `hath0r-opensource` · Issue: #227

---

## 🎯 Executive Summary & Objectives

When autonomous agents generate structured payloads, SQL statements, JSON envelopes, or tool arguments, syntax errors and subtle contract schema violations can occur (e.g. stringified booleans, trailing commas in JSON, markdown backtick fences wrapping JSON, or missing required fields). Rather than failing immediately or crashing subagent execution, agent systems must employ **Programmatic Assertions and Self-Repair Loops**.

This strategy establishes the **`SchemaRepairEngine` and Assertion Feedback Loop** in `HATH0R-CLI`. By coupling deterministic pre-parsing sanitization (coercion of types, stripping markdown artifacts, trailing comma removal) with programmatic validation assertions (`AssertionGuardrail`), Hath0r CLI automatically repairs malformed outputs in-flight with zero hallucinations.

---

## 🏗️ Architecture: Schema Self-Repair Loop

```text
               Raw LLM Output / Tool Payload
                             │
                             ▼
┌────────────────────────────────────────────────────────────┐
│                    SchemaRepairEngine                      │
├────────────────────────────────────────────────────────────┤
│ 1. Markdown Code Fence Stripping (` ```json ... ``` `)     │
│ 2. Trailing Comma & Truncated Bracket Auto-Balancing       │
│ 3. Primitive Type Coercion (Strings -> Booleans/Numbers)   │
│ 4. Case-Insensitive Enum Normalization                     │
└────────────────────────────┬───────────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────────┐
│                    AssertionGuardrail                      │
├────────────────────────────────────────────────────────────┤
│ • Evaluates programmatic invariants & JSON Schema contract │
│ • If Valid: Returns clean parsed object                    │
│ • If Invalid: Emits structured error prompt for retry loop │
└────────────────────────────┬───────────────────────────────┘
                             │ Validated Payload
                             ▼
┌────────────────────────────────────────────────────────────┐
│              Durable Step Execution Envelope               │
└────────────────────────────────────────────────────────────┘
```

---

## 🛡️ Core Invariants

1. **Deterministic Pre-Execution Repair**: Trivial syntax corruptions (markdown fences, mismatched quotes, whitespace) MUST be repaired deterministically in $<1\text{ms}$ without invoking additional LLM turns.
2. **Contract Preservation**: Schema coercion must never invent missing business fields without an explicit schema default.
3. **Structured Assertion Feedback**: If a payload cannot be repaired deterministically, the guardrail emits a targeted error constraint for the retry loop.
