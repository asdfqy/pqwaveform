"""Searchable dialog for named JSON waveform-viewer history states."""
from PyQt6 import QtCore, QtGui, QtWidgets


class HistoryDialog(QtWidgets.QDialog):
    """Search, save, restore, delete, and assign code to traces."""

    SAVE_CURRENT = 2
    DELETE_SELECTED = 3

    def __init__(self, entries, commands=None, traces=None, parent=None):
        super().__init__(parent)
        self.entries = entries
        self.commands = list(commands or [])
        self.traces = list(traces or [])
        self.selected_indices = []
        self.selected_index = None
        self.trace_code_editors = {}
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
        for trace_id, trace_name in self.traces:
            editor = self._editor(
                f"Executed with trace {trace_id} active: {trace_name}"
            )
            self.trace_code_editors[trace_id] = editor
            self.code_tabs.addTab(editor, f"Trace {trace_id}")
        assignment = QtWidgets.QHBoxLayout()
        assignment.addWidget(QtWidgets.QLabel("Copy selected source text to:"))
        self.assignment_target = QtWidgets.QComboBox()
        self.assignment_target.addItem("Before traces", None)
        for trace_id, trace_name in self.traces:
            self.assignment_target.addItem(
                f"Trace {trace_id}: {trace_name}", trace_id
            )
        self.assign_button = QtWidgets.QPushButton("Copy selection")
        self.assign_button.clicked.connect(self.copy_selection)
        assignment.addWidget(self.assignment_target, 1)
        assignment.addWidget(self.assign_button)
        layout.addLayout(assignment)
        buttons = QtWidgets.QDialogButtonBox()
        self.save_button = buttons.addButton(
            "Save current", QtWidgets.QDialogButtonBox.ButtonRole.ActionRole
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
        self.save_button.clicked.connect(lambda: self.done(self.SAVE_CURRENT))
        self.delete_button.clicked.connect(
            lambda: self.done(self.DELETE_SELECTED)
        )
        self.load_button.clicked.connect(self.restore)
        buttons.rejected.connect(self.reject)
        self.refresh()

    @staticmethod
    def _editor(placeholder):
        editor = QtWidgets.QPlainTextEdit()
        editor.setPlaceholderText(placeholder)
        return editor

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

    def select_rows(self):
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
        if self.selected_index is not None:
            entry = self.entries[self.selected_index]
            self.name.setText(entry.get("name", ""))
            self.description.setPlainText(entry.get("description", ""))

    def restore(self):
        if len(self.selected_indices) == 1:
            self.accept()
