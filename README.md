# Markgitup Research Desk

Hourly source-led research portal. Each dispatch starts from one of 24 topic families, finds a new current angle with the local LLM, expands into adjacent search lenses, gathers evidence through SearXNG, and publishes a linked synthesis.

## Runtime

- Schedule: hourly (`0 * * * *`)
- LLM: OpenAI-compatible local endpoint at `192.168.0.219:8080/v1`
- Search: local SearXNG at `127.0.0.1:8888`
- Novelty ledger: `data/search-history.json`
- Topic cycle ledger: `data/topic-cycle.json` (random permutation of all 24 topic families, then reset)
- Exact-query cooldown: 3 days (configurable with `MARKGITUP_SEARCH_COOLDOWN_DAYS`)
- Output: GitHub Pages via `main`
