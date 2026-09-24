"""Single-window editor for persistent file-tree multi-selection."""
from PyQt6 import QtCore, QtGui, QtWidgets
from style_dialog import MARKER_CODES, MARKER_SYMBOLS, STYLE_NAMES


class MultiSelectionDialog(QtWidgets.QDialog):
    """Apply all supported bulk operations without child dialogs."""

    def __init__(self, model, styles, graph_count, parent=None):
        super().__init__(parent)
        self.model = model
        self.selected_color = tuple(styles[0].color)
        self.setWindowTitle("Edit multi-selection")
        self.resize(560, 520)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel(
            f"Editing {len(styles)} selected source/graph rows"
        ))
        form = QtWidgets.QFormLayout()
        self.width = QtWidgets.QDoubleSpinBox()
        self.width.setRange(0.5, 100.0)
        self.width.setSingleStep(0.5)
        self.width.setValue(float(styles[0].width))
        self.line_style = QtWidgets.QComboBox()
        self.line_style.addItems(STYLE_NAMES)
        self.line_style.setCurrentIndex(int(styles[0].line_style) - 1)
        self.points = QtWidgets.QCheckBox("Show original measurement points")
        self.points.setChecked(bool(styles[0].show_points))
        self.symbol = QtWidgets.QComboBox()
        self.symbol.addItems(MARKER_SYMBOLS)
        code = getattr(styles[0], "marker_symbol", "o")
        self.symbol.setCurrentIndex(
            MARKER_CODES.index(code) if code in MARKER_CODES else 0
        )
        form.addRow("Line width", self.width)
        form.addRow("Line style", self.line_style)
        form.addRow("Samples", self.points)
        form.addRow("Sample symbol", self.symbol)
        layout.addLayout(form)
        layout.addWidget(QtWidgets.QLabel("Line color"))
        colors = QtWidgets.QGridLayout()
        self.color_buttons = []
        for index, source in enumerate(model.palette):
            color = tuple(source)
            if len(color) == 3:
                color += (255,)
            button = QtWidgets.QToolButton()
            button.setFixedSize(30, 24)
            button.setCheckable(True)
            button.setStyleSheet(
                "background-color: rgba"
                f"({color[0]}, {color[1]}, {color[2]}, {color[3]});"
            )
            button.clicked.connect(
                lambda checked=False, c=color: self._select_color(c)
            )
            colors.addWidget(button, index // 10, index % 10)
            self.color_buttons.append((button, color))
        layout.addLayout(colors)
        actions = QtWidgets.QHBoxLayout()
        self.enable_y = QtWidgets.QPushButton("Enable Y")
        self.disable_y = QtWidgets.QPushButton("Disable Y")
        self.delete_graphs = QtWidgets.QPushButton(
            f"Delete selected graphs ({graph_count})"
        )
        self.delete_graphs.setEnabled(graph_count > 0)
        actions.addWidget(self.enable_y)
        actions.addWidget(self.disable_y)
        actions.addWidget(self.delete_graphs)
        layout.addLayout(actions)
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Apply
            | QtWidgets.QDialogButtonBox.StandardButton.Close
        )
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.apply_button = buttons.button(
            QtWidgets.QDialogButtonBox.StandardButton.Apply
        )

    def _select_color(self, color):
        self.selected_color = tuple(color)
        for button, value in self.color_buttons:
            button.setChecked(tuple(value) == self.selected_color)

    def changes(self):
        return {
            "color": self.selected_color,
            "width": self.width.value(),
            "line_style": self.line_style.currentIndex() + 1,
            "show_points": self.points.isChecked(),
            "marker_symbol": MARKER_CODES[self.symbol.currentIndex()],
        }
