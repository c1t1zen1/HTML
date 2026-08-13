# Markgitup Research Desk

Hourly source-led research portal. Each dispatch starts from one of 24 topic families, finds a new current angle, gathers evidence through SearXNG, and publishes a linked synthesis.

## Runtime

- Schedule: hourly (`0 * * * *`)
- Local model: discovered dynamically from `/v1/models` at `192.168.0.219:8080/v1`
- Local inference budget: one attempt, 30 minutes
- Fallback LLM: GPT 5.6 Codex Luna through Hermes `openai-codex`
- Failure policy: no post is written when both inference paths fail
- Search: local SearXNG at `127.0.0.1:8888`
- Output: GitHub Pages via `main`
