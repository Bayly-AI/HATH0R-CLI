# Strategy: HATH0R CLI Voice Command Group

> Document Type: **Strategy** (`cr-workflow-doc-001`)  
> Product: **HATH0R-CLI** · Issue: #131 · SemVer: `minor`

## 1. Context & Motivation

To provide operators with hands-free, low-latency control of Hath0r development and agent operations, the CLI exposes the `hath0r voice` command surface.

The command surface adheres to CLI-First governance (`cli-first-rules.md`), structured JSON envelope output (`hath0r.cli.response/1`), and three-tier trust governance (guest, elevated, sovereign).

## 2. Capabilities

1. `hath0r voice status`: Inspects local audio capture capabilities, speech synthesis engines, fast-path router health, and active governance tier.
2. `hath0r voice exec "<transcript>"`: Single-shot evaluation of spoken or transcribed utterances, executing fast-path actions in sub-50ms.
3. `hath0r voice listen`: Interactive continuous ambient or push-to-talk listening loop with rich terminal visual feedback.
