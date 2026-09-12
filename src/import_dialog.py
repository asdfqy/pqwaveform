"""Dialogs for retrying ambiguous data imports and PDF export settings."""

from PyQt6 import QtCore, QtWidgets


class ImportSettingsDialog(QtWidgets.QDialog):
    """Edit file-specific command-line compatible import parameters."""

    def __init__(self, options, filename, error, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Data import settings")
        self.resize(620, 360)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel(f"File: {filename}"))
        message = QtWidgets.QLabel(str(error))
        message.setWordWrap(True)
        layout.addWidget(message)
        form = QtWidgets.QFormLayout()
        self.separator = QtWidgets.QLineEdit(options.dseparator)
        self.comment = QtWidgets.QLineEdit(options.dcomment)
        self.header = QtWidgets.QSpinBox()
        self.header.setRange(-1, 1000000)
        self.header.setValue(options.dheader)
        self.skip_begin = QtWidgets.QSpinBox()
        self.skip_begin.setRange(0, 1000000)
        self.skip_begin.setValue(options.dskipbegin)
        self.skip_end = QtWidgets.QSpinBox()
        self.skip_end.setRange(0, 1000000)
        self.skip_end.setValue(options.dskipend)
        self.x_column = QtWidgets.QSpinBox()
        self.x_column.setRange(0, 1000000)
        self.x_column.setValue(options.xcolumn)
        self.y_columns = QtWidgets.QLineEdit(
            " ".join(str(value) for value in options.ycolumn)
        )
        for label, widget in (
            ("Column separator / regex", self.separator),
            ("Comment prefix", self.comment),
            ("Header row (-1: none)", self.header),
            ("Skip rows at start", self.skip_begin),
            ("Skip rows at end", self.skip_end),
            ("Default X column", self.x_column),
            ("Default Y columns", self.y_columns),
        ):
            form.addRow(label, widget)
        layout.addLayout(form)
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Open
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def values(self):
        """Return validated import settings."""
        columns = [int(value) for value in self.y_columns.text().split()]
        if not columns:
            raise ValueError("At least one Y column is required.")
        return {
            "dseparator": self.separator.text() or r"\s+",
            "dcomment": self.comment.text(),
            "dheader": self.header.value(),
            "dskipbegin": self.skip_begin.value(),
            "dskipend": self.skip_end.value(),
            "xcolumn": self.x_column.value(),
            "ycolumn": columns,
        }


class PlotExportDialog(QtWidgets.QDialog):
    """Select traces, format, and background for vector export."""

    def __init__(self, model, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Export traces")
        self.resize(430, 420)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel("Select traces:"))
        self.trace_list = QtWidgets.QListWidget()
        for trace_id in model.trace_order:
            trace = model.traces[trace_id]
            item = QtWidgets.QListWidgetItem(trace.name)
            item.setData(QtCore.Qt.ItemDataRole.UserRole, trace_id)
            item.setFlags(item.flags() | QtCore.Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(QtCore.Qt.CheckState.Checked)
            self.trace_list.addItem(item)
        layout.addWidget(self.trace_list)
        self.format = QtWidgets.QComboBox()
        self.format.addItems(["PDF", "SVG"])
        layout.addWidget(QtWidgets.QLabel("Format:"))
        layout.addWidget(self.format)
        self.background = QtWidgets.QComboBox()
        self.background.addItems(["White", "Black", "Transparent"])
        layout.addWidget(QtWidgets.QLabel("Background:"))
        layout.addWidget(self.background)
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def values(self):
        """Return selected trace IDs and background name."""
        trace_ids = []
        for row in range(self.trace_list.count()):
            item = self.trace_list.item(row)
            if item.checkState() == QtCore.Qt.CheckState.Checked:
                trace_ids.append(item.data(QtCore.Qt.ItemDataRole.UserRole))
        return (trace_ids, self.format.currentText().lower(),
                self.background.currentText().lower())
