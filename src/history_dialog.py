"""Searchable dialog for named JSON waveform-viewer history states."""
from PyQt6 import QtCore, QtGui, QtWidgets


class HistoryDialog(QtWidgets.QDialog):
    """Search, save, restore, delete, and assign code to traces."""

    SAVE_CURRENT = 2
    DELETE_SELECTED = 3
    OVERWRITE_SELECTED = 4

    def __init__(self, entries, commands=None, traces=None, parent=None):
        super().__init__(parent)
        self.entries = entries
        self.commands = list(commands or [])
        self.traces = list(traces or [])
        self.selected_indices = []
        self.selected_index = None
        self.entries_changed = False
        self.trace_code_editors = {}
        self.current_traces = list(self.traces)
        self.current_sections = {
            "before_traces": "",
            "traces": {
                str(trace_id): "" for trace_id, _name in self.current_traces
            },
        }
        self.displaying_current_structure = True
        self.current_source_code = "\n".join(self.commands)
        self.setWindowTitle("Waveform history")
        self.resize(980, 760)
        layout = QtWidgets.QVBoxLayout(self)
        self.search = QtWidgets.QLineEdit()
        self.search.setPlaceholderText("Search date, name, or description")
        self.table = QtWidgets.QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Date", "Name", "Description"])
        self.table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection
        )
        self.table.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.search)
        layout.addWidget(self.table)
        form = QtWidgets.QFormLayout()
        self.name = QtWidgets.QLineEdit()
        self.description = QtWidgets.QPlainTextEdit()
        self.description.setMaximumHeight(70)
        form.addRow("Name", self.name)
        form.addRow("Description", self.description)
        layout.addLayout(form)
        self.code_tabs = QtWidgets.QTabWidget()
        layout.addWidget(self.code_tabs)
        self.source_code = self._editor("Central command history")
        self.source_code.setPlainText("\n".join(self.commands))
        self.pre_trace_code = self._editor(
            "Executed once after files and aliases are restored"
        )
        self.code_tabs.addTab(self.source_code, "Source")
        self.code_tabs.addTab(self.pre_trace_code, "Before traces")
        self._rebuild_trace_editors(self.current_traces, {})
        assignment = QtWidgets.QHBoxLayout()
        assignment.addWidget(QtWidgets.QLabel("Copy selected source text to:"))
        self.assignment_target = QtWidgets.QComboBox()
        self.assignment_target.addItem("Before traces", None)
        self._refresh_assignment_targets(self.current_traces)
        self.assign_button = QtWidgets.QPushButton("Copy selection")
        self.assign_button.clicked.connect(self.copy_selection)
        self.current_session_button = QtWidgets.QPushButton(
            "Show current session code"
        )
        self.current_session_button.setToolTip(
            "Rebuild the Python editor tabs for the currently running "
            "session and restore their unsaved contents"
        )
        self.current_session_button.clicked.connect(
            self.restore_current_trace_structure
        )
        assignment.addWidget(self.assignment_target, 1)
        assignment.addWidget(self.assign_button)
        assignment.addWidget(self.current_session_button)
        layout.addLayout(assignment)
        buttons = QtWidgets.QDialogButtonBox()
        self.save_button = buttons.addButton(
            "Save current", QtWidgets.QDialogButtonBox.ButtonRole.ActionRole
        )
        self.overwrite_button = buttons.addButton(
            "Overwrite selected",
            QtWidgets.QDialogButtonBox.ButtonRole.ActionRole,
        )
        self.overwrite_button.setEnabled(False)
        self.overwrite_button.setToolTip(
            "Replace the selected state with the current project state"
        )
        self.delete_button = buttons.addButton(
            "Delete selected",
            QtWidgets.QDialogButtonBox.ButtonRole.DestructiveRole,
        )
        self.load_button = buttons.addButton(
            "Restore selected",
            QtWidgets.QDialogButtonBox.ButtonRole.AcceptRole,
        )
        buttons.addButton(QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(buttons)
        self.search.textChanged.connect(self.refresh)
        self.table.itemSelectionChanged.connect(self.select_rows)
        self.table.doubleClicked.connect(self.restore)
        self.save_button.clicked.connect(self.save_current)
        self.overwrite_button.clicked.connect(self.overwrite_selected)
        self.delete_button.clicked.connect(self.delete_selected)
        self.load_button.clicked.connect(self.restore)
        buttons.rejected.connect(self.reject)
        self.refresh()

    @staticmethod
    def _editor(placeholder):
        editor = QtWidgets.QPlainTextEdit()
        editor.setPlaceholderText(placeholder)
        return editor

    def _refresh_assignment_targets(self, traces):
        """Synchronize assignment choices with the visible trace editors."""
        self.assignment_target.blockSignals(True)
        self.assignment_target.clear()
        self.assignment_target.addItem("Before traces", None)
        for trace_id, trace_name in traces:
            self.assignment_target.addItem(
                f"Trace {trace_id}: {trace_name}", int(trace_id)
            )
        self.assignment_target.blockSignals(False)

    def _rebuild_trace_editors(self, traces, sections):
        """Build code tabs from the selected history state's trace model."""
        while self.code_tabs.count() > 2:
            widget = self.code_tabs.widget(2)
            self.code_tabs.removeTab(2)
            widget.deleteLater()
        self.trace_code_editors = {}
        trace_sections = sections.get("traces", {})
        for trace_id, trace_name in traces:
            trace_id = int(trace_id)
            editor = self._editor(
                f"Executed with trace {trace_id} active: {trace_name}"
            )
            editor.setPlainText(trace_sections.get(str(trace_id), ""))
            self.trace_code_editors[trace_id] = editor
            self.code_tabs.addTab(
                editor, f"Trace {trace_id}: {trace_name}"
            )
        if hasattr(self, "assignment_target"):
            self._refresh_assignment_targets(traces)

    @staticmethod
    def _entry_traces(entry):
        """Return ordered trace IDs and names captured by one entry."""
        model = entry.get("model", {})
        by_id = {
            int(item["uid"]): item.get("name", f"Trace {item['uid']}")
            for item in model.get("traces", [])
        }
        order = model.get("trace_order", list(by_id))
        return [(int(trace_id), by_id.get(int(trace_id),
                 f"Trace {trace_id}")) for trace_id in order]

    def capture_current_editor_contents(self):
        """Retain unsaved code while current-session editors are visible."""
        if not self.displaying_current_structure:
            return
        self.current_source_code = self.source_code.toPlainText()
        self.current_sections = self.code_sections()

    def restore_current_trace_structure(self):
        """Show current-session editors and retain all unsaved contents."""
        self.capture_current_editor_contents()
        self.source_code.setPlainText(self.current_source_code)
        self.pre_trace_code.setPlainText(
            self.current_sections.get("before_traces", "")
        )
        self._rebuild_trace_editors(
            self.current_traces, self.current_sections
        )
        self.displaying_current_structure = True
        self.code_tabs.setCurrentIndex(0)

    def copy_selection(self):
        """Append selected central source text to one code section."""
        selected = self.source_code.textCursor().selectedText()
        selected = selected.replace("\u2029", "\n")
        if not selected:
            return
        trace_id = self.assignment_target.currentData()
        target = (
            self.pre_trace_code
            if trace_id is None
            else self.trace_code_editors[trace_id]
        )
        current = target.toPlainText()
        separator = "\n" if current and not current.endswith("\n") else ""
        target.setPlainText(current + separator + selected)
        target.moveCursor(QtGui.QTextCursor.MoveOperation.End)

    def code_sections(self):
        """Return pre-trace and trace-owned editable Python code."""
        return {
            "before_traces": self.pre_trace_code.toPlainText(),
            "traces": {
                str(trace_id): editor.toPlainText()
                for trace_id, editor in self.trace_code_editors.items()
            },
        }

    def selected_code(self):
        """Compatibility accessor for the unassigned central source."""
        return self.source_code.toPlainText()

    @staticmethod
    def display_date(entry):
        return str(entry.get("saved", "")).replace("T", " ")[:16]

    def refresh(self):
        query = self.search.text().casefold()
        matches = []
        for index, entry in enumerate(self.entries):
            date = self.display_date(entry)
            name = entry.get("name", "")
            description = entry.get("description", "")
            if query in f"{date} {name} {description}".casefold():
                matches.append((index, date, name, description))
        self.table.setRowCount(len(matches))
        for row, values in enumerate(matches):
            index, date, name, description = values
            date_item = QtWidgets.QTableWidgetItem(date)
            date_item.setData(QtCore.Qt.ItemDataRole.UserRole, index)
            self.table.setItem(row, 0, date_item)
            self.table.setItem(row, 1, QtWidgets.QTableWidgetItem(name))
            self.table.setItem(
                row, 2, QtWidgets.QTableWidgetItem(description)
            )
        self.table.resizeColumnToContents(0)
        self.table.resizeColumnToContents(1)

    def save_current(self):
        """Save with the current project's trace structure, not an old one."""
        self.restore_current_trace_structure()
        self.done(self.SAVE_CURRENT)

    def select_rows(self):
        self.capture_current_editor_contents()
        rows = sorted({index.row() for index in self.table.selectedIndexes()})
        self.selected_indices = []
        for row in rows:
            item = self.table.item(row, 0)
            if item is not None:
                self.selected_indices.append(
                    item.data(QtCore.Qt.ItemDataRole.UserRole)
                )
        self.selected_index = (
            self.selected_indices[0] if self.selected_indices else None
        )
        self.overwrite_button.setEnabled(len(self.selected_indices) == 1)
        if self.selected_index is not None:
            entry = self.entries[self.selected_index]
            self.name.setText(entry.get("name", ""))
            self.description.setPlainText(entry.get("description", ""))
            sections = entry.get("python_sections", {})
            self.pre_trace_code.setPlainText(
                sections.get("before_traces", "")
            )
            traces = self._entry_traces(entry)
            self._rebuild_trace_editors(traces, sections)
            self.displaying_current_structure = False
            legacy = entry.get("ipython_code", "")
            if isinstance(legacy, list):
                legacy = "\n".join(legacy)
            self.source_code.setPlainText(str(legacy or ""))

    def overwrite_selected(self):
        """Confirm replacement of one selected state with current data."""
        if len(self.selected_indices) != 1:
            return
        answer = QtWidgets.QMessageBox.question(
            self,
            "Overwrite history state",
            "Replace the selected history state with the current project "
            "configuration? This cannot be undone.",
            QtWidgets.QMessageBox.StandardButton.Yes
            | QtWidgets.QMessageBox.StandardButton.No,
            QtWidgets.QMessageBox.StandardButton.No,
        )
        if answer == QtWidgets.QMessageBox.StandardButton.Yes:
            self.restore_current_trace_structure()
            self.done(self.OVERWRITE_SELECTED)

    def delete_selected(self):
        """Delete selected rows while keeping the history dialog open."""
        if not self.selected_indices:
            return
        selected = set(self.selected_indices)
        self.entries[:] = [
            entry for index, entry in enumerate(self.entries)
            if index not in selected
        ]
        self.entries_changed = True
        self.selected_indices = []
        self.selected_index = None
        self.name.clear()
        self.description.clear()
        self.refresh()

    def restore(self):
        if len(self.selected_indices) == 1:
            self.accept()
