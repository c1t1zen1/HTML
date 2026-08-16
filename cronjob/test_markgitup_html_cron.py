#!/usr/bin/env python3
"""Regression tests for Markgitup's model attribution footer."""

import importlib.util
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path


SCRIPT = Path(__file__).with_name("markgitup-html-cron.py")
SPEC = importlib.util.spec_from_file_location("markgitup_html_cron", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class ModelCreditFooterTests(unittest.TestCase):
    def test_local_inference_budget_is_30_minutes_with_one_attempt_before_fallback(self):
        self.assertEqual(MODULE.LOCAL_INFERENCE_BUDGET_SECONDS, 30 * 60)
        self.assertEqual(MODULE.LOCAL_INFERENCE_ATTEMPTS, 1)

    def test_local_timeout_uses_shared_run_deadline(self):
        self.assertEqual(
            MODULE.local_timeout_seconds(now=100, deadline=100 + 123),
            123,
        )
        self.assertEqual(MODULE.local_timeout_seconds(now=200, deadline=100), 1)

    def test_parse_model_ids_reads_openai_models_response(self):
        self.assertEqual(
            MODULE.parse_model_ids(
                {"object": "list", "data": [{"id": "glm-5.2-colibri", "object": "model"}]}
            ),
            ["glm-5.2-colibri"],
        )

    def test_parse_model_ids_rejects_empty_response(self):
        with self.assertRaises(MODULE.MarkgitupError):
            MODULE.parse_model_ids({"object": "list", "data": []})

    def test_local_payload_uses_discovered_model_id(self):
        payload = MODULE.local_chat_payload([], 64, "deepseek-r1")
        self.assertEqual(payload["model"], "deepseek-r1")

    def test_local_payload_does_not_use_legacy_local_llm_identifier(self):
        payload = MODULE.local_chat_payload([], 64, "glm-5.2-colibri")
        self.assertNotEqual(payload["model"], "local-llm")

    def test_local_backend_credit_names_nemotron(self):
        self.assertEqual(MODULE.model_credit({"Nemotron 3 Super"}), "Powered by Nemotron 3 Super")

    def test_fallback_backend_credit_names_gpt(self):
        self.assertEqual(
            MODULE.model_credit({"GPT 5.6 Luna"}),
            "Powered by GPT 5.6 Luna",
        )

    def test_model_credit_supports_a_llama_cpp_model_name(self):
        self.assertEqual(MODULE.model_credit({"GLM-4.5"}), "Powered by GLM-4.5")

    def test_model_credit_lists_distinct_models_used_in_one_run(self):
        self.assertEqual(
            MODULE.model_credit({"GLM-4.5", "GPT 5.6 Luna"}),
            "Powered by GLM-4.5 + GPT 5.6 Luna",
        )

    def test_saved_model_names_are_plain_names_without_footer_prefix(self):
        self.assertEqual(
            MODULE.model_names_text({"GLM-4.5", "GPT 5.6 Luna"}),
            "GLM-4.5 + GPT 5.6 Luna",
        )

    def test_article_footer_uses_selected_model_credit(self):
        html = MODULE.render_article(
            article_number=1,
            title="A test headline",
            original_topic="AI research",
            angle={"tags": "AI", "angle": "test"},
            results=[],
            article={
                "dek": "A test briefing.",
                "overview": "Overview.",
                "sections": [],
                "conclusion": "Conclusion.",
                "upside": [],
                "risks": [],
                "watch_next": [],
                "takeaways": [],
            },
            generated=datetime(2026, 8, 12, tzinfo=timezone.utc),
            model_credit_text="Powered by GPT 5.6 Luna",
        )
        self.assertIn(
            "Markgitup - hourly source-led research - AI-assisted synthesis with human-readable citations - Powered by GPT 5.6 Luna",
            html,
        )

    def test_index_references_root_globe_favicon(self):
        rendered = MODULE.render_index([])
        self.assertIn(
            '<link rel="icon" type="image/svg+xml" href="favicon.svg">',
            rendered,
        )

    def test_article_references_parent_globe_favicon(self):
        rendered = MODULE.render_article(
            article_number=1,
            title="A test headline",
            original_topic="AI research",
            angle={"tags": "AI", "angle": "test"},
            results=[],
            article={
                "dek": "A test briefing.",
                "overview": "Overview.",
                "sections": [],
                "conclusion": "Conclusion.",
                "upside": [],
                "risks": [],
                "watch_next": [],
                "takeaways": [],
            },
            generated=datetime(2026, 8, 12, tzinfo=timezone.utc),
            model_credit_text="Powered by GPT 5.6 Luna",
        )
        self.assertIn(
            '<link rel="icon" type="image/svg+xml" href="../favicon.svg">',
            rendered,
        )


if __name__ == "__main__":
    unittest.main()
