# Troubleshooting Playbook

> **Note:** This playbook must be read and followed anytime we are going to fix a bug.

## 1. Reproducing the Error First
Before diving into the code, establish a minimal reproducible example (MRE). If a bug cannot be consistently reproduced, it cannot be reliably fixed. Document the exact state and inputs required to trigger the issue.

## 2. Separate Concerns
When diagnosing an issue in our UI or multi-part applications, you must separate your application into distinct components. Isolate and identify:

- **API**
- **EDGE Server**
- **Database Server**
- **UI Server / Site**

**Action:** Test each of these components independently to ascertain exactly where the problem exists before proposing or implementing a fix. Do not assume the bug's location without verifying the individual component's behavior.

## 3. Log Analysis & Tracing
Trace the failing request systematically through the stack to find the disconnect:
1. Inspect the UI network tabs and console.
2. Check the EDGE server logs.
3. Review the API layer logs.
4. Analyze the Database queries.

## 4. Validating the Fix
All fixes must be validated through the canonical environment promotion path (`development` -> `testing` -> `staging` -> `master`). Validate the fix in an isolated environment before promoting it up the chain.

## 5. Root Cause Analysis (RCA)
Once the bug is fixed, document the root cause to understand *why* the bug occurred and to prevent similar issues in the future.
