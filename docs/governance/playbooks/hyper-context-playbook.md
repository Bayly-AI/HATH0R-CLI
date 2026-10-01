# Hyper Context Playbook

**Reference:** [Hyper Context Strategy](../strategies/hyper-context-strategy.md)

## When to Use This Playbook
Use this playbook whenever you are adding a new feature, a major sub-folder, or a complex system that requires its own rules, coding standards, or operational context that do not apply to the rest of the project.

## Execution
1. **Identify Boundary:** Determine the root directory of the new feature.
2. **Spread Context:** Use the `hath0r context spread` command to generate the localized `AGENTS.md`, `rules.md`, and `canonical.md` templates in the target directory.
3. **Link from Root:** Update the project root's `AGENTS.md` to reference the newly created localized rule files, acting as a pointer for future agents.
4. **Refine Context:** Edit the localized files to contain *only* the rules specific to that feature boundary.
