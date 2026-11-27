import os
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

try:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication, QComboBox, QDialog, QListWidget, QPushButton
except ImportError:
    QApplication = None


@unittest.skipUnless(QApplication, "The desktop UI requires PySide6")
class PrivateDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with patch.dict(os.environ, {"QT_QPA_PLATFORM": "offscreen"}):
            cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        from agent.private_memory import PrivateMemory
        from workspace.private_ai_dialog import PrivateAIDialog

        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.brain = Mock()
        self.brain.memory = PrivateMemory(Path(directory.name) / "memory.db")
        self.brain.status.return_value = dict(
            connected=False, enabled=False, fallback=True, model="", models=[],
            active="", error="", cost_confirmed=False, remember=False,
        )
        self.view = PrivateAIDialog(self.brain)
        self.view.show()
        self.addCleanup(self.view.close)

    def finish_action(self):
        deadline = time.monotonic() + 4
        while self.view._pending is not None and time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(0.01)
        self.assertIsNone(self.view._pending)

    def test_private_answer_routes_to_active_collection_and_clears_when_switched(self):
        self.brain.ask.return_value = "Project-specific reply"
        self.view._collections("work")
        self.view.question.setText("Where did we leave off?")
        self.view._ask()
        self.finish_action()
        self.brain.ask.assert_called_once_with("work", "Where did we leave off?")
        self.assertEqual(self.view.answer.toPlainText(), "Project-specific reply")
        self.view.project.setCurrentIndex(self.view.project.findData(""))
        self.assertEqual(self.view.answer.toPlainText(), "")
        self.assertFalse(self.view.smoke.isEnabled())

    def test_declining_cost_confirmation_never_enables_inference(self):
        self.brain.status.return_value["connected"] = True
        self.view._refresh_status()
        with patch("workspace.private_ai_dialog._confirm", return_value=False):
            self.view.cost.click()
        self.brain.confirm_cost.assert_not_called()
        self.brain.smoke.assert_not_called()
        self.assertFalse(self.view.enable.isEnabled())
        self.assertFalse(self.view.smoke.isEnabled())

    def test_settings_chat_uses_supplied_private_callback_and_personal_collection(self):
        callback = Mock(return_value="Personal reply")
        self.view.ask_private = callback
        self.view._collections("")
        self.view.question.setText("Personal question")
        self.view._ask()
        self.finish_action()
        callback.assert_called_once_with("", "Personal question")
        self.brain.ask.assert_not_called()
        self.assertEqual(self.view.answer.toPlainText(), "Personal reply")
        self.assertEqual(self.view.project.currentData(), "")

    def test_preview_starts_unselected_and_import_requires_ownership_confirmation(self):
        from agent.private_memory import ConversationInfo
        preview = SimpleNamespace(conversations=(ConversationInfo("a", "First", "p"),
                                                 ConversationInfo("b", "Second", None)),
                                  project_ids=("p",))
        self.brain.memory = Mock()
        self.brain.memory.import_selected.return_value = 1
        self.brain.memory.collections.return_value = []
        self.brain.memory.list_conversations.return_value = []

        def select_one(dialog):
            entries = dialog.findChild(QListWidget)
            button = next(b for b in dialog.findChildren(QPushButton) if "ownership" in b.text())
            self.assertFalse(button.isEnabled())
            entries.item(1).setCheckState(Qt.CheckState.Checked)
            self.assertTrue(button.isEnabled())
            return QDialog.DialogCode.Accepted

        with patch.object(QDialog, "exec", new=select_one):
            with patch("workspace.private_ai_dialog._confirm", return_value=False):
                self.view._select_import(preview)
                self.brain.memory.import_selected.assert_not_called()
            with patch("workspace.private_ai_dialog._confirm", return_value=True):
                self.view._select_import(preview)
                self.finish_action()
        self.brain.memory.import_selected.assert_called_once_with(
            preview, conversation_ids=["b"], project_ids=(), destination="", owner_confirmed=True)

    def test_whole_project_requires_named_destination_and_explicit_membership(self):
        from agent.private_memory import ConversationInfo
        preview = SimpleNamespace(conversations=(ConversationInfo("a", "First", "p"),
                                                 ConversationInfo("b", "Second", None)),
                                  project_ids=("p",))
        destination = ""

        def choose_project(dialog):
            sources = dialog.findChild(QComboBox)
            entries = dialog.findChild(QListWidget)
            sources.setCurrentIndex(sources.findData("p"))
            self.assertEqual(entries.count(), 1)
            self.assertEqual(entries.item(0).data(Qt.ItemDataRole.UserRole), "a")
            button = next(b for b in dialog.findChildren(QPushButton) if "ownership" in b.text())
            self.assertEqual(button.isEnabled(), bool(destination))
            return QDialog.DialogCode.Rejected

        with patch.object(QDialog, "exec", new=choose_project):
            self.view._select_import(preview)
            destination = "work"
            self.view._collections(destination)
            self.view._select_import(preview)
