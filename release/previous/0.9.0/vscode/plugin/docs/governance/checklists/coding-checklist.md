# Coding Checklist

**Reference:** [Coding Strategy](../strategies/coding-strategy.md) | [Coding Playbook](../playbooks/playbook-coding.md)

- [ ] All strings are managed by a Safe wrapper and explicitly checked for null.
- [ ] All numbers and arrays are managed by Safe wrappers.
- [ ] Code adheres to SOA specifications and Dependency Injection.
- [ ] State updates (especially for UI) utilize immutability.
- [ ] All service/network connections are asynchronous (ASync).
- [ ] Error handling and fallbacks are implemented for async calls.
- [ ] SonarCloud Quality Gate is passing.
