# Procedure: Voice Conversational Interface (`voice-converse-factory`)

## Overview
This procedure details how the `voice-converse-factory` executes interactive voice sessions, manages multi-turn dialogue, routes fast-path commands, and triggers proactive agent speech.

## Factory Workflows
1. **`converse-session`**: Continuous meeting/dialogue loop (Listen $\to$ Reason $\to$ Speak $\to$ Listen).
2. **`listen-and-respond`**: Single or multi-turn conversational exchange with automatic speech synthesis.
3. **`proactive-announcement`**: Autonomous verbal notification when background tasks finish or require human intervention.
4. **`meeting-mode`**: Ambient standup/meeting participant mode with wake detection and proactive check-ins.

## Execution Matrix
- **CLI Command**: `hath0r voice converse`
- **Meeting Command**: `hath0r voice meeting`
- **Workflow Command**: `hath0r workflow run voice-converse-factory <workflow-id>`
- **Trust Tier Enforcement**: Default elevated tier allows CLI execution and agent delegation; guest tier restricts muting and status.
