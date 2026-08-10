# Markgitup CronJob Archive

Versioned copy of the Markgitup HTML research cronjob and its tests.

## Runtime source

- Canonical development script: `/home/pi/Documents/Hermes-Jetson/scripts/markgitup-html-cron.py`
- Scheduler launcher: `/home/pi/.hermes/scripts/markgitup-html-cron.py`
- Schedule: hourly, `0 * * * *`
- Portal state: `../data/search-history.json` and `../data/topic-cycle.json`
- Target branch: `main`

The scheduler executes the canonical development script through the launcher. This folder is the GitHub versioned archive. Edit the canonical development script first, run tests, then refresh this archive before publishing.

## Checks

Run from the Hermes-Jetson repository:

```bash
python3 -m unittest scripts.test_markgitup_html_cron -v
python3 -m py_compile scripts/markgitup-html-cron.py scripts/test_markgitup_html_cron.py
```

## Restore

Do not execute an archived script blindly. Inspect the archive, copy the desired version to the canonical development path, run the checks above, then let the scheduler use the launcher.
