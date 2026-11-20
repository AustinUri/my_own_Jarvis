from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase, main
from unittest.mock import patch

from agent.provider import OpenAICompatibleProvider, ProviderError
from core.gaming_mode import gaming_reason, require_local_ai_available, is_local_endpoint
from core.resource_governor import ResourceGovernor, ResourceSnapshot
from services.local_ai_runtime import acquire


class GamingModeTests(TestCase):
    def test_flag_and_auto_detection(self):
        with TemporaryDirectory() as d:
            flag = Path(d) / "gaming.flag"
            with patch("core.gaming_mode.flag_path", return_value=flag), \
                    patch("core.gaming_mode.active_game", return_value=None):
                self.assertIsNone(gaming_reason())
                flag.touch()
                self.assertIn("manually", gaming_reason())
                with self.assertRaisesRegex(RuntimeError, "paused"):
                    require_local_ai_available()
                flag.unlink()
            with patch("core.gaming_mode.flag_path", return_value=flag), \
                    patch("core.gaming_mode.active_game", return_value="cs2.exe"):
                self.assertIn("cs2.exe", gaming_reason())

    def test_governor_blocks_new_llm_work(self):
        governor = ResourceGovernor(SimpleNamespace())
        snap = ResourceSnapshot(cpu=1, ram=1)
        with patch("core.resource_governor.gaming_reason", return_value="Game active"):
            governor._apply_policy(snap)
        self.assertEqual(snap.state, "gaming")
        self.assertEqual(snap.llm_parallel_limit, 0)

    def test_provider_does_not_resolve_or_call_model_when_gaming(self):
        provider = OpenAICompatibleProvider("http://127.0.0.1:1234/v1", "qwen")
        with patch("agent.provider.gaming_reason", return_value="Game active"), \
                patch.object(OpenAICompatibleProvider, "resolve_model") as resolve:
            with self.assertRaisesRegex(ProviderError, "paused"):
                provider.chat([])
            resolve.assert_not_called()

    def test_claude_runtime_does_not_start_server_when_gaming(self):
        with patch("core.gaming_mode.gaming_reason", return_value="Game active"), \
                patch("services.local_ai_runtime.start_server") as start:
            with self.assertRaisesRegex(RuntimeError, "paused"):
                acquire("qwen")
            start.assert_not_called()

    def test_local_endpoint(self):
        self.assertTrue(is_local_endpoint("http://localhost:1234/v1"))
        self.assertTrue(is_local_endpoint("http://[::1]:1234/v1"))
        self.assertFalse(is_local_endpoint("https://example.com/v1"))


if __name__ == "__main__":
    main()
