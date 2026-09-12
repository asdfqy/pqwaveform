"""One explicit confirmation for all history-associated Python code."""
from PyQt6 import QtWidgets


class HistoryCodeDialog(QtWidgets.QDialog):
    """Review all code sections and authorize one ordered execution pass."""

    RUN_CODE = 2

    def __init__(self, sections, trace_names=None, parent=None):
        super().__init__(parent)
        self.sections = sections or {}
        self.trace_names = trace_names or {}
        self.editors = {}
        self.setWindowTitle("Restore calculated graphs")
        self.resize(900, 650)
        layout = QtWidgets.QVBoxLayout(self)
        message = QtWidgets.QLabel(
            "Review all stored Python code. Run authorizes the complete "
            "ordered sequence once: setup code, then each trace's code "
            "while that trace is active. Cancel keeps the restored base state."
        )
        message.setWordWrap(True)
        layout.addWidget(message)
        tabs = QtWidgets.QTabWidget()
        layout.addWidget(tabs)
        before = QtWidgets.QPlainTextEdit()
        before.setPlainText(self.sections.get("before_traces", ""))
        self.editors["before_traces"] = before
        tabs.addTab(before, "Before traces")
        for trace_id, code in self.sections.get("traces", {}).items():
            editor = QtWidgets.QPlainTextEdit()
            editor.setPlainText(code or "")
            self.editors[str(trace_id)] = editor
            name = self.trace_names.get(int(trace_id), f"Trace {trace_id}")
            tabs.addTab(editor, f"Trace {trace_id}: {name}")
        buttons = QtWidgets.QDialogButtonBox()
        run = buttons.addButton(
            "Run all", QtWidgets.QDialogButtonBox.ButtonRole.AcceptRole
        )
        buttons.addButton(QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        run.clicked.connect(lambda: self.done(self.RUN_CODE))
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def reviewed_sections(self):
        """Return all code after possible review edits."""
        return {
            "before_traces": self.editors["before_traces"].toPlainText(),
            "traces": {
                key: editor.toPlainText()
                for key, editor in self.editors.items()
                if key != "before_traces"
            },
        }
