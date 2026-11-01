# Troubleshooting Runbook

**Reference:** [Troubleshooting Strategy](../strategies/troubleshooting-strategy.md) | [Troubleshooting Playbook](../playbooks/playbook-troubleshooting.md)

## Execution
1. **Verify Environment:** Ensure your local environment is running the latest `development` branch.
2. **Reproduce Issue:** Feed the known bad state into the application.
3. **Trace Logs:** 
   - Check UI console / Network tab.
   - Tail EDGE logs (`hath0r docker diagnose <edge_container>`).
   - Tail API logs (`hath0r docker diagnose <api_container>`).
4. **Implement Fix:** Write code to resolve the isolated issue.
5. **Promote:** Push to a branch, create a PR to `development`, and follow standard release paths.
