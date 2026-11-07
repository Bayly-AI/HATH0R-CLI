# Git Worktree Concurrency Isolation Playbook

> Scope: **Developer & Operator Runbook for Isolated Agent Execution**  
> Rule Reference: **CR-CLI-ENTRY-001 / CR-BRANCH-GOV-001**  
> Issue: **#242**

---

## 1. Quick Start

### Creating an Isolated Worktree for Background Agent
```bash
hath0r branch worktree create --branch feature/242-test --task-id task-101
```

### Listing Active Agent Worktrees
```bash
hath0r branch worktree list
```

### Removing a Finished Agent Worktree
```bash
hath0r branch worktree remove task-101 --force
```

### Pruning Stale Worktree Records
```bash
hath0r branch worktree prune
```
