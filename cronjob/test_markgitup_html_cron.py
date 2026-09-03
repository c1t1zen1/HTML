#!/usr/bin/env python3
"""Regression tests for Markgitup model routing and attribution."""

import importlib.util
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch


SCRIPT = Path(__file__).with_name("markgitup-html-cron.py")
SPEC = importlib.util.spec_from_file_location("markgitup_html_cron", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class ModelCreditFooterTests(unittest.TestCase):
    def setUp(self):
        self.status_dir = tempfile.TemporaryDirectory(prefix="markgitup-test-")
        self.status_path_patch = patch.object(
            MODULE,
            "LOCAL_STATUS_PATH",
            Path(self.status_dir.name) / "status.json",
            create=True,
        )
        self.status_path_patch.start()

    def tearDown(self):
        self.status_path_patch.stop()
        self.status_dir.cleanup()

    def test_local_inference_uses_long_wait_window_before_fallback(self):
        self.assertEqual(MODULE.LOCAL_INFERENCE_ATTEMPTS, 2)
        self.assertGreaterEqual(MODULE.LOCAL_INFERENCE_TIMEOUT_SECONDS, 20 * 60)
        self.assertGreaterEqual(MODULE.LOCAL_INFERENCE_BUDGET_SECONDS, 40 * 60)
        self.assertLess(MODULE.LOCAL_INFERENCE_RETRY_DELAY_SECONDS, 180)

    def test_deepseek_v4_payload_disables_thinking_and_streams_progress(self):
        payload = MODULE.local_chat_payload([], 64, "deepseek-v4-flash")
        self.assertEqual(payload["thinking"], {"type": "disabled"})
        self.assertTrue(payload["stream"])
        self.assertNotIn("chat_template_kwargs", payload)

    def test_non_deepseek_payload_retains_legacy_controls(self):
        payload = MODULE.local_chat_payload([], 64, "glm-5.2-colibri")
        self.assertEqual(payload["temperature"], 0.45)
        self.assertEqual(payload["chat_template_kwargs"], {"enable_thinking": False})
        self.assertNotIn("thinking", payload)
        self.assertNotIn("stream", payload)

    def test_source_gate_requires_multiple_sources(self):
        self.assertEqual(MODULE.MINIMUM_SOURCES, 2)
        self.assertFalse(MODULE.has_minimum_sources([]))
        self.assertFalse(
            MODULE.has_minimum_sources(
                [{"url": "https://example.com/one", "domain": "example.com"}]
            )
        )
        self.assertTrue(
            MODULE.has_minimum_sources(
                [
                    {"url": "https://example.com/one", "domain": "example.com"},
                    {"url": "https://example.org/two", "domain": "example.org"},
                ]
            )
        )

    def test_source_gate_retries_with_a_new_topic_after_zero_results(self):
        first_angle = {
            "title": "Unsearchable angle",
            "search_query": "unsearchable query 2026",
            "angle": "first",
            "tags": "AI",
        }
        second_angle = {
            "title": "Source-backed angle",
            "search_query": "source-backed query 2026",
            "angle": "second",
            "tags": "AI",
        }
        results = [
            {"url": "https://example.com/one", "domain": "example.com"},
            {"url": "https://example.org/two", "domain": "example.org"},
        ]
        with patch.object(MODULE, "choose_topic", side_effect=["Topic A", "Topic B"]) as choose_topic:
            with patch.object(
                MODULE,
                "choose_angle",
                side_effect=[(first_angle, {"Model A"}), (second_angle, {"Model B"})],
            ) as choose_angle:
                with patch.object(MODULE, "deep_search", side_effect=[[], results]) as deep_search:
                    topic, angle, found, models = MODULE.find_source_backed_research(
                        [], "local-model", 999999
                    )

        self.assertEqual(topic, "Topic B")
        self.assertEqual(angle, second_angle)
        self.assertEqual(found, results)
        self.assertEqual(models, {"Model A", "Model B"})
        self.assertEqual(choose_topic.call_count, 2)
        self.assertEqual(choose_angle.call_count, 2)
        self.assertEqual(deep_search.call_count, 2)

    def test_source_gate_aborts_after_exhausting_topic_retries(self):
        with patch.object(MODULE, "MAX_SOURCE_RETRIES", 2):
            with patch.object(MODULE, "choose_topic", side_effect=["Topic A", "Topic B"]):
                with patch.object(
                    MODULE,
                    "choose_angle",
                    side_effect=[
                        ({"title": "A", "search_query": "a", "angle": "a", "tags": "AI"}, set()),
                        ({"title": "B", "search_query": "b", "angle": "b", "tags": "AI"}, set()),
                    ],
                ):
                    with patch.object(MODULE, "deep_search", side_effect=[[], []]):
                        with self.assertRaises(MODULE.MarkgitupError) as raised:
                            MODULE.find_source_backed_research([], "local-model", 999999)

        self.assertIn("at least 2 sources", str(raised.exception))

    def test_article_synthesis_rejects_insufficient_sources_before_ai(self):
        with patch.object(MODULE, "ai_chat") as mocked_ai:
            with self.assertRaises(MODULE.MarkgitupError):
                MODULE.synthesize_article(
                    "Test headline",
                    "AI research",
                    {"angle": "test", "tags": "AI"},
                    [{"url": "https://example.com/one", "domain": "example.com"}],
                    "local-model",
                    999999,
                )

        mocked_ai.assert_not_called()

    def test_render_index_omits_archived_and_under_sourced_entries(self):
        rendered = MODULE.render_index(
            [
                {
                    "article_number": 1,
                    "topic": "Good article",
                    "file": "html/good.html",
                    "full_timestamp": "2026-09-03T01:00:00+00:00",
                    "source_count": 2,
                },
                {
                    "article_number": 2,
                    "topic": "Archived article",
                    "file": "BAD/archived.html",
                    "full_timestamp": "2026-09-03T02:00:00+00:00",
                    "source_count": 0,
                    "archived": True,
                },
                {
                    "article_number": 3,
                    "topic": "Under-sourced article",
                    "file": "html/under.html",
                    "full_timestamp": "2026-09-03T03:00:00+00:00",
                    "source_count": 1,
                },
            ]
        )

        self.assertIn("Good article", rendered)
        self.assertNotIn("Archived article", rendered)
        self.assertNotIn("Under-sourced article", rendered)
        self.assertIn(".filter(entry=>!entry.archived && Number(entry.source_count||0)>=2)", rendered)
        self.assertIn('<strong id="count">1</strong>', rendered)

    def test_timeout_falls_back_without_starting_a_second_20_minute_wait(self):
        fallback_json = {"title": "Fallback angle", "search_query": "new AI signal 2026"}
        with patch.object(
            MODULE,
            "urlopen",
            side_effect=TimeoutError("timed out"),
        ) as mocked_urlopen:
            with patch.object(MODULE.time, "sleep") as mocked_sleep:
                with patch.object(MODULE, "codex_chat", return_value=json.dumps(fallback_json)):
                    response, data = MODULE.ai_chat(
                        [],
                        64,
                        "angle selection",
                        "deepseek-v4-flash",
                        999999,
                        expected="object",
                    )

        self.assertEqual(response.backend, "fallback")
        self.assertEqual(data, fallback_json)
        self.assertEqual(mocked_urlopen.call_count, 1)
        mocked_sleep.assert_not_called()

    def test_deepseek_stream_response_is_parsed_as_local_json(self):
        local_json = {"ok": True}

        class FakeStreamResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, traceback):
                return False

            def __iter__(self):
                chunks = [
                    {"choices": [{"delta": {"reasoning_content": "thinking"}}]},
                    {
                        "model": "deepseek-v4-flash",
                        "choices": [{"delta": {"content": json.dumps(local_json)}}],
                    },
                    {"choices": [{"delta": {}, "finish_reason": "stop"}]},
                ]
                for chunk in chunks:
                    yield ("data: " + json.dumps(chunk) + "\n\n").encode()
                yield b"data: [DONE]\n\n"

        with patch.object(MODULE, "urlopen", return_value=FakeStreamResponse()) as mocked_urlopen:
            with patch.object(MODULE, "codex_chat") as mocked_codex:
                response, data = MODULE.ai_chat(
                    [],
                    64,
                    "angle selection",
                    "deepseek-v4-flash",
                    999999,
                    expected="object",
                )

        self.assertEqual(response.backend, "local")
        self.assertEqual(response.model_name, "deepseek-v4-flash")
        self.assertEqual(data, local_json)
        mocked_codex.assert_not_called()
        request = mocked_urlopen.call_args.args[0]
        payload = json.loads(request.data.decode())
        self.assertEqual(payload["thinking"], {"type": "disabled"})
        self.assertTrue(payload["stream"])

    def test_local_discovery_retries_then_returns_none_for_total_outage(self):
        with patch.object(MODULE, "urlopen", side_effect=OSError("no route")) as mocked_urlopen:
            with patch.object(MODULE.time, "sleep") as mocked_sleep:
                self.assertIsNone(MODULE.discover_local_model())

        self.assertEqual(mocked_urlopen.call_count, 2)
        mocked_sleep.assert_called_once_with(MODULE.LOCAL_DISCOVERY_RETRY_DELAY_SECONDS)

    def test_ai_chat_skips_unavailable_local_model_and_uses_codex(self):
        fallback_json = {"title": "Fallback angle", "search_query": "new AI signal 2026"}
        with patch.object(MODULE, "codex_chat", return_value=json.dumps(fallback_json)) as mocked_codex:
            response, data = MODULE.ai_chat(
                [],
                64,
                "angle selection",
                None,
                0,
                expected="object",
            )

        self.assertEqual(response.backend, "fallback")
        self.assertEqual(data, fallback_json)
        mocked_codex.assert_called_once()

    def test_ai_chat_retries_local_twice_then_uses_codex(self):
        fallback_json = {"title": "Fallback angle", "search_query": "new AI signal 2026"}
        with patch.object(MODULE, "urlopen", side_effect=OSError("connection refused")) as mocked_urlopen:
            with patch.object(MODULE.time, "sleep") as mocked_sleep:
                with patch.object(MODULE, "codex_chat", return_value=json.dumps(fallback_json)) as mocked_codex:
                    response, data = MODULE.ai_chat(
                        [],
                        64,
                        "angle selection",
                        "local-model",
                        999999,
                        expected="object",
                    )

        self.assertEqual(response.backend, "fallback")
        self.assertEqual(data, fallback_json)
        self.assertEqual(mocked_urlopen.call_count, 2)
        mocked_sleep.assert_called_once_with(MODULE.LOCAL_INFERENCE_RETRY_DELAY_SECONDS)
        mocked_codex.assert_called_once()

    def test_ai_chat_uses_second_local_attempt_when_it_recovers(self):
        local_json = {"ok": True}
        local_response = MagicMock()
        local_response.__enter__.return_value.read.return_value = json.dumps(
            {
                "model": "local-model",
                "choices": [{"message": {"content": json.dumps(local_json)}}],
            }
        ).encode()
        with patch.object(
            MODULE,
            "urlopen",
            side_effect=[OSError("temporary outage"), local_response],
        ) as mocked_urlopen:
            with patch.object(MODULE.time, "sleep"):
                with patch.object(MODULE, "codex_chat") as mocked_codex:
                    response, data = MODULE.ai_chat(
                        [],
                        64,
                        "angle selection",
                        "local-model",
                        999999,
                        expected="object",
                    )

        self.assertEqual(response.backend, "local")
        self.assertEqual(data, local_json)
        self.assertEqual(mocked_urlopen.call_count, 2)
        mocked_codex.assert_not_called()

    def test_ai_chat_raises_only_when_local_and_codex_both_fail(self):
        with patch.object(MODULE, "urlopen", side_effect=OSError("local offline")):
            with patch.object(MODULE.time, "sleep"):
                with patch.object(MODULE, "codex_chat", side_effect=MODULE.MarkgitupError("codex offline")):
                    with self.assertRaises(MODULE.MarkgitupError) as raised:
                        MODULE.ai_chat([], 64, "article synthesis", None, 0, expected="object")

        self.assertIn("Codex fallback failed", str(raised.exception))

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
