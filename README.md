# Markgitup Research Desk

Hourly source-led research portal published from `main` to GitHub Pages. Each dispatch starts from one of 24 topic families, finds a sharper current angle, gathers evidence through local SearXNG, synthesizes a linked briefing, and records the result in `manifest.json`.

## Current runtime

- Repository: `c1t1zen1/HTML`
- Branch: `main`
- Schedule: hourly, cron expression `0 * * * *`
- Canonical publisher: `/home/pi/Documents/Hermes-Jetson/scripts/markgitup-html-cron.py`
- Scheduler launcher: `/home/pi/.hermes/scripts/markgitup-html-cron.py`
- Local model discovery: OpenAI-compatible `/v1/models` endpoint
- Search: local SearXNG at `127.0.0.1:8888`
- Fallback: GPT 5.6 Codex Luna through Hermes `openai-codex`
- Failure policy: no article is written when inference and fallback both fail
- Output: `index.html`, `manifest.json`, `favicon.svg`, and `html/*.html`

## Source and archive policy

Edit the canonical Hermes-Jetson script first. `cronjob/markgitup-html-cron.py` is a versioned archive copy and must stay byte-identical to the canonical script before portal publication. The launcher, not the archive copy, is the scheduler runtime path.

Do not put credentials in URLs, prompts, article content, logs, or commits. Runtime search/topic state is scheduler-owned and may change between runs; inspect Git status before manual publication.

## Checks

From Hermes-Jetson:

```bash
python3 -m unittest scripts.test_markgitup_html_cron -v
python3 -m py_compile scripts/markgitup-html-cron.py scripts/test_markgitup_html_cron.py
```

Before publishing, verify manifest references, HTML count, favicon links, source/archive parity, and `git diff --check`. GitHub Pages publication is separate from the local generator test suite.
