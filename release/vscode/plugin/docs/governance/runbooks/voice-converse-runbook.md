# Runbook: Voice Conversational Interface (`voice-converse-factory`)

## Diagnostics & Troubleshooting

1. **Verify Voice Subsystem**:
   ```bash
   hath0r voice status
   ```
   Check that TTS Engine is `ready` (`native_say` on macOS) and STT is `ready`.

2. **Test Speech Output**:
   ```bash
   hath0r voice speak "Audio subsystem verified operational."
   ```

3. **Verify Factory Registration**:
   ```bash
   hath0r factory list
   hath0r factory inspect voice-converse-factory
   ```

4. **Run Unit Tests**:
   ```bash
   uv run pytest tests/unit/test_voice_converse.py -v
   ```
