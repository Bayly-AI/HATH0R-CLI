# Troubleshooting Checklist

**Reference:** [Troubleshooting Strategy](../strategies/troubleshooting-strategy.md) | [Troubleshooting Playbook](../playbooks/playbook-troubleshooting.md)

- [ ] Issue is consistently reproducible (MRE established).
- [ ] Components (API, EDGE, DB, UI) were separated and tested independently to find the fault.
- [ ] Logs traced systematically (UI -> EDGE -> API -> DB).
- [ ] Fix validated in `testing` environment.
- [ ] Fix validated in `staging` environment.
- [ ] Root Cause Analysis (RCA) documented.
