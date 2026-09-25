# Strategy: Repository Hygiene & Cleanliness Factory (repo-clean-factory)

> Factory ID: **`repo-clean-factory`**  
> Status: **Canonical Specification**  
> Issue: #135 · SemVer: `minor`  
> Updated: 2026-09-25

---

## 1. Executive Summary

As repositories scale under multi-agent autonomous engineering, errant artifacts, temporary dumps, misplaced configuration files, and monolithic knowledge documents frequently pollute the project root and subdirectories.

The **`repo-clean-factory`** provides continuous automated repo maintenance and structure governance for Hath0r repositories:
1. **Root Hygiene**: Strictly validates allowable root files per Universal Project Layout (UPL) specifications, flagging or archiving errant files, dumps, and unapproved artifacts.
2. **Knowledge Organization**: Enforces modular knowledge architecture — disallowing large monolithic documents by requiring content to be modularized across designated folders (`rules/`, `knowledge/`, `plans/`, `procedures/`, `runbooks/`, `playbooks/`, `checklists/`).
3. **Config Organization**: Identifies configuration files that do not strictly require root placement (e.g. non-toolchain configs) and relocates or verifies them in dedicated `.cfg/` or `cfg/` directories.

---

## 2. Goals & Non-Goals

### Goals
- Keep project root clean and free of rogue output, test artifacts, or stray documents.
- Require knowledge, agent definitions, and rules to be decomposed into modular files under organized topic directories instead of bloated single files.
- Organize auxiliary and non-root configuration files into `.cfg/` (or `cfg/`).
- Provide non-destructive audit mode (`audit-cleanliness`) and automated remediation (`organize-cleanliness`).
- Provide CLI commands (`hath0r repo clean`, `hath0r repo audit`).

### Non-Goals
- Deleting essential toolchain root files required by Python, Git, or CI (such as `pyproject.toml`, `Makefile`, `.gitignore`, `LICENSE`, `VERSION`, `README.md`, `AGENTS.md`).
- Replacing git version control or git-clean.
