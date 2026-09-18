# Markgitup CronJob Archive

Versioned archive of the Markgitup publisher and its regression tests. This directory is not the scheduler's canonical runtime source.

## Runtime source

- Canonical development script: `/home/pi/Documents/Hermes-Jetson/scripts/markgitup-html-cron.py`
- Scheduler launcher: `/home/pi/.hermes/scripts/markgitup-html-cron.py`
- Schedule: hourly, `0 * * * *`
- Portal state: `../data/search-history.json` and `../data/topic-cycle.json`
- Target branch: `main`
- Portal `README.md`: hand-maintained. The publisher no longer generates it, so documentation edits survive hourly runs.
- Source retrieval: SearXNG is primary; Bing News RSS supplies direct publisher links when local metasearch engines return no results.
- Source policy: a zero-source or recent-query angle selects another topic; the default run considers all 24 topic families before aborting.

`markgitup-html-cron.py` in this archive must be byte-identical to the canonical development script. Edit the canonical file first, run tests, synchronize this archive, then publish the portal repository. Do not edit or execute the archived copy as the scheduler path.

## Checks

Run from Hermes-Jetson:

```bash
cmp /home/pi/Documents/Hermes-Jetson/scripts/markgitup-html-cron.py \
    /home/pi/Documents/HTML-Portal/cronjob/markgitup-html-cron.py
node --test scripts/markgitup-weather/test-*.cjs
/home/pi/.hermes/hermes-agent/venv/bin/python -m unittest \
    scripts.test_markgitup_html_cron \
    scripts.test_markgitup_index_browser \
    scripts.test_markgitup_weather_browser -v
python3 -m py_compile scripts/markgitup-html-cron.py \
    scripts/test_markgitup_html_cron.py \
    scripts/test_markgitup_index_browser.py \
    scripts/test_markgitup_weather_browser.py
```

## Local weather hero

The landing-page hero resolves approximate IP-region coordinates in the visitor's browser through GeoJS, rounds them to 0.1 degrees, then requests Open-Meteo current conditions. It makes no GPS request and does not persist visitor location, weather, identifiers, cookies, or storage. Failed or stale provider data leaves a neutral, usable fallback.

The generated index bundles `cronjob/markgitup-weather/`: vendored Astronomy Engine, weather transport, deterministic sky painting, CSS, lunar texture, licenses, and Node regression tests. The model uses calculated Sun/Moon arcs, lunar illumination, WMO weather effects, bounded rain/snow particles, and reduced-motion/offscreen guards. The artwork is decorative rather than a compass-accurate sky projection. The visible privacy disclosure links GeoJS, Open-Meteo, NASA lunar-texture attribution, and Astronomy Engine.

The full design and validation contract is documented in `Hermes-Jetson/docs/notes/markgitup-local-weather-hero.md`.

## Progressive index loading

The generated index mounts the featured article and only enough grid cards to fill the viewport plus approximately two measured rows ahead. Scrolling appends rows without rebuilding existing cards. The full compact card/search metadata array remains embedded so search includes unmounted articles; article pages load only when opened. Already visited cards stay mounted. This is progressive DOM rendering, not network pagination or full virtualization.

The responsive row size follows actual CSS columns and measured card heights. An IntersectionObserver sentinel, passive scroll fallback, manual **Load more articles** button, and live loaded-count status handle continued browsing and exhaustion. Keyboard loading focuses the first appended article. Storage-disabled browsers still render normally. Archived/under-sourced filtering, newest-first order, and card text escaping remain unchanged.

`test_markgitup_index_browser.py` uses a synthetic 700-record fixture and real headless Chromium. It covers desktop/mobile/tall screens, scrolling, resize, search over unmounted records, no matches, archive exhaustion without duplicates, no-observer fallback, keyboard loading, and disabled theme storage. Browser tests require Chromium on PATH and Python with the `websockets` package; they never call search or inference APIs.

Run archive tests from this directory using the existing Hermes Python environment:

```bash
/home/pi/.hermes/hermes-agent/venv/bin/python -m unittest \
    test_markgitup_html_cron test_markgitup_index_browser -v
```

To regenerate only the index, import the canonical publisher and call `render_index()` with the existing manifest. Do not run the publisher's `main()` to refresh the index: that performs research and creates a new article. Wait for an in-flight cron run to finish, re-check remote ancestry and manifest stability, and stage only the intended portal files. Do not include unrelated runtime ledger changes.

## Restore

Do not execute an archived script blindly. Inspect the archive, copy the desired version to the canonical development path, run the checks above, synchronize the archive, and let the scheduler use the launcher.
