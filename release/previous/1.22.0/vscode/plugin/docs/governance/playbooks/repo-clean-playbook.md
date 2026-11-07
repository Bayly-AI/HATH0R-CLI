# Playbook: Repository Cleanliness & Structure Maintenance

> Document Type: **Playbook** (`cr-workflow-doc-001`)  
> Product: **HATH0R-CLI** · Issue: #135 · SemVer: `minor`

## 1. Decision Matrix for Errant Files

When an unwhitelisted file is discovered at repository root:
1. **Check if toolchain-mandated**: Certain files (e.g. `pyproject.toml`, `.gitignore`, `Makefile`) MUST remain at root. If a new official root tool is added, add it to the whitelist in `repo_clean.py`.
2. **Configuration file**: If it is a config (`.yaml`, `.json`, `.toml`, `.ini`, `.conf`) not strictly required at root by external tools, relocate to `.cfg/` or `cfg/`.
3. **Knowledge or Documentation file**: If markdown or text, evaluate size. If monolithic (>300 lines or covering multiple topics), partition into topic files within categorized folders (`docs/` or `knowledgebase/` subdirectories).
4. **Temporary / Cache / Scratch**: Files matching patterns like `*.tmp`, `*.dump`, `temp_*`, `scratch*` should be deleted or relocated to `.hath0r/spool/`.

## 2. Monolithic Knowledge Decomposition

When a file in `knowledgebase` or `rules` exceeds threshold size (e.g., >300 lines or >15KB) or contains multiple disparate topics:
- Split into discrete atomic files under relevant category folders:
  - `rules/<topic>-rule.md`
  - `knowledge/<topic>.md`
  - `agents/<agent-id>.md`
- Maintain an `INDEX.md` in that folder referencing the split documents.
