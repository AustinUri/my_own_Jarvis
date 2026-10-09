import tempfile
import unittest
from pathlib import Path

from cloud_core.app.shared_memory import SharedMemoryStore


class SharedMemoryTests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = SharedMemoryStore(Path(self.tmp.name) / "memory.sqlite3")

    def tearDown(self):
        self.tmp.cleanup()

    def test_explicit_memory_is_shared_across_devices(self):
        saved = self.store.remember_from_text(
            "Remember that my test project is called Apollo",
            source_device="uri-s25",
        )
        self.assertIsNotNone(saved)

        context = self.store.context_for(
            "What is my test project called?",
        )
        self.assertIn("Apollo", context["prompt"])
        self.assertEqual(saved["source_device"], "uri-s25")

    def test_recent_turns_preserve_source_device(self):
        self.store.record_turn(
            "user",
            "Hello from Windows",
            source_device="uri-windows",
        )
        self.store.record_turn(
            "assistant",
            "Hello, sir.",
            source_device="uri-windows",
        )
        self.store.record_turn(
            "user",
            "Now I am on my phone",
            source_device="uri-s25",
        )

        turns = self.store.recent_turns(limit=10)
        self.assertEqual(len(turns), 3)
        self.assertEqual(turns[0]["source_device"], "uri-windows")
        self.assertEqual(turns[-1]["source_device"], "uri-s25")

    def test_hebrew_remember_command(self):
        saved = self.store.remember_from_text(
            "תזכור שהשם של פרויקט הבדיקה שלי הוא אפולו",
            source_device="uri-s25",
        )
        self.assertIsNotNone(saved)
        self.assertIn("אפולו", saved["value"])


if __name__ == "__main__":
    unittest.main()
