# Markgitup Research Desk

Hourly source-led research portal. Each dispatch starts from one of 24 topic families, finds a new current angle, gathers evidence through SearXNG, and publishes a linked synthesis.

## Runtime

- Schedule: hourly (`0 * * * *`)
- Local model: discovered dynamically from `/v1/models` at `192.168.0.219:8080/v1`
- Local inference: DeepSeek V4 uses native thinking-disabled streaming; other models retain the legacy payload; each response waits up to 20 minutes
- Local status: `/home/pi/.hermes/cron/markgitup-local-inference-status.json`
- Fallback LLM: GPT 5.6 Luna through Hermes `openai-codex`
- Failure policy: no post is written when both inference paths fail
- Search: local SearXNG at `127.0.0.1:8888`
- Source gate: publish only after at least 2 sources; low-source searches select another unused topic family (up to 6 attempts)
- Output: GitHub Pages via `main`
