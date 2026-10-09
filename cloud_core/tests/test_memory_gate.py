import tempfile
import unittest
from pathlib import Path

from cloud_core.app.shared_memory import SharedMemoryStore


class MemoryGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = SharedMemoryStore(Path(self.tmp.name) / "memory.sqlite3")

    def tearDown(self):
        self.tmp.cleanup()

    def gate(self, text, source="uri-s25", allow_auto=True):
        return self.store.process_user_text(
            text,
            source_device=source,
            allow_auto=allow_auto,
        )

    def test_explicit_remember_is_durable(self):
        result = self.gate("Remember that my test project is called Apollo")
        self.assertEqual(result["action"], "remember")
        facts = self.store.list_facts()
        self.assertEqual(len(facts), 1)
        self.assertIn("Apollo", facts[0]["value"])
        self.assertEqual(facts[0]["source_device"], "uri-s25")
        self.assertEqual(facts[0]["source_kind"], "explicit")

    def test_high_confidence_preference_can_auto_save(self):
        result = self.gate("I prefer short spoken replies")
        self.assertEqual(result["action"], "remember_auto")
        facts = self.store.list_facts()
        self.assertEqual(len(facts), 1)
        self.assertEqual(facts[0]["category"], "preference")

    def test_casual_query_does_not_become_fact(self):
        result = self.gate("What is the weather today?")
        self.assertEqual(result["action"], "none")
        self.assertEqual(self.store.list_facts(), [])

    def test_sensitive_data_is_not_auto_saved(self):
        result = self.gate("My medication is ExampleDrug 10 mg")
        self.assertEqual(result["action"], "none")
        self.assertEqual(self.store.list_facts(), [])

    def test_secret_disclosure_is_marked_no_store(self):
        result = self.gate("My password is example-secret")
        self.assertEqual(result["action"], "no_store")
        self.assertFalse(result["store_turn"])
        self.assertEqual(self.store.list_facts(), [])

    def test_secret_is_blocked_even_when_explicit(self):
        result = self.gate("Remember that my PIN is 1234")
        self.assertEqual(result["action"], "blocked")
        self.assertEqual(result["reason"], "secret")
        self.assertEqual(self.store.list_facts(), [])

    def test_correction_updates_existing_memory(self):
        first = self.gate("Remember that my test project is called Apolo")
        old_key = first["memory"]["key"]
        corrected = self.gate("Actually, my test project is called Apollo")
        self.assertEqual(corrected["action"], "correct")
        facts = self.store.list_facts()
        self.assertEqual(len(facts), 1)
        self.assertEqual(facts[0]["key"], old_key)
        self.assertIn("Apollo", facts[0]["value"])
        self.assertEqual(facts[0]["source_kind"], "correction")

    def test_forget_removes_matching_fact(self):
        self.gate("Remember that my test project is called Apollo")
        result = self.gate("Forget that my test project is called Apollo")
        self.assertEqual(result["action"], "forget")
        self.assertIsNotNone(result["forgotten"])
        self.assertEqual(self.store.list_facts(), [])

    def test_show_memory_is_deterministic(self):
        self.gate("Remember that my test project is called Apollo")
        result = self.gate("Show me what you remember")
        self.assertEqual(result["action"], "show")
        self.assertIn("Apollo", result["direct_response"])

    def test_forget_all_clears_durable_facts(self):
        self.gate("Remember that my test project is called Apollo")
        self.gate("Remember that my car is blue")
        result = self.gate("Forget everything you remember")
        self.assertEqual(result["action"], "forget_all")
        self.assertEqual(result["deleted"], 2)
        self.assertEqual(self.store.list_facts(), [])

    def test_hebrew_explicit_memory_still_works(self):
        result = self.gate("תזכור שהשם של פרויקט הבדיקה שלי הוא אפולו")
        self.assertEqual(result["action"], "remember")
        self.assertIn("אפולו", result["memory"]["value"])


if __name__ == "__main__":
    unittest.main()
