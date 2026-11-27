import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from agent.private_memory import PrivateMemory, preview_export


def node(key, parent, role, text, **fields):
    return {"id": key, "parent": parent, "message": {
        "author": {"role": role}, "content": {"content_type": "text", "parts": [text]}, **fields}}


def conversation(key, text, project=None):
    return {"id": key, "title": "Conversation " + key, "project_id": project, "current_node": "answer",
            "mapping": {"root": {"id": "root", "parent": None, "message": None},
                        "q": node("q", "root", "user", text),
                        "answer": node("answer", "q", "assistant", "Acknowledged.")}}


class PrivateMemoryTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.db = self.root / "memory.sqlite"
        self.export = self.root / "conversations.json"
        self.records = [conversation("one", "A cerulean bicycle", "bikes"),
                        conversation("two", "An amber bicycle", "bikes"),
                        conversation("three", "The private maple recipe")]
        self.write_export()
        self.store = PrivateMemory(self.db)

    def write_export(self):
        self.export.write_text(json.dumps(self.records), encoding="utf-8")

    def test_import_never_initializes_the_oracle_store(self):
        cloud_db = self.root / "separate-oracle.sqlite3"
        program = ("import sys; import agent.private_memory; "
                   "assert 'cloud_core.app.shared_memory' not in sys.modules")
        subprocess.run([sys.executable, "-c", program], check=True,
                       cwd=Path(__file__).resolve().parents[1],
                       env=dict(os.environ, JARVIS_MEMORY_DB=str(cloud_db)))
        self.assertFalse(cloud_db.exists())

    def test_shared_text_matching_preserves_english_and_hebrew(self):
        from cloud_core.app.memory_text import memory_tokens
        self.assertEqual({"bicycle", "צבע", "כחול"}, memory_tokens("WHAT is MY BiCyCle צבע שלי? כחול!"))

    def select(self, ids=("one",), project="", **args):
        return self.store.import_selected(preview_export(self.export), conversation_ids=ids,
                                          destination=project, owner_confirmed=True, **args)

    def test_metadata_preview_does_not_import_or_retain_conversation_text(self):
        preview = preview_export(self.export)
        self.assertEqual(("bikes",), preview.project_ids)
        self.assertEqual(["one", "two", "three"], [c.id for c in preview.conversations])
        self.assertFalse(any("cerulean" in str(value) for value in vars(preview).values()))
        self.assertEqual([], self.store.list_conversations(""))

    def test_explicit_selection_and_owner_confirmation(self):
        preview = preview_export(self.export)
        for consent in [False, None, "yes", 1]:
            with self.assertRaises(PermissionError):
                self.store.import_selected(preview, conversation_ids=["one"], owner_confirmed=consent, destination="")
        for ids, projects in [((), ()), (["missing"], ()), ((), ["missing"]), (["three"], ["bikes"])]:
            with self.assertRaises(ValueError):
                self.store.import_selected(preview, conversation_ids=ids, project_ids=projects,
                                           owner_confirmed=True, destination="Bike notes")
        with self.assertRaises(ValueError):
            self.select((), project_ids=["bikes"])
        self.assertEqual([""], self.store.collections())
        self.assertEqual(1, self.select())
        self.assertEqual(["one"], [c.id for c in self.store.list_conversations("")])

    def test_whole_project_uses_only_explicit_membership_and_manual_assignment(self):
        self.records[2].update(gizmo_id="bikes", project={"id": "bikes"}, title="bikes")
        self.records.append(dict(conversation("four", "contradictory", "bikes"), project={"id": "other"}))
        self.write_export()
        self.assertEqual(2, self.select((), "Bike notes", project_ids=["bikes"]))
        self.assertEqual(["one", "two"], [c.id for c in self.store.list_conversations("Bike notes")])
        self.assertEqual(1, self.select(["three"], "Kitchen"))
        self.assertEqual("", self.store.context("Bike notes", "maple"))
        self.assertIn("maple", self.store.context("Kitchen", "maple"))
        self.assertEqual("", self.store.context("", "maple"))
        with self.assertRaises(KeyError):
            self.store.read_conversation("Bike notes", "three")
        self.assertFalse(self.store.delete_conversation("Bike notes", "three"))

    def test_duplicate_incremental_reimport_and_changed_preview(self):
        self.assertEqual(1, self.select())
        self.assertEqual(0, self.select())
        old = preview_export(self.export)
        self.records[0]["mapping"]["q"]["message"]["content"]["parts"] = ["A violet bicycle"]
        self.write_export()
        with self.assertRaises(ValueError):
            self.store.import_selected(old, conversation_ids=["one"], destination="", owner_confirmed=True)
        self.assertIn("cerulean", self.store.context("", "cerulean"))
        self.assertEqual(1, self.select())
        self.assertEqual(1, len(self.store.list_conversations("")))
        self.assertEqual("", self.store.context("", "cerulean"))
        self.assertIn("violet", self.store.context("", "violet"))

    def test_active_visible_text_only(self):
        record = self.records[0]
        nodes = record["mapping"]
        nodes["orphan"] = node("orphan", "q", "assistant", "discarded")
        nodes["hidden"] = node("hidden", "q", "user", "private", metadata={"is_visually_hidden_from_conversation": True})
        nodes["tool"] = node("tool", "hidden", "tool", "command")
        nodes["analysis"] = node("analysis", "tool", "assistant", "thinking", channel="analysis")
        nodes["call"] = node("call", "analysis", "assistant", "invocation", recipient="tool")
        nodes["file"] = node("file", "call", "user", "attachment text", metadata={"attachments": [{"id": "f"}]})
        nodes["image"] = node("image", "file", "user", "image text")
        nodes["image"]["message"]["content"]["content_type"] = "multimodal_text"
        nodes["answer"]["parent"] = "image"
        self.write_export()
        self.select()
        self.assertEqual(["A cerulean bicycle", "Acknowledged."],
                         [msg["content"] for msg in self.store.read_conversation("", "one")])

    def test_older_export_does_not_overwrite_dated_conversation(self):
        self.records[0]["update_time"] = 1234567890.5
        self.write_export()
        self.assertEqual(1, self.select())
        self.records[0]["update_time"] -= 10
        self.records[0]["title"] = "Obsolete title"
        self.write_export()
        self.assertEqual(0, self.select())
        self.assertEqual("Conversation one", self.store.list_conversations("")[0].title)

    def test_unresolvable_branch_rejects_entire_selection(self):
        self.records[1]["mapping"]["q"]["parent"] = "answer"
        self.write_export()
        with self.assertRaises(ValueError):
            self.select(["one", "two"])
        self.assertEqual([], self.store.list_conversations(""))
        self.assertEqual(1, self.select(["one"]))

    def test_archive_only_reads_root_conversations_shards(self):
        archive = self.root / "export.zip"
        with zipfile.ZipFile(archive, "w") as out:
            out.writestr("conversations-001.json", json.dumps(self.records[:2]))
            out.writestr("conversations-002.json", json.dumps(self.records[2:]))
            out.writestr("user.json", "not readable")
            out.writestr("files/attachment.txt", "not read")
            out.writestr("../conversations.json", "not read")
        preview = preview_export(archive)
        self.assertEqual(3, len(preview.conversations))
        self.assertEqual(1, self.store.import_selected(preview, conversation_ids=["one"], destination="",
                                                       owner_confirmed=True))
        self.assertFalse((self.root / "files").exists())
        self.assertEqual(3, len(preview_export(self.root).conversations))
        with patch("agent.private_memory._MAX_SHARD", 30), self.assertRaises(ValueError):
            preview_export(archive)

    def test_duplicate_id_or_ambiguous_json_fails_closed(self):
        self.records.append(self.records[0])
        self.write_export()
        with self.assertRaises(ValueError):
            preview_export(self.export)
        self.export.write_text('[{"id":"one","id":"two"}]', encoding="utf-8")
        with self.assertRaises(ValueError):
            preview_export(self.export)

    def test_os_owner_scopes_read_context_update_delete_and_export(self):
        self.select(project="A")
        with patch("agent.private_memory._os_principal", return_value="different OS principal"):
            with self.assertRaises(PermissionError):
                self.store.context("A", "cerulean")
            other = PrivateMemory(self.db)
            self.assertEqual([], other.list_conversations("A"))
            self.assertEqual("", other.context("A", "cerulean"))
            with self.assertRaises(KeyError):
                other.read_conversation("A", "one")
            self.assertFalse(other.delete_conversation("A", "one"))
            other.save_turn("A", "other owner's question", "answer", enabled=True)
            out = self.root / "other.json"
            other.export_user(out)
            exported = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(1, len(exported))
            self.assertEqual("other owner's question", exported[0]["messages"][0]["content"])
            with self.assertRaises(FileExistsError):
                other.export_user(out)
            other.delete_user()
            self.assertEqual([], other.list_conversations("A"))
        self.assertEqual("one", self.store.list_conversations("A")[0].id)
        self.assertTrue(self.store.delete_conversation("A", "one"))
        self.assertEqual([], self.store.list_conversations("A"))

    def test_bounded_retrieval_and_opt_in_turn_storage(self):
        self.store.save_turn("A", "subject", "reply", enabled=False)
        self.assertEqual([], self.store.list_conversations("A"))
        self.store.save_turn("A", "bicycle choice", ("bicycle " * 350) + "unrelated tail", enabled=True)
        context = self.store.context("A", "bicycle")
        self.assertIn("bicycle", context)
        self.assertLessEqual(len(context), 3 * 420 + 2)
        self.assertEqual("", self.store.context("A", "penguin"))
        self.assertEqual("", self.store.context("", "bicycle"))

    def test_context_checks_identity_and_project_for_empty_or_stopword_only_questions(self):
        for question in ("", "what about me"):
            with self.assertRaises(ValueError):
                self.store.context(None, question)
            with patch("agent.private_memory._os_principal", return_value="other user"):
                with self.assertRaises(PermissionError):
                    self.store.context("", question)
