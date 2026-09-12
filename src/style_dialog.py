"""Line style editor including optional measured sample markers."""

from PyQt6 import QtWidgets


STYLE_NAMES = ("Solid", "Dash", "Dot", "Dash-dot", "Points only")


class LineStyleDialog(QtWidgets.QDialog):
    """Choose a line style and optionally overlay real sample points."""

    def __init__(self, line_style, show_points, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Line style")
        form = QtWidgets.QFormLayout(self)
        self.style = QtWidgets.QComboBox()
        self.style.addItems(STYLE_NAMES)
        self.style.setCurrentIndex(int(line_style) - 1)
        self.points = QtWidgets.QCheckBox("Show original measurement points")
        self.points.setChecked(bool(show_points))
        form.addRow("Style", self.style)
        form.addRow("Samples", self.points)
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def values(self):
        """Return internal style number and sample-marker flag."""
        return self.style.currentIndex() + 1, self.points.isChecked()
