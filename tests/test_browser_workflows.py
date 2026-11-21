import subprocess
import unittest
from unittest.mock import patch

from core.capabilities import browser_runtime as browser
from core.capabilities.workflows import compose


class BrowserTests(unittest.TestCase):
    @patch.object(browser, "resolve_browser", return_value="agent-browser")
    @patch.object(browser.subprocess, "run")
    def test_mobile_inspection_uses_fixed_script(self, run, resolve):
        run.side_effect = [subprocess.CompletedProcess([], 0, text, "") for text in (
            "opened", "https://example.com", "snapshot", "viewport set",
            '{"title":"Shop","viewport_width":390,"document_width":500,"phone_links":2}', "closed")]
        result = browser.read_page("https://example.com", include_links=True, inspect_site=True)
        self.assertTrue(result["inspection"]["horizontal_overflow_hint"])
        self.assertEqual(result["inspection"]["phone_links"], 2)
        self.assertEqual(run.call_args_list[-2].args[0][-2:], ["eval", browser.SITE_CHECKS])
        self.assertEqual(run.call_args_list[-1].args[0][-1], "close")

    @patch.object(browser, "resolve_browser", return_value="agent-browser")
    @patch.object(browser.subprocess, "run")
    def test_inspection_skips_block(self, run, resolve):
        run.side_effect = [subprocess.CompletedProcess([], 0, text, "") for text in (
            "opened", "https://example.com", "reCAPTCHA", "closed")]
        result = browser.read_page("https://example.com", inspect_site=True)
        self.assertIsNone(result["inspection"])
        self.assertEqual(result["status"], "possible_block")
        self.assertEqual(run.call_count, 4)

    @patch.object(browser, "resolve_browser", return_value="agent-browser")
    @patch.object(browser.subprocess, "run")
    def test_read_isolated_and_bounded(self, run, resolve):
        run.side_effect = [subprocess.CompletedProcess([], 0, text, "") for text in
                           ("opened", "https://example.com", "x" * 9000, "closed")]
        result = browser.read_page("https://example.com")
        self.assertTrue(result["truncated"])
        self.assertEqual(len(result["untrusted_snapshot"]), 8000)
        calls = run.call_args_list
        self.assertEqual(calls[-1].args[0][-1], "close")
        self.assertEqual(len({c.args[0][2] for c in calls}), 1)
        self.assertTrue(all(c.kwargs["shell"] is False for c in calls))

    @patch.object(browser, "resolve_browser", return_value="agent-browser")
    @patch.object(browser.subprocess, "run")
    def test_block_is_reported(self, run, resolve):
        run.side_effect = [subprocess.CompletedProcess([], 0, text, "") for text in
                           ("opened", "https://example.com", "reCAPTCHA", "closed")]
        self.assertEqual(browser.read_page("https://example.com")["status"], "possible_block")

    @patch.object(browser, "resolve_browser", return_value="agent-browser")
    @patch.object(browser.subprocess, "run")
    def test_failure_still_closes(self, run, resolve):
        run.side_effect = [subprocess.CompletedProcess([], 1, "", "failed"),
                           subprocess.CompletedProcess([], 0, "closed", "")]
        with self.assertRaises(RuntimeError):
            browser.read_page("https://example.com")
        self.assertEqual(run.call_args.args[0][-1], "close")

    def test_reject_invalid_urls(self):
        for url in ("file:///etc/passwd", "https://user:pass@example.com", "https://example.com\n"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                browser.read_page(url)


class WorkflowTests(unittest.TestCase):
    def test_workflow_order_and_combination(self):
        stages = compose("website-factory")
        self.assertEqual([s.name for s in stages],
                         ["discovery", "strategy", "design", "content", "development", "quality"])
        self.assertTrue(all(len(s.skills) > 1 and s.gate for s in stages))
        self.assertEqual(compose("lead-discovery"), stages[:2])
        self.assertEqual(compose("website-audit"), stages[-1:])


if __name__ == "__main__":
    unittest.main()
