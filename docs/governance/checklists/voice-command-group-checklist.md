# Checklist: HATH0R CLI Voice Command Verification

> Document Type: **Checklist** (`cr-workflow-doc-001`)  
> Product: **HATH0R-CLI** · Issue: #131 · SemVer: `minor`

- [ ] `hath0r voice --help` exposes `status`, `exec`, and `listen` subcommands
- [ ] `hath0r voice status` outputs audio device, STT, TTS, router, and trust tier information
- [ ] `hath0r voice exec` executes fast-path actions in sub-50ms
- [ ] Structured JSON responses conform to `hath0r.cli.response/1`
- [ ] Voice actions conform to `hath0r.voice.action/1`
- [ ] Trust tiers (guest, elevated, sovereign) enforced on voice commands
- [ ] Unit tests pass 100% in `tests/cli/test_voice.py`
- [ ] Zero secrets committed
