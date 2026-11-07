---
id: HATHOR-GUIDE-046
title: "HATH0R CLI and POC Integration Troubleshooting"
summary: "Diagnostic steps for CLI installation, Tower orientation, KB/catalog access, POC mediation, and planned machine-output failures."
doc_type: GUIDE
diataxis: how-to
audience: [developer, operator, agent]
tags: [troubleshooting, cli, poc, knowledgebase, diagnostics]
version: 0.1.0
status: draft
created: 2026-09-16
updated: 2026-09-16
owner: "Raymond Bayly (BaylyAI)"
review:
  trust: unverified
  reviewed_by: null
  reviewed_at: null
  interval: 180d
  next_review: null
stale: false
supersedes: []
superseded_by: null
amended_by: []
parent: HATHOR-CANON-014
sources:
  - HATHOR-GUIDE-041
  - HATHOR-GUIDE-042
  - HATHOR-GUIDE-043
  - HATHOR-TS-005
  - "../README.md"
  - "../src/hath0r_cli/cli.py"
  - "../cfg/control-tower.yaml"
---
# HATH0R CLI and POC Integration Troubleshooting

## 1. Start with current commands

Run in order:

```sh
hath0r --version
hath0r doctor
hath0r kb path
hath0r kb products
```

Stop at the first failure. Do not substitute design-stage commands.

## 2. `hath0r` not found

Install the sibling CLI into the active Python environment:

```sh
python3 -m pip install -e ../HATH0R-CLI
hath0r --version
```

If the POC server still cannot find it, confirm the server process receives the
trusted scripts directory in its minimal `PATH`. Do not accept an executable
path from HTTP input and do not add a shell fallback.

## 3. Wrong CLI version

```sh
hath0r --version
python3 -m pip show hath0r-cli
```

Confirm the executable and package belong to the same active environment.
Compare versions with SemVer logic. Update fixtures only from the intended
release.

## 4. `hath0r doctor` fails

Doctor identifies failed checks in its table and exits `1`.

Verify:

1. the OpenSource group root exists;
2. group `AGENTS.md` and `WARP.md` exist;
3. Framework, CLI, and POC siblings exist;
4. this repository contains the four Tower config files;
5. member Tower pointers identify HATH0R-CLI;
6. the canonical KB directory exists; and
7. the suite product catalog references the control tower.

Use the exit code as overall authority. Do not scrape the table into a stable
machine model.

## 5. Wrong group root

For a trusted local clone location:

```sh
export HATH0R_GROUP_ROOT="/path/to/OpenSource"
hath0r doctor
```

Do not commit a user-specific override or accept it from the browser.

## 6. KB path command prints a path and then fails

This is expected v0.1 behavior when the resolved path does not exist:
`hath0r kb path` writes the path before checking the directory.

Remediation:

1. ignore stdout because the process failed;
2. verify `HATH0R_GROUP_ROOT`;
3. verify any `HATH0R_KB_PATH` override;
4. restore the canonical group KB through an authorized change; and
5. rerun doctor and KB path.

Do not create a second canonical KB inside the CLI or POC repository.

## 7. Product catalog missing

Confirm the canonical KB contains:

```text
catalogs/suite-products.yaml
```

Repair the group hub/catalog through an authorized control-tower change.
Do not copy an authoritative replacement into the POC.

## 8. Product catalog parser fails

The current command emits YAML/text.

1. retain only bounded redacted output for diagnosis;
2. mark the adapter result invalid/degraded;
3. update parser fixtures from verified CLI output;
4. validate normalized fields;
5. reject unsafe YAML types; and
6. never return an empty list for a parse failure.

Prefer implementing HATHOR-TS-005 over expanding screen scraping.

## 9. `--output json` is rejected

HATH0R-CLI v0.1 does not implement structured output. HATHOR-TS-005 is a
proposed contract.

Use the four current argv forms in the compatibility adapter. Do not claim
structured capability or silently pass unsupported flags. Move to JSON only
after the CLI source, tests, and release implement it.

## 10. Doctor works in a terminal but fails in the POC

Compare only approved process context:

- trusted executable resolution;
- minimal `PATH`;
- group-root and KB overrides;
- working directory;
- timeout/output caps; and
- process exit/termination class.

Never log the complete environment. Terminal formatting differences must not
alter the exit-based verdict.

## 11. Timeout or output limit

Confirm:

- the process is terminated;
- partial output is not parsed as success;
- response and logs remain bounded;
- audit metadata records timeout/output-limit distinctly;
- retry does not exceed the concurrency cap; and
- the UI remains usable with an error remediation.

Raise a limit only with measured evidence and review.

## 12. POC accepts arbitrary command input

Disable the affected route. The API must expose named read-only operations,
not argv.

Add negative tests for executable, command, flag, path, environment,
working-directory, and shell-metacharacter injection before re-enabling it.

## 13. Fixture data appears live

Treat this as a product defect. Every synthetic result must remain labeled
`fixture` through runner, API, cache, and UI. Never replace a live failure with
an unlabeled fixture.

## 14. Unsupported Framework capability

If a command is absent from `src/hath0r_cli/cli.py`:

- mark it planned or unavailable;
- do not emulate it in the POC;
- create an issue in the owning repository;
- define a versioned CLI contract;
- implement and test the CLI first; and
- activate the POC only after released fixtures exist.

## 15. Wrong Tower pointer

The control-tower path and remote must identify HATH0R-CLI consistently across
the Tower configuration, group catalog, Framework, and POC member pointers.

Fix every affected pointer in an issue-backed change, then rerun doctor. Do not
change one file merely to make one check green.

## 16. Forbidden metadata directory found

Only `.hath0r/` is valid Framework-created metadata in this OpenSource group.
Inventory any legacy directory, classify its contents, and migrate/remove it
under an authorized change. Do not add a compatibility writer.

## 17. Promotion check fails

Verify the path:

```text
issue-backed work branch → development
development → testing
testing → staging
staging → master
```

Feature work never targets testing, staging, or master directly.

## 18. Escalation bundle

Include:

- repository, branch, and authorizing issue;
- CLI version;
- operation key, not untrusted raw argv;
- redacted exit/termination class;
- expected and actual state;
- smallest reproduction;
- request ID when applicable;
- fixture/live source;
- relevant test result; and
- whether the failure is current text mode or proposed structured mode.

Exclude tokens, credential contents, complete environment dumps, real home
paths, and canonical KB record contents.
