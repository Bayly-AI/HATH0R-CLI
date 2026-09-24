---
id: HATHOR-REPORT-MULTI-001
title: "Multi-tree Hath0r integration compliance — 1-Nation, BAI, Websites"
summary: "Point-in-time audit of all product trees under 1-Nation, BAI, and Websites against HATHOR-PLAYBOOK-001 / CR-HATH0R-INIT-001."
doc_type: REPORT
diataxis: mixed
audience: [operator, architect, agent]
tags: [hath0r, compliance, multi-tree]
version: 1.0.0
status: draft
created: 2026-09-19
updated: 2026-09-19
owner: "Raymond Bayly (BaylyAI)"
review: {trust: machine-checked, reviewed_by: null, reviewed_at: null, interval: null, next_review: null}
stale: false
---

# HATHOR-REPORT-MULTI-001 — Multi-tree Hath0r compliance

- **Generated (UTC):** 2026-09-19T13:16:07Z
- **Operator CLI:** `hath0r` 0.2.0
- **Playbook:** HATHOR-PLAYBOOK-001 / CR-HATH0R-INIT-001
- **Trees:** `1-Nation/`, `BAI/`, `Websites/`
- **Machine data:** `docs/reports/hath0r-multi-tree-compliance-20260919.json` (this control-tower copy)

## 0. Executive verdict

| Segment | PASS | PARTIAL | FAIL | NOT_INIT | Notes |
|---------|-----:|--------:|-----:|---------:|-------|
| Websites UXP (BC) | 1 | 0 | 0 | 0 | Fully integrated standalone reference |
| 1-Nation UXP | 0 | 1 | 0 | 0 | UPL+bootstrap ok; missing agent maps/compliance pack |
| BAI UXP | 0 | 1 | 0 | 0 | UPL+bootstrap ok; missing agent maps/compliance pack |
| BAI/AEGIS products | 0 | 0 | 16 | 1 | Legacy `.ai`/`.infraOS`/`.aegis` — **not** Hath0r UPL |
| Empty placeholders | 0 | 0 | 0 | 3 | doctor-sleep, knithappens, 1-Nation/site |

**Bottom line:** Marketing/product **UXP** apps under 1-Nation, BAI, and Websites are on the Hath0r standalone fileset (0.2.0) with healthy bootstrap. **Bayly Consulting** is the only full PASS including compliance pack. The private **BAI/AEGIS/** fleet remains on legacy InfraOS/AEGIS hidden roots and is **not** Hath0r-integrated despite the shared “should use Hath0r” intent.

## 1. Method

Scored each git repo (and non-git placeholders) against:

1. UPL core (AGENTS, `.hath0r/`, cfg, contracts, bootstrap, MANIFEST, runbook)
2. AEGIS independence (no `.aegis/.ai/.infraOS`)
3. Agent CLI docs (`hath0r` teaching + bootstrap)
4. Agent maps (`docs/INDEX.md`, `llms.txt`)
5. Compliance pack (report/checklist/procedure/strategy/playbook)
6. Org gates (CR-HATH0R-INIT-001, CR-BAI-001)

Live checks: `hath0r --version`, `./bin/hath0r-bootstrap.sh` on the three UXPs (all **ok**). Suite doctor remains OpenSource-scoped (23/23) when `HATH0R_GROUP_ROOT` is set.

## 2. Full scoreboard

| Path | Score | Verdict | product_id | mode | core | legacy |
|------|------:|---------|------------|------|------|--------|
| `1-Nation/UXP` | 77.5 | **PARTIAL** | `1nation-uxp` | `standalone` | 10/10 | `—` |
| `BAI/AEGIS` | 5.5 | **NOT_INIT** | `—` | `—` | 1/10 | `—` |
| `BAI/AEGIS/ATC` | 23.5 | **FAIL** | `—` | `—` | 3/10 | `.ai` |
| `BAI/AEGIS/CLI` | 30.5 | **FAIL** | `—` | `—` | 3/10 | `.ai, .infraOS, .infraos` |
| `BAI/AEGIS/CMCP` | 26.5 | **FAIL** | `—` | `—` | 3/10 | `.ai` |
| `BAI/AEGIS/Ctrl` | 21.5 | **FAIL** | `—` | `—` | 3/10 | `.ai` |
| `BAI/AEGIS/Data` | 32.5 | **FAIL** | `—` | `—` | 3/10 | `.ai` |
| `BAI/AEGIS/EA` | 21.5 | **FAIL** | `—` | `—` | 3/10 | `.ai` |
| `BAI/AEGIS/EDGE` | 32.5 | **FAIL** | `—` | `—` | 3/10 | `.ai, .infraOS, .infraos` |
| `BAI/AEGIS/Forge` | 21.5 | **FAIL** | `—` | `—` | 3/10 | `.ai` |
| `BAI/AEGIS/Gate` | 32.5 | **FAIL** | `—` | `—` | 3/10 | `.ai` |
| `BAI/AEGIS/HATH0R` | 17.5 | **NOT_INIT** | `—` | `—` | 1/10 | `.aegis, .ai` |
| `BAI/AEGIS/Know` | 36.5 | **FAIL** | `—` | `—` | 3/10 | `.ai, .infraOS, .infraos` |
| `BAI/AEGIS/MCP` | 26.5 | **FAIL** | `—` | `—` | 3/10 | `.ai` |
| `BAI/AEGIS/Model` | 28.5 | **FAIL** | `—` | `—` | 3/10 | `.ai` |
| `BAI/AEGIS/OBS` | 28.5 | **FAIL** | `—` | `—` | 3/10 | `.ai` |
| `BAI/AEGIS/RT` | 28.5 | **FAIL** | `—` | `—` | 3/10 | `.ai, .infraOS, .infraos` |
| `BAI/AEGIS/UXP` | 32.5 | **FAIL** | `—` | `—` | 3/10 | `.ai, .infraOS, .infraos` |
| `BAI/AEGIS/VS` | 21.5 | **FAIL** | `—` | `—` | 3/10 | `.ai, .infraOS, .infraos` |
| `BAI/UXP` | 82.0 | **PARTIAL** | `baylyai-uxp` | `standalone` | 10/10 | `—` |
| `Websites/bayly-consulting/UXP` | 90.0 | **PASS** | `bayly-consulting-uxp` | `standalone` | 10/10 | `—` |
| `Websites/doctor-sleep` | 0.0 | **NOT_INIT** | `—` | `—` | 0/10 | `—` |
| `Websites/knithappens` | 0.0 | **NOT_INIT** | `—` | `—` | 0/10 | `—` |
| `1-Nation/site` | 0.0 | **NOT_INIT** | `—` | `—` | 0/10 | `—` |

## 3. Websites

| Path | Score | Verdict | product_id | mode | core | legacy |
|------|------:|---------|------------|------|------|--------|
| `Websites/bayly-consulting/UXP` | 90.0 | **PASS** | `bayly-consulting-uxp` | `standalone` | 10/10 | `—` |
| `Websites/doctor-sleep` | 0.0 | **NOT_INIT** | `—` | `—` | 0/10 | `—` |
| `Websites/knithappens` | 0.0 | **NOT_INIT** | `—` | `—` | 0/10 | `—` |

### Findings
- **bayly-consulting/UXP** — PASS (~90). Reference standalone integration + full compliance pack (BC-REPORT-001).
- **doctor-sleep**, **knithappens** — empty placeholders (no git). NOT_INIT until product repos exist.

## 4. 1-Nation

| Path | Score | Verdict | product_id | mode | core | legacy |
|------|------:|---------|------------|------|------|--------|
| `1-Nation/UXP` | 77.5 | **PARTIAL** | `1nation-uxp` | `standalone` | 10/10 | `—` |
| `1-Nation/site` | 0.0 | **NOT_INIT** | `—` | `—` | 0/10 | `—` |

### Findings
- **1-Nation/UXP** — PARTIAL (77.5). Core UPL 10/10, bootstrap ok, product_id `1nation-uxp`, mode standalone. Gaps: docs INDEX/llms + compliance pack (report/checklist/procedure/strategy/playbook).
- **1-Nation/site** — non-git placeholder. NOT_INIT.

## 5. BAI

| Path | Score | Verdict | product_id | mode | core | legacy |
|------|------:|---------|------------|------|------|--------|
| `BAI/AEGIS` | 5.5 | **NOT_INIT** | `—` | `—` | 1/10 | `—` |
| `BAI/AEGIS/ATC` | 23.5 | **FAIL** | `—` | `—` | 3/10 | `.ai` |
| `BAI/AEGIS/CLI` | 30.5 | **FAIL** | `—` | `—` | 3/10 | `.ai, .infraOS, .infraos` |
| `BAI/AEGIS/CMCP` | 26.5 | **FAIL** | `—` | `—` | 3/10 | `.ai` |
| `BAI/AEGIS/Ctrl` | 21.5 | **FAIL** | `—` | `—` | 3/10 | `.ai` |
| `BAI/AEGIS/Data` | 32.5 | **FAIL** | `—` | `—` | 3/10 | `.ai` |
| `BAI/AEGIS/EA` | 21.5 | **FAIL** | `—` | `—` | 3/10 | `.ai` |
| `BAI/AEGIS/EDGE` | 32.5 | **FAIL** | `—` | `—` | 3/10 | `.ai, .infraOS, .infraos` |
| `BAI/AEGIS/Forge` | 21.5 | **FAIL** | `—` | `—` | 3/10 | `.ai` |
| `BAI/AEGIS/Gate` | 32.5 | **FAIL** | `—` | `—` | 3/10 | `.ai` |
| `BAI/AEGIS/HATH0R` | 17.5 | **NOT_INIT** | `—` | `—` | 1/10 | `.aegis, .ai` |
| `BAI/AEGIS/Know` | 36.5 | **FAIL** | `—` | `—` | 3/10 | `.ai, .infraOS, .infraos` |
| `BAI/AEGIS/MCP` | 26.5 | **FAIL** | `—` | `—` | 3/10 | `.ai` |
| `BAI/AEGIS/Model` | 28.5 | **FAIL** | `—` | `—` | 3/10 | `.ai` |
| `BAI/AEGIS/OBS` | 28.5 | **FAIL** | `—` | `—` | 3/10 | `.ai` |
| `BAI/AEGIS/RT` | 28.5 | **FAIL** | `—` | `—` | 3/10 | `.ai, .infraOS, .infraos` |
| `BAI/AEGIS/UXP` | 32.5 | **FAIL** | `—` | `—` | 3/10 | `.ai, .infraOS, .infraos` |
| `BAI/AEGIS/VS` | 21.5 | **FAIL** | `—` | `—` | 3/10 | `.ai, .infraOS, .infraos` |
| `BAI/UXP` | 82.0 | **PARTIAL** | `baylyai-uxp` | `standalone` | 10/10 | `—` |

### Findings
- **BAI/UXP** — PARTIAL (82). Core UPL 10/10, bootstrap ok, product_id `baylyai-uxp`. Same agent-map/compliance-pack gaps as 1-Nation.
- **BAI/AEGIS/** (16 products + parent) — FAIL/NOT_INIT. Dominant legacy root is **`.ai/`**; several also carry **`.infraOS`** / **`.aegis`**. These are private AEGIS product trees, not OpenSource Hath0r members. Hath0r migration requires CR-HATH0R-INIT-001 (playbook + same-tech runbook + `.hath0r/` only + contracts pin) — do **not** register into OpenSource `products.yaml` unless explicitly promoted.

## 6. CLI / agent contact

| Check | Result |
|-------|--------|
| `hath0r` on PATH | 0.2.0 |
| JSON version envelope | ok |
| UXP bootstraps (1N, BAI, BC) | ok |
| OpenSource doctor (optional) | 23/23 ok with `HATH0R_GROUP_ROOT` |
| `hath0r planes` / `schema` | available (ADR-003 discovery) |

Agents should consume: nearest `AGENTS.md` → product `docs/llms.txt`/`INDEX.md` when present → framework `OpenSource/hath0r/docs/index.json`.

## 7. Priority remediation

### P0 — AEGIS fleet Hath0r migration plan (BAI)
For each `BAI/AEGIS/*` product:
1. Issue-first branch under product repo
2. Follow HATHOR-PLAYBOOK-001 (do not invent layout)
3. Replace/forbid `.ai`, `.infraOS`, `.aegis` with `.hath0r/` only
4. Pin contracts 0.2.0; add bootstrap; write runbook
5. Keep private — not OpenSource suite members by default

### P1 — Close PARTIAL on 1-Nation UXP + BAI UXP
Add compliance pack + INDEX/llms (same pattern as BC-REPORT-001).

### P2 — Placeholder sites
Initialize only when real product work starts (doctor-sleep, knithappens, 1-Nation/site).

## 8. Per-repo top gaps (non-PASS)


### `1-Nation/UXP` — PARTIAL (77.5)
- missing/issue: `docs/INDEX.md`
- missing/issue: `docs/llms.txt`
- missing/issue: `CR-BAI-001`
- missing/issue: `pack:report`
- missing/issue: `pack:checklist`
- missing/issue: `pack:procedure`
- missing/issue: `pack:strategy`
- missing/issue: `pack:playbook`

### `BAI/AEGIS` — NOT_INIT (5.5)
- missing/issue: `.hath0r/`
- missing/issue: `KB stub`
- missing/issue: `cfg/product.yaml`
- missing/issue: `cfg/suite.yaml`
- missing/issue: `cfg/knowledge-tower.yaml`
- missing/issue: `contracts/`
- missing/issue: `bootstrap`
- missing/issue: `MANIFEST.json`
- missing/issue: `runbook`
- missing/issue: `docs/INDEX.md`
- missing/issue: `docs/llms.txt`
- missing/issue: `CR-HATH0R-INIT-001`

### `BAI/AEGIS/ATC` — FAIL (23.5)
- missing/issue: `.hath0r/`
- missing/issue: `KB stub`
- missing/issue: `cfg/product.yaml`
- missing/issue: `contracts/`
- missing/issue: `bootstrap`
- missing/issue: `MANIFEST.json`
- missing/issue: `runbook`
- missing/issue: `docs/INDEX.md`
- missing/issue: `docs/llms.txt`
- missing/issue: `legacy roots: .ai`
- missing/issue: `pack:checklist`
- missing/issue: `pack:procedure`

### `BAI/AEGIS/CLI` — FAIL (30.5)
- missing/issue: `.hath0r/`
- missing/issue: `KB stub`
- missing/issue: `cfg/product.yaml`
- missing/issue: `contracts/`
- missing/issue: `bootstrap`
- missing/issue: `MANIFEST.json`
- missing/issue: `runbook`
- missing/issue: `docs/llms.txt`
- missing/issue: `legacy roots: .ai, .infraOS, .infraos`
- missing/issue: `pack:checklist`
- missing/issue: `pack:procedure`
- missing/issue: `pack:strategy`

### `BAI/AEGIS/CMCP` — FAIL (26.5)
- missing/issue: `.hath0r/`
- missing/issue: `KB stub`
- missing/issue: `cfg/product.yaml`
- missing/issue: `contracts/`
- missing/issue: `bootstrap`
- missing/issue: `MANIFEST.json`
- missing/issue: `runbook`
- missing/issue: `docs/llms.txt`
- missing/issue: `legacy roots: .ai`
- missing/issue: `pack:report`
- missing/issue: `pack:checklist`
- missing/issue: `pack:procedure`

### `BAI/AEGIS/Ctrl` — FAIL (21.5)
- missing/issue: `.hath0r/`
- missing/issue: `KB stub`
- missing/issue: `cfg/product.yaml`
- missing/issue: `contracts/`
- missing/issue: `bootstrap`
- missing/issue: `MANIFEST.json`
- missing/issue: `runbook`
- missing/issue: `docs/INDEX.md`
- missing/issue: `docs/llms.txt`
- missing/issue: `legacy roots: .ai`
- missing/issue: `pack:report`
- missing/issue: `pack:checklist`

### `BAI/AEGIS/Data` — FAIL (32.5)
- missing/issue: `.hath0r/`
- missing/issue: `KB stub`
- missing/issue: `cfg/product.yaml`
- missing/issue: `contracts/`
- missing/issue: `bootstrap`
- missing/issue: `MANIFEST.json`
- missing/issue: `runbook`
- missing/issue: `docs/llms.txt`
- missing/issue: `legacy roots: .ai`
- missing/issue: `pack:procedure`
- missing/issue: `pack:strategy`

### `BAI/AEGIS/EA` — FAIL (21.5)
- missing/issue: `.hath0r/`
- missing/issue: `KB stub`
- missing/issue: `cfg/product.yaml`
- missing/issue: `contracts/`
- missing/issue: `bootstrap`
- missing/issue: `MANIFEST.json`
- missing/issue: `runbook`
- missing/issue: `docs/INDEX.md`
- missing/issue: `docs/llms.txt`
- missing/issue: `legacy roots: .ai`
- missing/issue: `pack:report`
- missing/issue: `pack:checklist`

### `BAI/AEGIS/EDGE` — FAIL (32.5)
- missing/issue: `.hath0r/`
- missing/issue: `KB stub`
- missing/issue: `cfg/product.yaml`
- missing/issue: `contracts/`
- missing/issue: `bootstrap`
- missing/issue: `MANIFEST.json`
- missing/issue: `runbook`
- missing/issue: `docs/llms.txt`
- missing/issue: `legacy roots: .ai, .infraOS, .infraos`
- missing/issue: `pack:procedure`
- missing/issue: `pack:strategy`

### `BAI/AEGIS/Forge` — FAIL (21.5)
- missing/issue: `.hath0r/`
- missing/issue: `KB stub`
- missing/issue: `cfg/product.yaml`
- missing/issue: `contracts/`
- missing/issue: `bootstrap`
- missing/issue: `MANIFEST.json`
- missing/issue: `runbook`
- missing/issue: `docs/INDEX.md`
- missing/issue: `docs/llms.txt`
- missing/issue: `legacy roots: .ai`
- missing/issue: `pack:report`
- missing/issue: `pack:checklist`

### `BAI/AEGIS/Gate` — FAIL (32.5)
- missing/issue: `.hath0r/`
- missing/issue: `KB stub`
- missing/issue: `cfg/product.yaml`
- missing/issue: `contracts/`
- missing/issue: `bootstrap`
- missing/issue: `MANIFEST.json`
- missing/issue: `runbook`
- missing/issue: `docs/llms.txt`
- missing/issue: `legacy roots: .ai`
- missing/issue: `pack:procedure`
- missing/issue: `pack:strategy`

### `BAI/AEGIS/HATH0R` — NOT_INIT (17.5)
- missing/issue: `.hath0r/`
- missing/issue: `KB stub`
- missing/issue: `cfg/product.yaml`
- missing/issue: `cfg/suite.yaml`
- missing/issue: `cfg/knowledge-tower.yaml`
- missing/issue: `contracts/`
- missing/issue: `bootstrap`
- missing/issue: `MANIFEST.json`
- missing/issue: `runbook`
- missing/issue: `docs/INDEX.md`
- missing/issue: `docs/llms.txt`
- missing/issue: `legacy roots: .aegis, .ai`

### `BAI/AEGIS/Know` — FAIL (36.5)
- missing/issue: `.hath0r/`
- missing/issue: `KB stub`
- missing/issue: `cfg/product.yaml`
- missing/issue: `contracts/`
- missing/issue: `bootstrap`
- missing/issue: `MANIFEST.json`
- missing/issue: `runbook`
- missing/issue: `docs/llms.txt`
- missing/issue: `legacy roots: .ai, .infraOS, .infraos`

### `BAI/AEGIS/MCP` — FAIL (26.5)
- missing/issue: `.hath0r/`
- missing/issue: `KB stub`
- missing/issue: `cfg/product.yaml`
- missing/issue: `contracts/`
- missing/issue: `bootstrap`
- missing/issue: `MANIFEST.json`
- missing/issue: `runbook`
- missing/issue: `docs/llms.txt`
- missing/issue: `legacy roots: .ai`
- missing/issue: `pack:report`
- missing/issue: `pack:checklist`
- missing/issue: `pack:procedure`

### `BAI/AEGIS/Model` — FAIL (28.5)
- missing/issue: `.hath0r/`
- missing/issue: `KB stub`
- missing/issue: `cfg/product.yaml`
- missing/issue: `contracts/`
- missing/issue: `bootstrap`
- missing/issue: `MANIFEST.json`
- missing/issue: `runbook`
- missing/issue: `docs/llms.txt`
- missing/issue: `legacy roots: .ai`
- missing/issue: `pack:checklist`
- missing/issue: `pack:procedure`
- missing/issue: `pack:strategy`

### `BAI/AEGIS/OBS` — FAIL (28.5)
- missing/issue: `.hath0r/`
- missing/issue: `KB stub`
- missing/issue: `cfg/product.yaml`
- missing/issue: `contracts/`
- missing/issue: `bootstrap`
- missing/issue: `MANIFEST.json`
- missing/issue: `runbook`
- missing/issue: `docs/llms.txt`
- missing/issue: `legacy roots: .ai`
- missing/issue: `pack:checklist`
- missing/issue: `pack:procedure`
- missing/issue: `pack:strategy`

### `BAI/AEGIS/RT` — FAIL (28.5)
- missing/issue: `.hath0r/`
- missing/issue: `KB stub`
- missing/issue: `cfg/product.yaml`
- missing/issue: `contracts/`
- missing/issue: `bootstrap`
- missing/issue: `MANIFEST.json`
- missing/issue: `runbook`
- missing/issue: `docs/llms.txt`
- missing/issue: `legacy roots: .ai, .infraOS, .infraos`
- missing/issue: `pack:checklist`
- missing/issue: `pack:procedure`
- missing/issue: `pack:strategy`

### `BAI/AEGIS/UXP` — FAIL (32.5)
- missing/issue: `.hath0r/`
- missing/issue: `KB stub`
- missing/issue: `cfg/product.yaml`
- missing/issue: `contracts/`
- missing/issue: `bootstrap`
- missing/issue: `MANIFEST.json`
- missing/issue: `runbook`
- missing/issue: `docs/llms.txt`
- missing/issue: `legacy roots: .ai, .infraOS, .infraos`
- missing/issue: `pack:procedure`
- missing/issue: `pack:strategy`

### `BAI/AEGIS/VS` — FAIL (21.5)
- missing/issue: `.hath0r/`
- missing/issue: `KB stub`
- missing/issue: `cfg/product.yaml`
- missing/issue: `contracts/`
- missing/issue: `bootstrap`
- missing/issue: `MANIFEST.json`
- missing/issue: `runbook`
- missing/issue: `docs/INDEX.md`
- missing/issue: `docs/llms.txt`
- missing/issue: `legacy roots: .ai, .infraOS, .infraos`
- missing/issue: `pack:report`
- missing/issue: `pack:checklist`

### `BAI/UXP` — PARTIAL (82.0)
- missing/issue: `docs/INDEX.md`
- missing/issue: `docs/llms.txt`
- missing/issue: `pack:report`
- missing/issue: `pack:checklist`
- missing/issue: `pack:procedure`
- missing/issue: `pack:strategy`

### `Websites/doctor-sleep` — NOT_INIT (0.0)
- missing/issue: `.hath0r/`
- missing/issue: `KB stub`
- missing/issue: `cfg/product.yaml`
- missing/issue: `cfg/suite.yaml`
- missing/issue: `cfg/knowledge-tower.yaml`
- missing/issue: `contracts/`
- missing/issue: `bootstrap`
- missing/issue: `MANIFEST.json`
- missing/issue: `runbook`
- missing/issue: `docs/INDEX.md`
- missing/issue: `docs/llms.txt`
- missing/issue: `AGENTS.md`

### `Websites/knithappens` — NOT_INIT (0.0)
- missing/issue: `.hath0r/`
- missing/issue: `KB stub`
- missing/issue: `cfg/product.yaml`
- missing/issue: `cfg/suite.yaml`
- missing/issue: `cfg/knowledge-tower.yaml`
- missing/issue: `contracts/`
- missing/issue: `bootstrap`
- missing/issue: `MANIFEST.json`
- missing/issue: `runbook`
- missing/issue: `docs/INDEX.md`
- missing/issue: `docs/llms.txt`
- missing/issue: `AGENTS.md`

### `1-Nation/site` — NOT_INIT (0.0)
- missing/issue: `.hath0r/`
- missing/issue: `KB stub`
- missing/issue: `cfg/product.yaml`
- missing/issue: `cfg/suite.yaml`
- missing/issue: `cfg/knowledge-tower.yaml`
- missing/issue: `contracts/`
- missing/issue: `bootstrap`
- missing/issue: `MANIFEST.json`
- missing/issue: `runbook`
- missing/issue: `docs/INDEX.md`
- missing/issue: `docs/llms.txt`
- missing/issue: `AGENTS.md`


## 9. Changelog
- **1.0.0 — 2026-09-19:** Initial multi-tree audit (24 targets).
