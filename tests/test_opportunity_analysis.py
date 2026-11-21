import json
import unittest
from unittest.mock import Mock, patch

from core.capabilities import opportunity_analysis as analysis
from core.capabilities import lead_discovery as scout
from agent.provider import OpenAICompatibleProvider, ProviderError


def sample():
    return {"status": "read", "same_host": True, "https": True,
            "page_checks": {"title": "Untrusted page title", "viewport_width": 390, "document_width": 990,
                            "h1_count": 0, "meta_description": False, "images_missing_alt": 4, "phone_links": 0},
            "links_truncated": False, "digital_presence": {"whatsapp": {"status": "not_found_in_checked_links"}}}


class OpportunityTests(unittest.TestCase):
    def test_ranked_observations_only(self):
        ranker = Mock(return_value=["mobile", "phone", "whatsapp"])
        result = analysis.analyze(sample(), ranker=ranker)
        self.assertEqual(result["status"], "ranked")
        self.assertEqual(result["recommended_actions"][0]["evidence"]["document_width"], 990)
        self.assertNotIn("Untrusted", json.dumps(ranker.call_args.args[0]))
        self.assertIsNone(result["lead_score"])
        self.assertTrue(result["requires_human_review"])

    def test_invalid_ids_fail_without_retry(self):
        ranker = Mock(return_value=["mobile", "invented", "phone"])
        result = analysis.analyze(sample(), ranker=ranker)
        self.assertEqual(result["status"], "ranked_rules")
        self.assertEqual(result["analysis_source"], "rules")
        self.assertEqual(result["model_status"], "failed")
        self.assertEqual([a["id"] for a in result["recommended_actions"]], ["mobile", "phone", "heading"])
        self.assertIsNone(result["lead_score"])
        ranker.assert_called_once()
        self.assertIn("mobile", result["measured_findings"])

    def test_incomplete_audit_no_model(self):
        ranker = Mock()
        audit = sample() | {"same_host": False}
        self.assertEqual(analysis.analyze(audit, ranker=ranker)["status"], "audit_incomplete")
        ranker.assert_not_called()

    def test_truncated_links_not_inferred_missing(self):
        self.assertNotIn("whatsapp", analysis.findings(sample() | {"links_truncated": True}))

    @patch.object(analysis, "require_local_ai_available")
    @patch.object(analysis.runtime, "loaded_models", return_value=["qwen/qwen3.5-9b"])
    @patch.object(analysis, "OpenAICompatibleProvider")
    def test_uses_existing_provider_without_memory_or_tools(self, factory, loaded, guard):
        factory.return_value.chat_without_reasoning.return_value = {"content": '{"priority_order":["mobile"]}'}
        with patch.object(analysis.runtime, "BASE_URL", "http://127.0.0.1:1234"), patch.dict(analysis.runtime.MODEL_KEYS, {"qwen": "qwen/qwen3.5-9b"}):
            self.assertEqual(analysis.rank_local({"mobile": {}}, "qwen"), ["mobile"])
        self.assertEqual(factory.call_args.kwargs["base_url"], "http://127.0.0.1:1234/v1")
        self.assertEqual(factory.call_args.kwargs["timeout"], 30)
        self.assertEqual(factory.return_value.chat_without_reasoning.call_args.kwargs, {"max_tokens": 256})
        factory.return_value.chat.assert_not_called()

    @patch.object(analysis, "require_local_ai_available")
    @patch.object(analysis.runtime, "loaded_models", return_value=["qwen/qwen3.5-9b"])
    @patch.object(analysis, "OpenAICompatibleProvider")
    def test_empty_content_diagnostic(self, factory, loaded, guard):
        factory.return_value.chat_without_reasoning.return_value = {"content": "", "reasoning_content": "private reasoning"}
        with patch.object(analysis.runtime, "BASE_URL", "http://127.0.0.1:1234"), patch.dict(analysis.runtime.MODEL_KEYS, {"qwen": "qwen/qwen3.5-9b"}):
            result = analysis.analyze(sample())
        self.assertEqual(result["status"], "ranked_rules")
        self.assertIn("separate reasoning present: True", result["model_error"])
        self.assertNotIn("private reasoning", json.dumps(result))
        factory.return_value.chat_without_reasoning.assert_called_once()

    @patch("agent.provider.gaming_reason", return_value=None)
    @patch.object(OpenAICompatibleProvider, "list_models", return_value=["wanted"])
    @patch("agent.provider.urllib.request.urlopen")
    def test_provider_forwards_schema_only_when_requested(self, urlopen, models, game):
        urlopen.return_value.__enter__.return_value.read.return_value = b'{"choices":[{"message":{"content":"ok"}}]}'
        provider = OpenAICompatibleProvider("http://127.0.0.1:1234/v1", "wanted")
        fmt = {"type": "json_schema", "json_schema": {"name": "test", "schema": {"type": "object"}}}
        provider.chat([], use_oracle_memory=False, strict_model=True, response_format=fmt)
        self.assertEqual(json.loads(urlopen.call_args.args[0].data)["response_format"], fmt)
        provider.chat([], use_oracle_memory=False, strict_model=True)
        self.assertNotIn("response_format", json.loads(urlopen.call_args.args[0].data))

    @patch("agent.provider.gaming_reason", return_value=None)
    @patch.object(OpenAICompatibleProvider, "list_models", return_value=["wanted"])
    @patch("agent.provider.urllib.request.urlopen")
    def test_native_chat_payload_and_final_message(self, urlopen, models, game):
        urlopen.return_value.__enter__.return_value.read.return_value = b'{"output":[{"type":"reasoning","content":"private"},{"type":"message","content":"ok"}]}'
        provider = OpenAICompatibleProvider("http://127.0.0.1:1234/v1", "wanted")
        self.assertEqual(provider.chat_without_reasoning("rank"), {"content": "ok"})
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "http://127.0.0.1:1234/api/v1/chat")
        self.assertEqual(json.loads(request.data), {"model": "wanted", "input": "rank", "reasoning": "off", "max_output_tokens": 256, "temperature": 0, "store": False, "stream": False})

    @patch("agent.provider.gaming_reason", return_value="Gaming")
    @patch("agent.provider.urllib.request.urlopen")
    def test_native_chat_blocks_gaming_and_remote(self, urlopen, game):
        for endpoint in ("http://127.0.0.1:1234/v1", "https://api.example.com/v1"):
            with self.assertRaises(ProviderError):
                OpenAICompatibleProvider(endpoint, "wanted").chat_without_reasoning("rank")
        urlopen.assert_not_called()

    @patch("agent.provider.gaming_reason", return_value=None)
    @patch.object(OpenAICompatibleProvider, "list_models", return_value=["wanted"])
    @patch("agent.provider.urllib.request.urlopen")
    def test_native_reasoning_only_rejected(self, urlopen, models, game):
        urlopen.return_value.__enter__.return_value.read.return_value = b'{"output":[{"type":"reasoning","content":"private"}]}'
        with self.assertRaisesRegex(ProviderError, "no final message"):
            OpenAICompatibleProvider("http://127.0.0.1:1234/v1", "wanted").chat_without_reasoning("rank")

    @patch.object(analysis, "require_local_ai_available")
    @patch.object(analysis.runtime, "loaded_models", return_value=[])
    @patch.object(analysis, "OpenAICompatibleProvider")
    def test_unloaded_model_or_nonlocal_endpoint_do_not_generate(self, factory, loaded, guard):
        with patch.object(analysis.runtime, "BASE_URL", "http://127.0.0.1:1234"):
            with self.assertRaises(RuntimeError):
                analysis.rank_local({"mobile": {}}, "qwen")
        with patch.object(analysis.runtime, "BASE_URL", "https://api.example.com"):
            with self.assertRaises(ValueError):
                analysis.rank_local({"mobile": {}}, "qwen")
        factory.assert_not_called()

    @patch.object(OpenAICompatibleProvider, "list_models", return_value=["other-model"])
    def test_strict_provider_never_falls_back(self, models):
        provider = OpenAICompatibleProvider("http://127.0.0.1:1234/v1", "wanted")
        with self.assertRaises(ProviderError):
            provider.resolve_model(strict=True)
        self.assertEqual(provider.resolve_model(), "other-model")

    def test_website_builder_not_business_domain(self):
        result = scout.audit_site("https://shop.example/", validate=lambda url: None,
            reader=lambda *a, **k: {"status": "read", "final_url": "https://shop.example/", "inspection": {},
              "links": [{"label": "Website builder", "url": "https://builder.example/"}]})
        self.assertEqual([x["url"] for x in result["digital_presence"]["website"]["evidence"]], ["https://shop.example/"])
