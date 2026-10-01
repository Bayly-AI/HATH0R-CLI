# Hyper Context Procedure

**Reference:** [Hyper Context Strategy](../strategies/hyper-context-strategy.md)

## Steps to Scaffold Hyper Context
1. **Determine Target Directory:** Identify the folder where localized rules should live.
2. **Execute Spread Bot:** Run the factory or the `hath0r context spread` CLI command targeting the directory.
3. **Verify Creation:** Ensure `AGENTS.md`, `rules.md`, and `canonical.md` exist in the target directory.
4. **Document Links:** Add the relative path to these files in the root `AGENTS.md` index section.
5. **Add Localized Rules:** Populate the localized files with the specific constraints (e.g., "This module only uses React, no Vue" or "This module must use SQLAlchemy").
