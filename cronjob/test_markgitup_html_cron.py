#!/usr/bin/env python3
"""Regression tests for the Markgitup Luna-style renderer contract."""

import importlib.util
import json
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).with_name("markgitup-html-cron.py")
spec = importlib.util.spec_from_file_location("markgitup_html_cron", SCRIPT)
markgitup = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(markgitup)


class MarkgitupEditorialContractTests(unittest.TestCase):
    def test_portal_summary_is_short_and_does_not_dump_source_evidence(self):
        raw = (
            "This research synthesis explores local AI runtimes. Key findings from recent sources include: "
            "Ollama updates: a very long source snippet that should not appear on the portal; "
            "MLX benchmarks: another source snippet. The research aggregates insights from verified publications."
        )
        summary = markgitup.concise_portal_summary(raw, "Local AI runtimes reshape Mac workflows")
        self.assertLessEqual(len(summary), 240)
        self.assertLessEqual(len(summary.split()), 38)
        self.assertNotIn("Key findings from recent sources", summary)
        self.assertNotIn("Ollama updates", summary)
        self.assertLessEqual(summary.count("."), 3)

    def test_article_renderer_contains_canonical_luna_sections_and_no_php(self):
        angle = {"angle": "A focused live signal.", "tags": "AI, local inference"}
        results = [
            {
                "title": "Primary source",
                "content": "A concise source snippet.",
                "url": "https://example.com/report",
                "domain": "example.com",
                "published": "2026-08-08",
                "img_src": "",
            }
        ]
        article = {
            "dek": "A sharp, source-led briefing.",
            "overview": "Why this matters now.",
            "sections": [
                {"heading": "The live signal", "body": "Evidence-backed detail.", "bullets": ["One implication"], "sources": [1]},
                {"heading": "What changes next", "body": "A second field note.", "bullets": [], "sources": [1]},
                {"heading": "The constraint", "body": "A third field note.", "bullets": [], "sources": [1]},
            ],
            "conclusion": "The evidence points to a measured next step.",
            "upside": ["A credible upside."],
            "risks": ["A credible risk."],
            "watch_next": ["A concrete signal."],
            "takeaways": ["A source-tied takeaway."],
        }
        rendered = markgitup.render_article(
            7, "A Better Research Signal", "AI systems", angle, results, article, markgitup.now_local()
        )
        for marker in (
            'class="hero"',
            'class="layout"',
            'Editor’s brief',
            'FIELD NOTE',
            'Evidence desk',
            'Where it could go',
            'What could go wrong',
            'Watch next',
            'Closing read',
            'Five takeaways',
            'class="citation"',
            'scrollY/max',
        ):
            self.assertIn(marker, rendered)
        self.assertNotIn("PHP", rendered.upper())
        self.assertTrue(rendered.startswith("<!DOCTYPE html>"))
        self.assertTrue(rendered.endswith("</html>"))

    def test_fallback_keeps_source_only_runs_in_the_same_editorial_shape(self):
        results = [
            {"title": f"Source {i}", "content": f"Evidence {i}", "url": f"https://example.com/{i}", "domain": "example.com"}
            for i in range(1, 13)
        ]
        article = markgitup.fallback_article("A fallback signal", {"angle": "A test angle."}, results)
        self.assertEqual(len(article["sections"]), 4)
        self.assertNotIn("\\n", article["overview"])
        self.assertEqual(len(article["takeaways"]), 5)

    def test_index_renderer_uses_concise_summary_and_safe_text_nodes(self):
        manifest = [
            {
                "article_number": 7,
                "topic": "A </script> title",
                "file": "html/article-0007.html",
                "full_timestamp": "2026-08-08T07:00:00-07:00",
                "summary": "One short human-readable line.",
                "original_topic": "AI",
                "source_count": 5,
                "tags": "AI",
            },
            {
                "topic": "Legacy dispatch",
                "file": "html/legacy.html",
                "full_timestamp": "2026-08-08T06:00:00-07:00",
                "summary": "A concise legacy summary.",
            }
        ]
        rendered = markgitup.render_index(manifest)
        self.assertIn("Signals worth following.", rendered)
        self.assertIn("id=\"featured\"", rendered)
        self.assertIn("id=\"grid\"", rendered)
        self.assertIn("textContent=entry.summary", rendered)
        self.assertNotIn("innerHTML=", rendered)
        self.assertNotIn("ARTICLE 0000", rendered)
        self.assertIn("Research dispatch", rendered)
        self.assertIn("<script>", rendered)
        # Manifest is serialized as data, not interpolated into markup.
        self.assertIn("<\\/script>", rendered)

    def test_m_series_queries_are_open_ended_not_chip_specific(self):
        query = markgitup.normalize_topic_query(
            "Apple M4 Ultra Enables On-Device LLM Fine-Tuning for Medical Records",
            "M Series Apple Silicon LLM Inference",
        )
        self.assertNotRegex(query.lower(), r"\\bm[1-4]\\b")
        self.assertIn("m-series", query.lower())
        broad_query = markgitup.normalize_topic_query(
            "Apple M3 local inference privacy engineering",
            "AI Fraud Detection in Banking & Finance",
        )
        self.assertNotRegex(broad_query.lower(), r"\\bm[1-4]\\b")
        self.assertIn("m-series", broad_query.lower())

    def test_topic_pool_stays_at_24_durable_families(self):
        self.assertEqual(len(markgitup.TOPICS), 24)
        self.assertEqual(len({item.casefold() for item in markgitup.TOPICS}), 24)

    def test_topic_cycle_uses_each_topic_once_before_reset(self):
        with tempfile.TemporaryDirectory() as directory:
            cycle_path = Path(directory) / "topic-cycle.json"
            rng = __import__("random").Random(42)
            chosen = [
                markgitup.select_cyclic_topic(cycle_path, topics=markgitup.TOPICS, rng=rng)
                for _ in range(len(markgitup.TOPICS))
            ]
            self.assertEqual(len(chosen), 24)
            self.assertEqual(len(set(chosen)), 24)
            self.assertEqual(markgitup.load_topic_cycle(cycle_path), [])

    def test_topic_cycle_clears_full_pool_before_starting_next_cycle(self):
        with tempfile.TemporaryDirectory() as directory:
            cycle_path = Path(directory) / "topic-cycle.json"
            rng = __import__("random").Random(7)
            for _ in markgitup.TOPICS:
                markgitup.select_cyclic_topic(cycle_path, topics=markgitup.TOPICS, rng=rng)
            next_topic = markgitup.select_cyclic_topic(cycle_path, topics=markgitup.TOPICS, rng=rng)
            self.assertIn(next_topic, markgitup.TOPICS)
            self.assertEqual(markgitup.load_topic_cycle(cycle_path), [next_topic])

    def test_search_plan_excludes_recent_exact_queries_but_keeps_adjacent_lenses(self):
        now = markgitup.now_local()
        recent = [
            {"query": "Apple silicon M-series inference deployment", "searched_at": (now - timedelta(days=1)).isoformat()},
            {"query": "Apple silicon M-series inference benchmarks", "searched_at": (now - timedelta(days=4)).isoformat()},
        ]
        angle = {
            "search_query": "Apple silicon M-series inference deployment",
            "adjacent_queries": [
                "Apple silicon M-series inference benchmarks",
                "Apple silicon M-series privacy engineering",
                "Apple silicon local model serving memory bandwidth",
            ],
        }
        plan = markgitup.build_search_plan(
            "M-series local inference deployment",
            "M Series Apple Silicon LLM Inference",
            angle,
            recent,
            now=now,
            max_queries=3,
        )
        self.assertEqual(len(plan), 3)
        self.assertNotIn("Apple silicon M-series inference deployment", plan)
        self.assertIn("Apple silicon M-series inference benchmarks", plan)
        self.assertEqual(len({markgitup.canonical_query(item) for item in plan}), len(plan))

    def test_search_history_persists_all_executed_queries(self):
        with tempfile.TemporaryDirectory() as directory:
            history_path = Path(directory) / "search-history.json"
            now = markgitup.now_local()
            markgitup.record_search_history(
                history_path,
                ["privacy-first local AI deployment", "local model serving memory bandwidth"],
                topic="Local AI Tools",
                searched_at=now,
            )
            history = markgitup.load_search_history(history_path)
            self.assertEqual(len(history), 2)
            self.assertEqual(history[0]["topic"], "Local AI Tools")
            self.assertEqual(history[1]["query"], "local model serving memory bandwidth")
            plan = markgitup.build_search_plan(
                "Local AI deployment",
                "Local AI Tools",
                {"search_query": "privacy-first local AI deployment", "adjacent_queries": []},
                history,
                now=now,
                max_queries=1,
            )
            self.assertNotEqual(plan, ["privacy-first local AI deployment"])

    def test_deep_search_attempts_every_adjacent_query_and_records_it(self):
        with tempfile.TemporaryDirectory() as directory:
            history_path = Path(directory) / "search-history.json"
            queries = ["base current event", "adjacent adoption lens", "adjacent policy lens"]
            attempted = []

            def fake_search(query):
                attempted.append(query)
                return []

            with patch.object(markgitup, "search_searxng", side_effect=fake_search):
                results = markgitup.deep_search(
                    "Current event",
                    queries[0],
                    original_topic="A topic family",
                    history=[],
                    search_plan=queries,
                    history_path=history_path,
                )

            self.assertEqual(results, [])
            self.assertEqual(attempted, queries)
            self.assertEqual(
                [item["query"] for item in markgitup.load_search_history(history_path)],
                queries,
            )

    def test_reusing_an_old_query_refreshes_its_cooldown_timestamp(self):
        with tempfile.TemporaryDirectory() as directory:
            history_path = Path(directory) / "search-history.json"
            now = markgitup.now_local()
            query = "local AI deployment adoption"
            markgitup.record_search_history(history_path, [query], searched_at=now - timedelta(days=4))
            history = markgitup.load_search_history(history_path)
            self.assertFalse(markgitup.query_in_cooldown(query, history, now=now))
            markgitup.record_search_history(history_path, [query], searched_at=now)
            refreshed = markgitup.load_search_history(history_path)
            self.assertTrue(markgitup.query_in_cooldown(query, refreshed, now=now))


if __name__ == "__main__":
    unittest.main()
