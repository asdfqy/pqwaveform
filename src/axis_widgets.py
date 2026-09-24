"""Engineering axes and per-trace display settings."""

import math
import pyqtgraph as pg
from PyQt6 import QtWidgets

SI = {
    -24: "y",
    -21: "z",
    -18: "a",
    -15: "f",
    -12: "p",
    -9: "n",
    -6: "u",
    -3: "m",
    0: "",
    3: "k",
    6: "M",
    9: "G",
    12: "T",
    15: "P",
    18: "E",
    21: "Z",
    24: "Y",
}


class EngineeringAxisItem(pg.AxisItem):
    """Format ticks in powers of 1000 with SI prefixes."""

    def __init__(self, orientation, engineering=True):
        """Create a configurable axis."""
        super().__init__(orientation=orientation)
        self.engineering = engineering

    def tickStrings(self, values, scale, spacing):
        """Return engineering tick labels."""
        if not self.engineering:
            return super().tickStrings(values, scale, spacing)
        display_values = values
        if getattr(self, "logMode", False):
            display_values = [10.0**value for value in values]
            scale = 1.0
        finite = [
            abs(value * scale)
            for value in display_values
            if math.isfinite(value) and value
        ]
        exp = (
            0
            if not finite
            else max(
                -24, min(24, int(math.floor(math.log10(max(finite)) / 3) * 3))
            )
        )
        factor = 10.0**exp
        return [
            f"{value*scale/factor:.5g}{SI[exp]}"
            if math.isfinite(value)
            else ""
            for value in display_values
        ]


class DisplaySettingsDialog(QtWidgets.QDialog):
    """Edit display values and select values applied across the active tab."""

    def __init__(self, trace, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Display settings: {trace.name}")
        self.resize(920, 600)
        self.setMinimumWidth(840)
        layout = QtWidgets.QVBoxLayout(self)
        info = QtWidgets.QLabel(
            "Check Apply to tab beside any option that should be copied "
            "to every trace in the current tab."
        )
        info.setWordWrap(True)
        layout.addWidget(info)
        grid = QtWidgets.QGridLayout()
        grid.addWidget(QtWidgets.QLabel("Option"), 0, 0)
        grid.addWidget(QtWidgets.QLabel("Value"), 0, 1)
        apply_header = QtWidgets.QLabel("Tab")
        apply_header.setToolTip("Apply checked properties to this tab")
        grid.addWidget(apply_header, 0, 2)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 3)
        grid.setColumnMinimumWidth(2, 44)
        self.controls = {}
        self.apply_to_tab = {}

        def add(row, key, label, widget):
            box = QtWidgets.QCheckBox()
            box.setChecked(False)
            box.setToolTip(f"Apply {label.lower()} to all traces in this tab")
            self.controls[key] = widget
            self.apply_to_tab[key] = box
            grid.addWidget(QtWidgets.QLabel(label), row, 0)
            grid.addWidget(widget, row, 1)
            grid.addWidget(box, row, 2, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)

        from PyQt6 import QtCore
        text_values = (
            ("title", "Plot title", trace.title),
            ("x_name", "X axis name", trace.x_name),
            ("x_unit", "X unit", trace.x_unit),
            ("y_name", "Y axis name", trace.y_name),
            ("y_unit", "Y unit", trace.y_unit),
        )
        row = 1
        for key, label, value in text_values:
            add(row, key, label, QtWidgets.QLineEdit(value))
            row += 1
        background = QtWidgets.QComboBox()
        background.addItems(["Black", "White"])
        background.setCurrentText(trace.background.title())
        add(row, "background", "Plot background", background)
        row += 1
        engineering = QtWidgets.QCheckBox()
        engineering.setChecked(trace.engineering_axes)
        add(row, "engineering_axes", "Engineering SI ticks", engineering)
        row += 1
        for key, label, value in (
            ("axis_label_size", "Axis label font", trace.axis_label_size),
            ("axis_tick_size", "Axis tick font", trace.axis_tick_size),
            ("marker_label_size", "Marker font", trace.marker_label_size),
            ("legend_font_size", "Legend font", trace.legend_font_size),
        ):
            widget = QtWidgets.QSpinBox()
            widget.setRange(6, 30)
            widget.setValue(value)
            add(row, key, label, widget)
            row += 1
        offset = QtWidgets.QDoubleSpinBox()
        offset.setRange(0, 1)
        offset.setSingleStep(0.02)
        offset.setValue(trace.marker_offset)
        add(row, "marker_offset", "Delta label offset", offset)
        layout.addLayout(grid)
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def values(self):
        """Return edited values and keys explicitly shared with the tab."""
        values = {}
        for key, widget in self.controls.items():
            if isinstance(widget, QtWidgets.QLineEdit):
                value = widget.text()
            elif isinstance(widget, QtWidgets.QComboBox):
                value = widget.currentText().lower()
            elif isinstance(widget, QtWidgets.QCheckBox):
                value = widget.isChecked()
            else:
                value = widget.value()
            values[key] = value
        shared = {
            key for key, box in self.apply_to_tab.items() if box.isChecked()
        }
        return values, shared
