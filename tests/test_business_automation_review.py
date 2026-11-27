import json
import os
from pathlib import Path
import subprocess
import unittest
import uuid

from core.capabilities.browser_runtime import resolve_browser
from core.capabilities.workflows import compose


ROOT = Path(__file__).resolve().parents[1]
WORKSHEET = ROOT / "skills/website-factory/references/automation-review.html"


class AutomationReviewTests(unittest.TestCase):
    def test_worksheet_is_reachable_from_strategy(self):
        stage = next(stage for stage in compose("website-factory") if stage.name == "strategy")
        self.assertIn(WORKSHEET.relative_to(ROOT).as_posix(), stage.gate)
        self.assertTrue(WORKSHEET.is_file())

    @unittest.skipUnless(os.getenv("JARVIS_TEST_AGENT_BROWSER") == "1", "Requires local Chromium and agent-browser")
    def test_owner_answers_in_local_browser(self):
        command = [resolve_browser(), "--session", "worksheet-" + uuid.uuid4().hex[:10], "--allow-file-access"]
        if executable := os.getenv("JARVIS_TEST_CHROMIUM"):
            command.extend(["--executable-path", executable])

        def run(*args):
            process = subprocess.run(command + list(args), capture_output=True, text=True,
                                     encoding="utf-8", errors="replace", timeout=45)
            self.assertEqual(process.returncode, 0, process.stderr or process.stdout)
            return process.stdout.strip()

        def evaluate(script):
            return json.loads(run("eval", script))

        def answer(active, values=None):
            changes = json.dumps(values or {})
            return evaluate(f"""(() => {{
                const choices = Array.from(document.querySelectorAll('#questions select'));
                choices.forEach((el, i) => el.value = i < {active} ? 'yes' : 'no');
                for (const [id, value] of Object.entries({changes})) document.getElementById(id).value = value;
                choices[0].dispatchEvent(new Event('change', {{bubbles:true}}));
                return [document.getElementById('score').innerText, document.getElementById('advice').innerText];
            }})()""")

        try:
            run("set", "viewport", "320", "720")
            run("open", WORKSHEET.as_uri())
            run("wait", "#questions select")
            self.assertTrue(evaluate("""document.querySelectorAll('#questions select').length === 10
                && Array.from(document.querySelectorAll('select')).every(s => s.labels.length === 1)
                && document.documentElement.scrollWidth <= innerWidth
                && document.getElementById('intake').hidden
                && performance.getEntriesByType('resource').length === 0"""))
            self.assertIn("טרם מולא", evaluate("document.getElementById('score').innerText"))
            for count in (0, 3, 4, 6, 7, 10):
                with self.subTest(count=count):
                    score, advice = answer(count)
                    self.assertIn(f"{count} מתוך 10", score)
                    expected = "עקבו אחרי" if count <= 3 else "לביקורת" if count <= 6 else "למדוד"
                    self.assertIn(expected, advice)
            self.assertIn("מענה ראשוני בוואטסאפ", answer(0, {"lead-route": "known"})[1])
            self.assertIn("כבר פועל", answer(3, {"lead-route": "known"})[1])
            self.assertIn("שני התהליכים כבר פועלים", answer(4, {"review": "yes", "follow-up": "yes"})[1])
            score, advice = answer(10, {"review": ""})
            self.assertNotIn("מתוך 10", score)
            self.assertIn("פתוחים: 1", advice)
            run("reload")
            run("wait", "#questions select")
            self.assertIn("טרם מולא", evaluate("document.getElementById('score').innerText"))
        finally:
            run("close")
