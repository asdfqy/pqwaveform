"""Line style editor including optional measured sample markers."""

from PyQt6 import QtWidgets


STYLE_NAMES = ("Solid", "Dash", "Dot", "Dash-dot", "None")
MARKER_SYMBOLS = ("Circle", "Square", "Triangle", "Diamond", "Plus", "Cross")
MARKER_CODES = ("o", "s", "t", "d", "+", "x")


class LineStyleDialog(QtWidgets.QDialog):
    """Choose a line style and optionally overlay real sample points."""

    def __init__(self, line_style, show_points, marker_symbol="o", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Line style")
        form = QtWidgets.QFormLayout(self)
        self.style = QtWidgets.QComboBox()
        self.style.addItems(STYLE_NAMES)
        self.style.setCurrentIndex(int(line_style) - 1)
        self.points = QtWidgets.QCheckBox("Show original measurement points")
        self.points.setChecked(bool(show_points))
        self.symbol = QtWidgets.QComboBox()
        self.symbol.addItems(MARKER_SYMBOLS)
        try:
            self.symbol.setCurrentIndex(MARKER_CODES.index(marker_symbol))
        except ValueError:
            self.symbol.setCurrentIndex(0)
        form.addRow("Style", self.style)
        form.addRow("Samples", self.points)
        form.addRow("Sample symbol", self.symbol)
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def values(self):
        """Return internal style number and sample-marker flag."""
        return (self.style.currentIndex() + 1, self.points.isChecked(),
                MARKER_CODES[self.symbol.currentIndex()])
