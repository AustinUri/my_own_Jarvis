"""Desktop-only controls for the signed-in OS user's private JARVIS session."""
from __future__ import annotations

import threading

from PySide6.QtCore import Qt, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFileDialog, QFormLayout, QHBoxLayout,
    QInputDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QMessageBox, QPlainTextEdit, QPushButton, QTabWidget, QVBoxLayout, QWidget,
)

from gui.styles import STYLE_SHEET


def _label(text=""):
    label = QLabel(text)
    label.setTextFormat(Qt.TextFormat.PlainText)
    label.setWordWrap(True)
    return label


def _button(text, clicked):
    button = QPushButton(text)
    button.setAutoDefault(False)
    button.clicked.connect(clicked)
    return button


def _row(*widgets):
    layout = QHBoxLayout()
    for widget in widgets:
        layout.addWidget(widget)
    return layout


def _confirm(parent, title, message):
    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setTextFormat(Qt.TextFormat.PlainText)
    box.setText(message)
    box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
    box.setDefaultButton(QMessageBox.StandardButton.No)
    try:
        return box.exec() == QMessageBox.StandardButton.Yes
    finally:
        box.deleteLater()


def _safe_error(error):
    from agent.private_brain import BrainError

    if isinstance(error, BrainError):
        return str(error)
    if isinstance(error, FileExistsError):
        return "Choose a new filename for your memory export."
    if isinstance(error, PermissionError):
        return "JARVIS could not access this selection for the current user."
    if isinstance(error, ValueError):
        return "Check the file format, collection name and conversation selection."
    return "JARVIS could not finish this action. Check local storage and provider settings."


def open_private_ai(brain_factory=None, parent=None, *, ask_private=None):
    try:
        if brain_factory is None:
            from agent.private_brain import PrivateBrain
            brain_factory = PrivateBrain
        dialog = PrivateAIDialog(brain_factory(), parent, ask_private=ask_private)
    except Exception:
        QMessageBox.warning(parent, "Private AI unavailable",
                            "JARVIS could not open this user's private storage.")
        return None
    dialog.show()
    return dialog


class PrivateAIDialog(QDialog):
    _completed = Signal(object, str)

    def __init__(self, brain, parent=None, *, ask_private=None):
        super().__init__(parent)
        self.brain = brain
        self.ask_private = ask_private if ask_private is not None else brain.ask
        self._pending = None
        self.setWindowTitle("JARVIS · Private AI")
        self.setStyleSheet(STYLE_SHEET + """
            QWidget#PrivateAIPage, QTabWidget QStackedWidget { background: #111823; }
            QTabWidget::pane { background: #111823; border: 1px solid #24384f; }
            QTabBar::tab { background: #111823; padding: 7px 12px; }
            QTabBar::tab:selected { background: #24476d; }
            QPushButton:disabled, QCheckBox:disabled {color: #8693a4;}
            QCheckBox::indicator:checked { border: 4px solid #4d7eb0; background: #e8eef7; }
            QPushButton:focus, QComboBox:focus, QLineEdit:focus, QListWidget:focus {
                border: 1px solid #8fb9d6;
            }
        """)
        self.resize(800, 630)
        main = QVBoxLayout(self)
        self.project = QComboBox()
        self.project.setAccessibleName("Active memory collection")
        self.new_project = _button("New collection…", self._new_project)
        main.addLayout(_row(_label("Active collection"), self.project, self.new_project))
        self.tabs = QTabWidget()
        main.addWidget(self.tabs)
        self._build_chat()
        self._build_providers()
        self._build_memory()
        self.notice = _label()
        main.addWidget(self.notice)
        self.project.currentIndexChanged.connect(self._change_project)
        self._completed.connect(self._finish)
        self._collections("")
        self._refresh_status()

    def _page(self, title):
        page = QWidget()
        page.setObjectName("PrivateAIPage")
        self.tabs.addTab(page, title)
        return QVBoxLayout(page)

    def _build_chat(self):
        page = self._page("Chat")
        self.active = _label()
        page.addWidget(self.active)
        page.addWidget(_label("Each question uses relevant excerpts from the active collection. "
                              "Enabling ChatGPT sends the question and those excerpts to OpenAI."))
        self.answer = QPlainTextEdit()
        self.answer.setReadOnly(True)
        self.answer.setAccessibleName("Private answer")
        page.addWidget(self.answer, 1)
        self.question = QLineEdit()
        self.question.setMaxLength(16000)
        self.question.setAccessibleName("Ask JARVIS privately")
        self.question.setPlaceholderText("Ask JARVIS privately")
        self.question.returnPressed.connect(self._ask)
        page.addLayout(_row(self.question, _button("Ask", self._ask)))
        self.remember = QCheckBox("Save new questions and answers in their active collection")
        self.remember.clicked.connect(lambda value: self._set(self.brain.set_remember, value))
        page.addWidget(self.remember)

    def _build_providers(self):
        page = self._page("Providers")
        self.connection = _label()
        page.addWidget(self.connection)
        self.login = _button("Connect with ChatGPT", lambda: self._run(
            "Finish sign-in and consent in your browser.", self.brain.connect))
        self.logout = _button("Disconnect", lambda: self._run(
            "Disconnecting from ChatGPT…", self.brain.disconnect))
        page.addLayout(_row(self.login, self.logout))
        self.cost = QCheckBox("I verified my ChatGPT credit settings")
        self.cost.clicked.connect(self._confirm_cost)
        usage = _button("Manage ChatGPT usage", lambda: QDesktopServices.openUrl(QUrl("https://chatgpt.com/settings/usage")))
        page.addLayout(_row(self.cost, usage))
        self.enable = QCheckBox("Use ChatGPT as the preferred provider")
        self.enable.clicked.connect(lambda value: self._set(self.brain.set_enabled, value))
        page.addWidget(self.enable)
        self.models = QComboBox()
        self.models.activated.connect(lambda index: self._set(
            self.brain.set_model, self.models.itemData(index)))
        self.reload_models = _button("Refresh models", lambda: self._run(
            "Checking available ChatGPT models…", self.brain.refresh_models))
        form = QFormLayout()
        self.models.setAccessibleName("ChatGPT model")
        form.addRow("ChatGPT model", _row(self.models, self.reload_models))
        page.addLayout(form)
        self.fallback = QCheckBox("Allow local fallback to Qwen, then Gemma")
        self.fallback.clicked.connect(lambda value: self._set(self.brain.set_fallback, value))
        page.addWidget(self.fallback)
        self.smoke = _button("Test ChatGPT plan inference", lambda: self._run(
            "Sending a test prompt to ChatGPT…", self.brain.smoke,
            lambda result: self.notice.setText(f"ChatGPT test response: {result}")))
        page.addWidget(self.smoke)
        self.issue = _label()
        page.addWidget(self.issue)
        page.addStretch(1)

    def _build_memory(self):
        page = self._page("Memory")
        page.addWidget(_label("Conversations in the active collection"))
        self.saved = QListWidget()
        self.saved.setAccessibleName("Saved conversations")
        self.saved.itemDoubleClicked.connect(lambda *_: self._review())
        page.addWidget(self.saved, 1)
        page.addLayout(_row(_button("Review", self._review),
                            _button("Delete conversation…", self._delete_one)))
        page.addWidget(_button("Import ChatGPT conversations…", self._choose_export))
        page.addLayout(_row(_button("Export all my memory…", self._export_user),
                            _button("Delete all my memory…", self._delete_user)))

    def _run(self, message, action, done=None):
        if self._pending is not None:
            return
        self._pending = done or (lambda _: self.notice.setText("Done."))
        self.notice.setText(message)
        self.tabs.setEnabled(False)
        self.project.setEnabled(False)
        self.new_project.setEnabled(False)

        def work():
            result, error = None, ""
            try:
                result = action()
            except Exception as exc:
                error = _safe_error(exc)
            try:
                self._completed.emit(result, error)
            except RuntimeError:
                pass  # The native application closed while the worker was running.

        threading.Thread(target=work, name="jarvis-private-ai", daemon=True).start()

    @Slot(object, str)
    def _finish(self, result, error):
        done, self._pending = self._pending, None
        self.tabs.setEnabled(True)
        self.project.setEnabled(True)
        self.new_project.setEnabled(True)
        self.notice.clear()
        try:
            self._refresh_status()
            if error:
                self.notice.setText(error)
            elif self.isVisible():
                done(result)
        except Exception as exc:
            self.notice.setText(_safe_error(exc))

    def _set(self, setter, value):
        self._run("Updating settings…", lambda: setter(value))

    def _confirm_cost(self, value):
        if value and not _confirm(self, "Confirm zero-extra-cost settings",
            "In your personal Plus or Pro workspace, open ChatGPT Settings → Usage. "
            "Verify that JARVIS's saved weekly app limit is below 100% or that credit use for apps is off. "
            "JARVIS cannot read those settings. Have you verified a control that prevents credit use for this account?"):
            self.cost.setChecked(False)
            return
        self._set(self.brain.confirm_cost, value)

    def _refresh_status(self):
        state = self.brain.status()
        connected = state["connected"]
        connection = "ChatGPT connected" if connected else "ChatGPT disconnected"
        if connected:
            connection += " · Plan inference on" if state["enabled"] else " · Plan inference off"
        active = state["active"]
        if not active or active == "None":
            active = "None available" if state["error"] else "No answer yet"
        provider = f"Current provider · {active}"
        self.connection.setText(f"{connection}\n{provider}")
        self.active.setText(provider)
        self.issue.setText(state["error"] or "")
        self.login.setText("Reconnect with ChatGPT" if connected else "Connect with ChatGPT")
        self.logout.setEnabled(connected)
        self.cost.setEnabled(connected)
        self.cost.setChecked(state["cost_confirmed"])
        self.enable.setEnabled(connected and state["cost_confirmed"])
        self.enable.setChecked(state["enabled"])
        self.models.clear()
        for slug, label in state["models"]:
            self.models.addItem(label, slug)
        self.models.setCurrentIndex(self.models.findData(state["model"]))
        self.models.setEnabled(connected and bool(self.models.count()))
        self.reload_models.setEnabled(connected)
        self.fallback.setChecked(state["fallback"])
        self.remember.setChecked(state["remember"])
        self.smoke.setEnabled(connected and state["enabled"] and state["cost_confirmed"]
                              and self.models.currentIndex() >= 0)

    def _collections(self, current):
        names = dict.fromkeys(["", *self.brain.memory.collections(), current])
        self.project.blockSignals(True)
        self.project.clear()
        for name in names:
            self.project.addItem(f"Project · {name}" if name else "Personal", name)
        self.project.setCurrentIndex(self.project.findData(current))
        self.project.blockSignals(False)
        self._change_project()

    def _new_project(self):
        name, ok = QInputDialog.getText(self, "New project collection", "Project name")
        if ok and name.strip():
            name = name.strip()
            if len(name) > 256 or not name.isprintable():
                self.notice.setText("Use a printable project name of up to 256 characters.")
                return
            self._collections(name)

    def _change_project(self):
        self.question.clear()
        self.answer.clear()
        self.notice.clear()
        self.saved.clear()
        for entry in self.brain.memory.list_conversations(self.project.currentData()):
            item = QListWidgetItem(entry.title or entry.id, self.saved)
            item.setData(Qt.ItemDataRole.UserRole, entry.id)

    def _ask(self):
        question = self.question.text().strip()
        if not question:
            self.question.setFocus()
            return
        project = self.project.currentData()

        def answered(result):
            self._change_project()
            self.answer.setPlainText(result)

        self._run("Waiting for an answer…", lambda: self.ask_private(project, question), answered)

    def submit_personal(self, question):
        if self._pending is not None:
            self.notice.setText("A private action is still running. Your new question is in the Control Center.")
            return False
        self.tabs.setCurrentIndex(0)
        self.project.setCurrentIndex(self.project.findData(""))
        self.question.setText(question)
        self._ask()
        return True

    def _choose_export(self):
        path, _ = QFileDialog.getOpenFileName(self, "Preview a ChatGPT export", "",
                                              "ChatGPT export (*.zip *.json)")
        if path:
            from agent.private_memory import preview_export
            self._run("Reading conversation titles locally…", lambda: preview_export(path),
                      self._select_import)

    def _select_import(self, preview):
        dialog = QDialog(self)
        dialog.setWindowTitle("Select conversations to import")
        dialog.resize(670, 530)
        layout = QVBoxLayout(dialog)
        destination = self.project.currentData()
        layout.addWidget(_label(f"Import into {self.project.currentText()}. "
                                "Select only conversations that belong to you."))
        sources = QComboBox()
        sources.setAccessibleName("Conversation selection mode")
        sources.addItem("Select individual conversations", None)
        for project_id in preview.project_ids:
            sources.addItem(f"Whole exported project · {project_id}", project_id)
        layout.addWidget(sources)
        entries = QListWidget()
        entries.setAccessibleName("Exported conversations")
        layout.addWidget(entries, 1)
        info = _label()
        layout.addWidget(info)
        commit = _button("Confirm ownership and import…", dialog.accept)
        layout.addLayout(_row(_button("Cancel", dialog.reject), commit))

        def checked_ids():
            return [entries.item(i).data(Qt.ItemDataRole.UserRole)
                    for i in range(entries.count())
                    if entries.item(i).checkState() == Qt.CheckState.Checked]

        def update_count():
            count = len(checked_ids())
            needs_project = sources.currentData() is not None and not destination
            info.setText("Select a named destination collection before importing an entire project."
                         if needs_project else f"{count} conversations selected")
            commit.setEnabled(count > 0 and not needs_project)

        def show_choices():
            source = sources.currentData()
            entries.blockSignals(True)
            entries.clear()
            for entry in preview.conversations:
                if source is not None and entry.project_id != source:
                    continue
                item = QListWidgetItem(f"{entry.title or 'Untitled'}  ·  {entry.id}", entries)
                item.setData(Qt.ItemDataRole.UserRole, entry.id)
                if source is None:
                    item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                    item.setCheckState(Qt.CheckState.Unchecked)
                else:
                    item.setCheckState(Qt.CheckState.Checked)
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)
            entries.blockSignals(False)
            update_count()

        sources.currentIndexChanged.connect(show_choices)
        entries.itemChanged.connect(update_count)
        show_choices()
        try:
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            selected = checked_ids()
            source = sources.currentData()
        finally:
            dialog.deleteLater()
        if not selected or not _confirm(self, "Confirm ownership",
            f"Do all {len(selected)} selected conversations belong to you, and do you authorize "
            f"importing their text into {self.project.currentText()}?"):
            return

        def imported(count):
            self._collections(destination)
            self.notice.setText(f"{count} conversations added or updated.")

        self._run("Importing selected conversations…", lambda: self.brain.memory.import_selected(
            preview, conversation_ids=selected if source is None else (),
            project_ids=(source,) if source is not None else (), destination=destination,
            owner_confirmed=True), imported)

    def _selected(self):
        item = self.saved.currentItem()
        if item is None:
            self.notice.setText("Select a saved conversation first.")
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def _review(self):
        selected = self._selected()
        if selected is None:
            return
        project = self.project.currentData()

        def display(messages):
            dialog = QDialog(self)
            dialog.setWindowTitle("Review conversation")
            dialog.resize(640, 450)
            layout = QVBoxLayout(dialog)
            text = QPlainTextEdit()
            text.setReadOnly(True)
            text.setPlainText("\n\n".join(f"{m['role']}\n{m['content']}" for m in messages))
            layout.addWidget(text)
            layout.addWidget(_button("Close", dialog.accept))
            try:
                dialog.exec()
            finally:
                dialog.deleteLater()

        self._run("Opening conversation…",
                  lambda: self.brain.memory.read_conversation(project, selected), display)

    def _delete_one(self):
        selected = self._selected()
        if selected is None or not _confirm(self, "Delete conversation",
                f"Delete the selected conversation from {self.project.currentText()}?"):
            return
        project = self.project.currentData()
        self._run("Deleting conversation…",
                  lambda: self.brain.memory.delete_conversation(project, selected),
                  lambda _: self._collections(project))

    def _export_user(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export all your memory to a new file",
                                               "", "JSON (*.json)")
        if path and _confirm(self, "Export private memory",
                "Write all your personal and project conversations as readable text to this file?"):
            self._run("Exporting your memory…", lambda: self.brain.memory.export_user(path))

    def _delete_user(self):
        if _confirm(self, "Delete all your private memory",
                "Permanently delete every conversation in all your local JARVIS collections?"):
            self._run("Deleting your memory…", self.brain.memory.delete_user,
                      lambda _: self._collections(""))

    def done(self, result):
        self.answer.clear()
        self.question.clear()
        self.notice.clear()
        super().done(result)
