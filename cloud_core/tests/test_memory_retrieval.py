from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cloud_core.app.shared_memory import SharedMemoryStore


class MemoryRetrievalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = SharedMemoryStore(Path(self.tmp.name) / "memory.sqlite3")

    def tearDown(self):
        self.tmp.cleanup()

    def test_relevant_fact_is_returned(self):
        self.store.remember(
            "my test project is called Apolo",
            source_device="uri-s25",
        )
        context = self.store.context_for("What is my test project called?")
        self.assertIn("Apolo", context["prompt"])

    def test_irrelevant_fact_is_not_injected(self):
        self.store.remember(
            "my test project is called Apolo",
            source_device="uri-s25",
        )
        context = self.store.context_for("Explain how a bicycle gear works")
        self.assertNotIn("Apolo", context["prompt"])

    def test_explicit_memory_meta_query_can_use_broad_context(self):
        self.store.remember(
            "my test project is called Apolo",
            source_device="uri-s25",
        )
        context = self.store.context_for("What do you remember about me?")
        self.assertIn("Apolo", context["prompt"])

    def test_relevant_cross_device_turn_is_returned(self):
        self.store.record_turn(
            "user",
            "The Falcon prototype needs a lighter hinge",
            source_device="uri-s25",
        )
        context = self.store.context_for("What did we say about the Falcon hinge?")
        self.assertIn("Falcon", context["prompt"])


if __name__ == "__main__":
    unittest.main()
