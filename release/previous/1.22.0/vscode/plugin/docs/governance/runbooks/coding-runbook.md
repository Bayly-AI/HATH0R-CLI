# Coding Runbook

**Reference:** [Coding Strategy](../strategies/coding-strategy.md) | [Coding Playbook](../playbooks/playbook-coding.md)

## Execution
1. **State Management:**
   - Instantiate strings via `SafeString` class.
   - Instantiate arrays via `SafeArray` class.
   - Check state using `.isNull()` or equivalent methods instead of relying on implicit existence.
2. **Network Calls:**
   - Always utilize `async`/`await` or Promises for network requests.
   - Implement error boundaries and fallbacks for failed network calls.
3. **Architecture:**
   - Inject dependencies through constructors or established DI frameworks rather than hardcoding references.
