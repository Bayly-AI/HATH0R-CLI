# CR-CONTEXT-SQUEEZE-001: Compress Context with SuperSqueeze (CRITICAL — Org-Wide · CANONICAL)

> **Status**: Active · **Tier**: Org Invariant (`RulePriority.ORG_INVARIANT`)
> **Scope**: All repositories across `/Users/raybayly/Development` (`OpenSource`, `1-Nation`, `BAI`, `Ray`, `Websites`, `Projects`)
> **Enforced by**: `hath0r squeeze`, `SuperSqueezeBot` (`SuperCompressBot`, `src/hath0r_cli/bots/supercompress_bot.py`),
> `SubstrateUtilizationBot`, `hath0r evals` (Tier 2 SuperSqueeze utilization ratio), `hath0r rules ensure-all`

---

## Rule

1. **Squeeze before you load**: Bulky context — whole files, logs, CI output, tool results, KB/RAG hits, transcripts,
   anything over roughly 2,000 tokens — MUST go through SuperSqueeze before it enters an agent's context window or a
   model prompt. Read the compressed output, not the raw text.
   - CLI: `hath0r squeeze -q "<active query>" -f <file>` or `hath0r squeeze -q "<active query>" -c "<text>"`.
   - Code: `SuperSqueezeBot` / `supersqueeze_bot` (alias of `SuperCompressBot`). Never hand-roll truncation or
     `head`/`[:N]` slicing as a substitute.
2. **Anchor on the active query**: `-q` is always the current task or question, so compression keeps what the task
   needs. Re-squeeze when the query changes.
3. **Quality floor**: Check `verifier.quality_score` (and `entity_recall`) in the response. Below `0.90`, lower
   `--threshold` and squeeze again, or switch to targeted reads (line ranges, `grep`, AST outlines via `hath0r code`).
   Never fall back to dumping the whole source.
4. **Local-first for sensitive content**: Use `--local` (deterministic, no network) for anything that may contain
   credentials, personal data, or private repository content. Secrets are never squeezed; redact them first.
5. **Exact-text exceptions**: Do not squeeze text that must be reproduced or edited verbatim: the lines of code being
   changed, diffs under review, quoted legal or licence text, and test fixtures. Load just those spans with targeted
   reads.
6. **Pipelines route through SuperSqueeze**: Agent pipelines that pack context (`CAGEngine.pack_context()`,
   `HybridCAGRAGRouter.rag_search()`, `HAHPProtocolManager.create_envelope()`, MCP tool responses) MUST call
   `SuperSqueezeBot`. `SubstrateUtilizationBot` audits this, and the Tier 2 eval scores the utilization ratio.
7. **Report savings**: The end-of-task Eval Scorecard Summary includes squeezed token savings (`savings_pct`) where
   SuperSqueeze ran.

## Rollout

```bash
hath0r rules ensure-all --rule CR-CONTEXT-SQUEEZE-001            # preview
hath0r rules ensure-all --rule CR-CONTEXT-SQUEEZE-001 --publish  # issue + PR per repository
hath0r rules status --rule CR-CONTEXT-SQUEEZE-001                # coverage on origin/development
```
