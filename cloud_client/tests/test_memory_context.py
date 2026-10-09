from __future__ import annotations

import unittest

from cloud_client.memory_context import (
    augment_messages_with_oracle_memory,
    inject_memory_prompt,
    last_user_text,
)


class MemoryContextTests(unittest.TestCase):
    def test_last_user_text(self):
        messages = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "first"},
            {"role": "assistant", "content": "answer"},
            {"role": "user", "content": "What is my project called?"},
        ]
        self.assertEqual(last_user_text(messages), "What is my project called?")

    def test_inject_after_system_messages_without_mutating_input(self):
        messages = [
            {"role": "system", "content": "main system"},
            {"role": "user", "content": "hello"},
        ]
        result = inject_memory_prompt(messages, "Shared facts:\n- project is Apolo")
        self.assertEqual(messages[1]["role"], "user")
        self.assertEqual(result[0]["content"], "main system")
        self.assertEqual(result[1]["role"], "system")
        self.assertIn("project is Apolo", result[1]["content"])
        self.assertEqual(result[2]["role"], "user")

    def test_duplicate_memory_marker_is_not_added(self):
        messages = [
            {
                "role": "system",
                "content": "JARVIS SHARED MEMORY (canonical Oracle cross-device context): existing",
            },
            {"role": "user", "content": "hello"},
        ]
        result = inject_memory_prompt(messages, "another")
        self.assertEqual(len(result), 2)

    def test_no_user_message_is_fail_open(self):
        messages = [{"role": "system", "content": "sys"}]
        self.assertEqual(augment_messages_with_oracle_memory(messages), messages)


if __name__ == "__main__":
    unittest.main()
