# Markgitup Research Desk

Hourly source-led research portal. Each dispatch starts from one of 24 topic families, finds a new current angle with the local LLM, gathers evidence through SearXNG, and publishes a linked synthesis.

## Runtime

- Schedule: hourly (`0 * * * *`)
- LLM: OpenAI-compatible local endpoint at `192.168.0.219:8080/v1`
- Search: local SearXNG at `127.0.0.1:8888`
- Output: GitHub Pages via `main`
