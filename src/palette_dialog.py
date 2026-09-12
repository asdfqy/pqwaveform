"""Compact RGB and RGBA palette selection dialog for Qt 6."""

from PyQt6 import QtWidgets


class PaletteDialog(QtWidgets.QDialog):
    """Display project palette colors as a compact button grid."""

    def __init__(self, colors, parent=None):
        """Create one selection button for every RGB or RGBA color."""
        super().__init__(parent)
        self.selected_color = None
        self.setWindowTitle("Line color")
        layout = QtWidgets.QGridLayout(self)

        for index, source_color in enumerate(colors):
            color = tuple(source_color)
            if len(color) == 3:
                color = color + (255,)
            if len(color) != 4:
                raise ValueError("Palette colors must be RGB or RGBA tuples.")

            button = QtWidgets.QPushButton()
            button.setFixedSize(28, 22)
            button.setToolTip(
                f"RGBA: {color[0]}, {color[1]}, {color[2]}, {color[3]}"
            )
            button.setStyleSheet(
                "background-color: "
                f"rgba({color[0]}, {color[1]}, {color[2]}, {color[3]});"
            )
            button.clicked.connect(
                lambda _checked=False, value=color: self._select(value)
            )
            layout.addWidget(button, index // 8, index % 8)

    def _select(self, color):
        """Store the selected RGBA color and close the dialog."""
        self.selected_color = color
        self.accept()
