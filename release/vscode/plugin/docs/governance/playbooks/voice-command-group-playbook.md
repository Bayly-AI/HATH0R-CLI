# Playbook: HATH0R CLI Voice Command Troubleshooting

> Document Type: **Playbook** (`cr-workflow-doc-001`)  
> Product: **HATH0R-CLI** · Issue: #131 · SemVer: `minor`

## 1. Scenario: Action Blocked with VOICE_GOVERNANCE_BLOCKED

When `hath0r voice exec` returns exit code 1 and state `degraded`:
1. Check the `trust_tier` in the response envelope.
2. In `guest` tier, only read-only commands (`hath0r doctor`, `hath0r version`, `hath0r status`, `hath0r voice status`) and system control tokens are permitted.
3. For computer-use actions (`open <App>`), supply `--trust-tier=elevated` or elevate the operator session.

## 2. Scenario: STT or TTS Degraded Status

When `hath0r voice status` shows `tts: degraded`:
1. macOS: Verify `/usr/bin/say` exists.
2. Linux: Check if `espeak-ng` or `piper` is installed on PATH.
3. In headless/container environments, synthesis degradation is expected and non-fatal.
