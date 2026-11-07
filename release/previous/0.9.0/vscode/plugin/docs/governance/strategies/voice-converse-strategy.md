# Strategy: Voice Conversational Interface and Meeting Mode (`voice-converse-factory`)

## Purpose
The **Voice Conversational Interface Strategy** establishes a real-time, two-way conversational loop between operators and Hath0r agents. It enables hands-free meeting participation, proactive verbal notifications, and immediate System 1/System 2 voice-driven orchestration, managed directly by the operator CLI (`hath0r`) across any repository in the OpenSource Project.

## Principles
1. **CLI-First Global Orchestration**: The factory and workflows reside at the CLI control tower (`HATH0R-CLI`), making voice meeting capabilities available across any suite workspace (`--repo <path>` or local context).
2. **Turn-Taking & Continuous Meeting Mode**: Decouples one-shot recording from ongoing conversational sessions. The system listens, reasons, responds aloud, and can speak up proactively when background events occur.
3. **Dual-Tier System Architecture**:
   - **System 1 (Low-Latency FastPath)**: Sub-50ms deterministic command routing (e.g. `hath0r doctor`, `hath0r repo audit`, `open Safari`).
   - **System 2 (Conversational Dialogue Reasoning)**: Deliberate multi-turn agent assistance for complex questions, planning, and task execution.
4. **Proactive Agent Speech**: Agents participate like real team members, announcing test results, task completions, and requesting approvals aloud.
5. **Cross-Platform Resilience**: Native audio adapter on macOS (`say` / AVFoundation), Linux (`espeak` / `piper`), and graceful fallback for automated CI testing.
