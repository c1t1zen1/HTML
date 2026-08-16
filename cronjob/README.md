# Markgitup CronJob Archive

Versioned archive of the Markgitup publisher and its regression tests. This directory is not the scheduler's canonical runtime source.

## Runtime source

- Canonical development script: `/home/pi/Documents/Hermes-Jetson/scripts/markgitup-html-cron.py`
- Scheduler launcher: `/home/pi/.hermes/scripts/markgitup-html-cron.py`
- Schedule: hourly, `0 * * * *`
- Portal state: `../data/search-history.json` and `../data/topic-cycle.json`
- Target branch: `main`

`markgitup-html-cron.py` in this archive must be byte-identical to the canonical development script. Edit the canonical file first, run tests, synchronize this archive, then publish the portal repository. Do not edit or execute the archived copy as the scheduler path.

## Checks

Run from Hermes-Jetson:

```bash
cmp /home/pi/Documents/Hermes-Jetson/scripts/markgitup-html-cron.py \
    /home/pi/Documents/HTML-Portal/cronjob/markgitup-html-cron.py
python3 -m unittest scripts.test_markgitup_html_cron -v
python3 -m py_compile scripts/markgitup-html-cron.py scripts/test_markgitup_html_cron.py
```

## Restore

Do not execute an archived script blindly. Inspect the archive, copy the desired version to the canonical development path, run the checks above, synchronize the archive, and let the scheduler use the launcher.
