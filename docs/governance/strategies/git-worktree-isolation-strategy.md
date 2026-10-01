# Git Worktree Concurrency Isolation Strategy

> Scope: **Hath0r CLI Workspace & Concurrent Subagent Isolation Subsystem**  
> Rule Reference: **CR-CLI-ENTRY-001 / CR-BRANCH-GOV-001**  
> Issue: **#242**

---

## 1. Executive Summary

When autonomous agents or background tasks perform extensive code refactoring, execute matrix builds, or run integration tests, operating directly within the developer's primary working tree causes file lock collisions, uncommitted diff corruption, and branch context churn.

Git Worktrees allow creating linked, lightweight, independent working directories checked out to different branches while sharing a single underlying `.git` object repository. This strategy details the automated lifecycle management of isolated worktrees under `.hath0r/worktrees/`.

---

## 2. Architecture & Lifecycle

```
                     ┌─────────────────────────────────────────┐
                     │          Primary Repository Root        │
                     │          (/path/to/project)             │
                     │                 .git/                   │
                     └────────────────────┬────────────────────┘
                                          │
                  ┌───────────────────────┴───────────────────────┐
                  │                                               │
                  ▼                                               ▼
   ┌─────────────────────────────┐                 ┌─────────────────────────────┐
   │    Active Developer Tree    │                 │   .hath0r/worktrees/task-1  │
   │  (branch: development)      │                 │   (branch: feature/242)     │
   │  Zero interruption          │                 │   Isolated Agent Sandbox    │
   └─────────────────────────────┘                 └─────────────────────────────┘
```

---

## 3. CLI Interfaces

- `hath0r branch worktree create --branch <branch-name> [--task-id <id>]`
- `hath0r branch worktree list`
- `hath0r branch worktree remove <worktree-path-or-id> [--force]`
- `hath0r branch worktree prune`
