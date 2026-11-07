# Playbook: CLI Update & Promotion Execution

> Step-by-step operational playbook for updating, verifying, and releasing changes to `hath0r`.

---

## Phase 1: Pre-Change Verification

1. Verify working branch was created from `development` targeting an active GitHub issue (`feature|bugfix|enhancement/<issue>-<slug>`).
2. Run preflight health check:
   ```sh
   hath0r doctor
   ```

---

## Phase 2: Autonomous Update Execution

Trigger the declarative update factory:

```sh
hath0r factory run update-cli-factory
```

Or execute dry-run preview:

```sh
hath0r factory run update-cli-factory --dry-run
```

---

## Phase 3: Post-Update Verification

1. Verify test suite passes completely:
   ```sh
   pytest -v
   ```
2. Validate release packaging:
   ```sh
   hath0r release validate
   ```
3. Confirm MemoryGraph ingestion:
   ```sh
   hath0r memory read core_rules
   ```

---

## Phase 4: Promotion Ladder

Follow the canonical environment promotion path:

```text
local ──► development ──► testing ──► staging ──► master
```
