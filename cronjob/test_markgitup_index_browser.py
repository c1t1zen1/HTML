#!/usr/bin/env python3
"""Real Chromium regressions for the generated portal (no network/LLM calls).

Run with Python providing websockets, and Chromium on PATH:
  python -m unittest discover -s scripts -p test_markgitup_index_browser.py -v
"""
import importlib.util
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone
from urllib.request import urlopen

from websockets.sync.client import connect

SCRIPT = Path(__file__).with_name("markgitup-html-cron.py")
SPEC = importlib.util.spec_from_file_location("markgitup_browser_publisher", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
PUBLISHER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = PUBLISHER
SPEC.loader.exec_module(PUBLISHER)


def articles(size=700):
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return [dict(article_number=i + 1, topic=f"Research dispatch {i + 1}: independent evidence and emerging technology",
                 file=f"html/article-{i + 1:04d}.html", summary="A source-linked briefing with findings, risks, and next steps.",
                 original_topic="Technology", tags=f"archive-marker-{i + 1:04d}", source_count=3,
                 full_timestamp=(start + timedelta(minutes=i)).isoformat()) for i in range(size)]


class BrowserHarness(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        executable = shutil.which("chromium") or shutil.which("chromium-browser")
        if not executable:
            raise RuntimeError("Chromium is required; browser coverage must not silently skip")
        cls.temp = tempfile.TemporaryDirectory(prefix="markgitup-browser-")
        cls.root = Path(cls.temp.name)
        cls.stderr = (cls.root / "chromium.log").open("w")
        cls.browser = subprocess.Popen([
            executable, "--headless", "--disable-gpu", "--no-first-run",
            "--disable-background-networking", "--disable-component-update",
            "--disable-extensions", "--remote-debugging-port=0",
            f"--user-data-dir={cls.root / 'profile'}", "about:blank",
        ], stdout=subprocess.DEVNULL, stderr=cls.stderr)
        try:
            portfile = cls.root / "profile" / "DevToolsActivePort"
            deadline = time.monotonic() + 15
            while not portfile.exists():
                if cls.browser.poll() is not None or time.monotonic() > deadline:
                    raise RuntimeError("Chromium did not start: " + (cls.root / "chromium.log").read_text()[-2000:])
                time.sleep(.05)
            cls.port = int(portfile.read_text().splitlines()[0])
            with urlopen(f"http://127.0.0.1:{cls.port}/json/list", timeout=10) as response:
                target = next(t for t in json.load(response) if t["type"] == "page")
            cls.socket = connect(target["webSocketDebuggerUrl"], open_timeout=10)
            cls.sequence = 0
        except BaseException:
            cls.browser.terminate()
            cls.browser.wait(timeout=10)
            cls.stderr.close()
            cls.temp.cleanup()
            raise

    @classmethod
    def tearDownClass(cls):
        # Ask Chromium to flush and close its children before deleting the profile.
        cls.sequence += 1
        cls.socket.send(json.dumps({'id': cls.sequence, 'method': 'Browser.close'}))
        try:
            cls.browser.wait(timeout=15)
        except subprocess.TimeoutExpired:
            cls.browser.terminate()
            cls.browser.wait(timeout=15)
        cls.socket.close()
        cls.stderr.close()
        cls.temp.cleanup()

    @classmethod
    def cdp(cls, method, **params):
        cls.sequence += 1
        request_id = cls.sequence
        cls.socket.send(json.dumps(dict(id=request_id, method=method, params=params)))
        while True:
            response = json.loads(cls.socket.recv(timeout=15))
            if response.get("id") == request_id:
                if "error" in response:
                    raise AssertionError(response["error"])
                return response.get("result", {})

    def evaluate(self, expression):
        result = self.cdp("Runtime.evaluate", expression=expression, returnByValue=True, awaitPromise=True)
        if "exceptionDetails" in result:
            self.fail(str(result["exceptionDetails"]))
        return result["result"].get("value")

    def settle(self):
        self.evaluate("new Promise(resolve => { let frames = 12; function tick() { if (--frames) requestAnimationFrame(tick); else resolve(true); } requestAnimationFrame(tick); })")

    def load(self, width=1280, height=900, records=None, setup=""):
        records = articles() if records is None else records
        content = PUBLISHER.render_index(records)
        content = content.replace("<script>", "<script>window.fetch=async()=>{throw new Error('Offline browser test')};" + setup + ";window.testErrors=[];window.addEventListener('error', e => testErrors.push(e.message));", 1)
        page = self.root / f"page-{time.monotonic_ns()}.html"
        page.write_text(content, encoding="utf-8")
        self.cdp("Emulation.setDeviceMetricsOverride", width=width, height=height, deviceScaleFactor=1, mobile=False)
        self.cdp("Page.navigate", url=page.as_uri())
        deadline = time.monotonic() + 10
        while not self.evaluate(f"location.href === {json.dumps(page.as_uri())} && document.readyState === 'complete'"):
            if time.monotonic() > deadline:
                self.fail("page did not finish loading")
            time.sleep(.05)
        self.settle()
        self.assertEqual([], self.evaluate("window.testErrors"))

    def metrics(self):
        return self.evaluate("""(() => {
            const grid = document.querySelector('#grid');
            const cards = [...grid.querySelectorAll('.card')];
            const style = getComputedStyle(grid);
            const columns = style.gridTemplateColumns.split(' ').length;
            const stride = cards.length ? Math.max(...cards.slice(-columns).map(c => c.getBoundingClientRect().height)) + parseFloat(style.rowGap) : 0;
            return {count: cards.length, columns, stride, viewport: innerHeight,
                lastTop: cards.length ? cards.at(-1).getBoundingClientRect().top : null,
                bottom: grid.getBoundingClientRect().bottom, scrollY,
                links: cards.map(c => c.querySelector('a').getAttribute('href'))};
        })()""")

    def search(self, query):
        self.evaluate(f"(() => {{ const input = document.querySelector('#search'); input.value = {json.dumps(query)}; input.dispatchEvent(new Event('input', {{bubbles:true}})); }})()")
        self.settle()


class PortalBrowserTests(BrowserHarness):
    def test_initial_render_is_bounded_to_viewport_and_two_extra_rows(self):
        self.load()
        metrics = self.metrics()
        self.assertGreater(metrics['count'], 0)
        limit = metrics['columns'] * (math.ceil(metrics['viewport'] / metrics['stride']) + 3)
        self.assertLessEqual(metrics['count'], limit, "initial render must not create the entire archive")
        self.assertEqual(1, self.evaluate("document.querySelectorAll('#featured .feature').length"))
        self.assertEqual("700 results", self.evaluate("document.querySelector('#status').textContent"))
        before = metrics['count']
        self.settle()
        self.assertEqual(before, self.metrics()['count'], "idle observer must not drain the archive")

    def search(self, query):
        self.evaluate(f"(() => {{ const input = document.querySelector('#search'); input.value = {json.dumps(query)}; input.dispatchEvent(new Event('input', {{bubbles:true}})); }})()")
        self.settle()

    def test_scroll_appends_without_duplicates_or_replacing_existing_cards(self):
        self.load()
        before = self.metrics()
        self.evaluate("window.firstCard = document.querySelector('#grid .card'); window.scrollTo(0, document.body.scrollHeight)")
        self.settle()
        after = self.metrics()
        self.assertGreater(after['count'], before['count'])
        self.assertLess(after['count'], 699)
        self.assertEqual(before['links'], after['links'][:before['count']])
        self.assertEqual(len(after['links']), len(set(after['links'])))
        self.assertTrue(self.evaluate("firstCard === document.querySelector('#grid .card')"))
        self.assertGreater(after['bottom'], after['viewport'] + after['stride'])
        self.assertLessEqual(after['lastTop'], after['viewport'] + after['stride'] * 3)
        self.settle()
        self.assertEqual(after['count'], self.metrics()['count'])

    def test_mobile_tall_viewport_and_resize_keep_progressive_loading(self):
        for width, height in [(390, 844), (768, 1024), (1920, 2400)]:
            with self.subTest(width=width, height=height):
                self.load(width=width, height=height)
                initial = self.metrics()
                self.assertLess(initial['count'], 40)
                self.assertEqual(1 if width == 390 else 2 if width == 768 else 3, initial['columns'])
                self.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                self.settle()
                after = self.metrics()
                self.assertGreater(after['count'], initial['count'])
                self.assertGreater(after['bottom'], after['viewport'] + after['stride'])
                self.cdp('Emulation.setDeviceMetricsOverride', width=1280, height=1600, deviceScaleFactor=1, mobile=False)
                self.settle()
                self.assertEqual(3, self.metrics()['columns'])
                self.assertLess(self.metrics()['count'], 80)

    def test_search_covers_unrendered_archive_and_resets_pending_scroll(self):
        self.load()
        self.assertNotIn('html/article-0001.html', self.metrics()['links'])
        self.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        self.search('archive-marker-0001')
        self.assertEqual(['html/article-0001.html'], self.metrics()['links'])
        self.assertEqual('1 result', self.evaluate("document.querySelector('#status').textContent"))
        self.assertTrue(self.evaluate("document.querySelector('#load-more').hidden"))
        self.search('not-present-anywhere')
        self.assertEqual(0, self.metrics()['count'])
        self.assertEqual('No dispatches match that filter yet.', self.evaluate("document.querySelector('.empty').textContent"))
        self.search('Technology')
        self.assertEqual('700 results', self.evaluate("document.querySelector('#status').textContent"))
        self.assertLess(self.metrics()['count'], 30)
        self.search('')
        self.assertEqual('html/article-0699.html', self.metrics()['links'][0])
        self.assertEqual(1, self.evaluate("document.querySelectorAll('#featured .feature').length"))
        self.assertLess(self.metrics()['count'], 30)

    def test_no_observer_scroll_and_load_more_button_reach_end(self):
        self.load(records=articles(31), setup='delete window.IntersectionObserver')
        initial = self.metrics()['count']
        self.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        self.settle()
        self.assertGreater(self.metrics()['count'], initial)
        for _ in range(20):
            if self.evaluate("document.querySelector('#load-more').hidden"):
                break
            self.evaluate("document.querySelector('#load-more').click()")
            self.settle()
        self.assertEqual([f'html/article-{i:04d}.html' for i in range(30, 0, -1)], self.metrics()['links'])
        self.assertTrue(self.evaluate("document.querySelector('#load-more').hidden && document.querySelector('#scroll-sentinel').hidden"))
        self.assertEqual('Showing 31 of 31', self.evaluate("document.querySelector('#load-status').textContent"))

    def test_empty_single_and_partial_row_archives_finish_cleanly(self):
        for size in [0, 1, 2, 5]:
            with self.subTest(size=size):
                self.load(records=articles(size))
                self.assertEqual(max(0, size - 1), self.metrics()['count'])
                self.assertTrue(self.evaluate("document.querySelector('#load-more').hidden"))
                self.assertEqual(f'Showing {size} of {size}', self.evaluate("document.querySelector('#load-status').textContent"))

    def test_full_archive_scroll_has_every_publishable_link_once(self):
        records = articles(700)
        records += [dict(records[0], topic='Archived record', archived=True), dict(records[0], topic='Under sourced', source_count=1)]
        self.load(records=records)
        for _ in range(250):
            if self.metrics()['count'] == 699:
                break
            self.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            self.settle()
        self.assertEqual([f'html/article-{i:04d}.html' for i in range(699, 0, -1)], self.metrics()['links'])
        self.assertTrue(self.evaluate("document.querySelector('#load-more').hidden"))
        self.assertEqual('Showing 700 of 700', self.evaluate("document.querySelector('#load-status').textContent"))
        self.assertEqual([], self.evaluate('testErrors'))

    def test_keyboard_load_more_focuses_first_new_article(self):
        self.load()
        before = self.metrics()['count']
        self.evaluate("document.querySelector('#load-more').focus({preventScroll:true})")
        self.cdp('Page.bringToFront')
        self.cdp('Input.dispatchKeyEvent', type='keyDown', key='Enter', code='Enter', text='\r', unmodifiedText='\r', windowsVirtualKeyCode=13, nativeVirtualKeyCode=13)
        self.cdp('Input.dispatchKeyEvent', type='keyUp', key='Enter', code='Enter', windowsVirtualKeyCode=13)
        self.settle()
        self.assertEqual(f'html/article-{699 - before:04d}.html', self.evaluate("document.activeElement.getAttribute('href')"))

    def test_disabled_theme_storage_does_not_break_lazy_rendering(self):
        self.load(setup="Object.defineProperty(window, 'localStorage', {get() { throw new DOMException('Disabled', 'SecurityError'); }})")
        self.assertGreater(self.metrics()['count'], 0)
        self.assertLess(self.metrics()['count'], 30)
        self.evaluate("document.querySelector('#theme').click()")
        self.assertEqual('light', self.evaluate('document.body.dataset.theme'))
        self.assertEqual([], self.evaluate('testErrors'))


if __name__ == '__main__':
    unittest.main()
