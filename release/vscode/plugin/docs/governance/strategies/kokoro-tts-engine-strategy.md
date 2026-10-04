# Kokoro-82M Local Neural TTS Engine Strategy

> Scope: **Hath0r CLI Voice Subsystem & Offline Audio Synthesis**  
> Rule Reference: **CR-CLI-ENTRY-001 / CR-SUBSTRATE-001**  
> Issue: **#237**

---

## 1. Executive Summary

Voice feedback in terminal agents improves situational awareness, hands-free debugging, and multithreaded task monitoring. However, relying on external cloud TTS introduces latency ($>500\text{ms}$ TTFT), API costs, and network vulnerabilities. Meanwhile, primitive OS fallback voices (e.g. legacy macOS `say`) sound robotic and lack emotional inflection.

`hexgrad/Kokoro-82M` is an open-weight, Apache 2.0-licensed neural text-to-speech model with only 82 million parameters that produces human-grade prosody with $<50\text{ms}$ latency. This strategy establishes a native Kokoro-82M synthesizer runtime within `hath0r_cli`.

---

## 2. Architecture & Design

```
                  ┌─────────────────────────────────┐
                  │       Agent Notification        │
                  │ (Text / Telemetry Alert Event)  │
                  └────────────────┬────────────────┘
                                   │
                                   ▼
                  ┌─────────────────────────────────┐
                  │      filter_speech_text()       │
                  │   (Strip Code/Markdown/Diffs)   │
                  └────────────────┬────────────────┘
                                   │
                                   ▼
                  ┌─────────────────────────────────┐
                  │         KokoroTTSEngine         │
                  │    (ONNX / PyTorch Vocoder)     │
                  │    Voices: af_heart, am_adam    │
                  └────────────────┬────────────────┘
                                   │
                                   ▼
                  ┌─────────────────────────────────┐
                  │       Local Audio Output        │
                  │   (PCM Stream / WAV Player)     │
                  └─────────────────────────────────┘
```

1. **Model Loader & Device Placement**:
   - Detects CPU, Metal (MPS), or CUDA hardware backends.
   - Loads ONNX / PyTorch weights from cache or fallback mock synthesizers.
2. **Preset Voice Profiles**:
   - `af_heart`: Friendly default voice.
   - `am_adam`: Deep authoritative technical narrator.
   - `bf_emma`: British articulate speaker.
3. **Graceful Fallback**:
   - If model files are not yet downloaded, dynamically synthesizes with system voice while providing automated one-click download hooks.

---

## 3. CLI Interfaces

- `hath0r voice speak --engine kokoro --voice af_heart "Build succeeded"`
- `hath0r voice list-voices`: Lists available Kokoro and system voices.
- `hath0r voice service start --engine kokoro`: Starts daemon with neural TTS backend.
