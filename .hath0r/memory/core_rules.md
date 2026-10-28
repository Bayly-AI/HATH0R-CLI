# Core Hath0r Rules
1. CLI-First: Always use the CLI capabilities before improvising.
2. Bots not Daemons: Background tasks are bots/factories.
3. Hyper-Context: Always traverse the defined context paths (playbooks, procedures).
4. Promotion Path: local -> development -> testing -> staging -> master.
6. Automatic Task Evaluation (CR-TASK-EVAL-001): Every task must execute and pass the 4-tier automatic task evaluation gate (hath0r evals run / hath0r evals verify, R_task >= 0.80) prior to announcing complete.
