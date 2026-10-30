# Bot Spec: `BITEVerifierBot`, `SecretPIISanitizerBot`, `DependencyGuardBot` & `ShadowAIClassifierBot`

## 1. `BITEVerifierBot` (`src/hath0r_cli/bots/bite_verifier_bot.py`)
- Evaluates `SKILL.md`, `AGENTS.md`, `WARP.md`, and MCP configs against the 3 BITE questions (`is_reachable`, `is_unnecessary`, `is_concealed`).
- Persists `.hath0r/security/bite_manifest.json`.

## 2. `SecretPIISanitizerBot` (`src/hath0r_cli/bots/secret_pii_sanitizer.py`)
- Deterministic L2 pre-persist redaction of AWS keys, GitHub tokens, Anthropic/OpenAI keys, Slack tokens, JWTs, private keys, SSNs, and emails across `MemoryManagerBot`, `HAHPProtocolManager`, and `TokenTelemetryCLIBot`.

## 3. `DependencyGuardBot` (`src/hath0r_cli/bots/dependency_guard_bot.py`)
- Scans `requirements.txt` and `pyproject.toml` for slopsquatted / hallucinated packages and checks `AGENTS.md` / `WARP.md` against `.hath0r/memory/hashes.json`.

## 4. `ShadowAIClassifierBot` (`src/hath0r_cli/bots/shadow_ai_classifier.py`)
- Computes a 0-100 AgentSonar score on Git commits (`AUTONOMOUS_AGENT`, `AI_ASSISTED_HYBRID`, `HUMAN_AUTHORED`).
