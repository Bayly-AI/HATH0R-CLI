# Kokoro-82M Local Neural TTS Engine Playbook

> Scope: **Developer & Operator Runbook for Kokoro-82M Local Voice Synthesis**  
> Rule Reference: **CR-CLI-ENTRY-001**  
> Issue: **#237**

---

## 1. Quick Start

### Speaking with Kokoro Neural Voice
```bash
hath0r voice speak --engine kokoro --voice af_heart "Hath0r CLI v0.4.0 ready."
```

### Listing Available Voices
```bash
hath0r voice list-voices
```

### Starting Voice Daemon with Kokoro Backend
```bash
hath0r voice service start --engine kokoro
```

---

## 2. Voice Profiles

| Voice ID | Accent / Gender | Description |
| :--- | :--- | :--- |
| `af_heart` | American Female | Soft, warm, natural conversational style. |
| `am_adam` | American Male | Deep, clear technical narrator. |
| `bf_emma` | British Female | Articulate, precise status announcer. |
| `bm_george` | British Male | Formal, resonant assistant. |
