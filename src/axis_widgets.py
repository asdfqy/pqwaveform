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
    """Edit axis names, units, engineering mode, fonts, and marker offset."""

    def __init__(self, trace, parent=None):
        """Create controls initialized from a trace."""
        super().__init__(parent)
        self.setWindowTitle(f"Display settings: {trace.name}")
        form = QtWidgets.QFormLayout(self)
        self.x_name = QtWidgets.QLineEdit(trace.x_name)
        self.x_unit = QtWidgets.QLineEdit(trace.x_unit)
        self.y_name = QtWidgets.QLineEdit(trace.y_name)
        self.y_unit = QtWidgets.QLineEdit(trace.y_unit)
        self.title = QtWidgets.QLineEdit(trace.title)
        self.background = QtWidgets.QComboBox()
        self.background.addItems(["Black", "White"])
        self.background.setCurrentText(trace.background.title())
        self.engineering = QtWidgets.QCheckBox()
        self.engineering.setChecked(trace.engineering_axes)
        self.axis_label_size = QtWidgets.QSpinBox()
        self.axis_tick_size = QtWidgets.QSpinBox()
        self.marker_label_size = QtWidgets.QSpinBox()
        self.legend_font_size = QtWidgets.QSpinBox()
        for widget, value in (
            (self.axis_label_size, trace.axis_label_size),
            (self.axis_tick_size, trace.axis_tick_size),
            (self.marker_label_size, trace.marker_label_size),
            (self.legend_font_size, trace.legend_font_size),
        ):
            widget.setRange(6, 30)
            widget.setValue(value)
        self.marker_offset = QtWidgets.QDoubleSpinBox()
        self.marker_offset.setRange(0, 1)
        self.marker_offset.setSingleStep(0.02)
        self.marker_offset.setValue(trace.marker_offset)
        for label, widget in (
            ("Plot title", self.title),
            ("X axis name", self.x_name),
            ("X unit", self.x_unit),
            ("Y axis name", self.y_name),
            ("Y unit", self.y_unit),
            ("Plot background", self.background),
            ("Engineering SI ticks", self.engineering),
            ("Axis label font", self.axis_label_size),
            ("Axis tick font", self.axis_tick_size),
            ("Marker font", self.marker_label_size),
            ("Legend font", self.legend_font_size),
            ("Delta label offset", self.marker_offset),
        ):
            form.addRow(label, widget)
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def values(self):
        """Return edited settings."""
        return {
            "title": self.title.text(),
            "x_name": self.x_name.text(),
            "x_unit": self.x_unit.text(),
            "y_name": self.y_name.text(),
            "y_unit": self.y_unit.text(),
            "background": self.background.currentText().lower(),
            "engineering_axes": self.engineering.isChecked(),
            "axis_label_size": self.axis_label_size.value(),
            "axis_tick_size": self.axis_tick_size.value(),
            "marker_label_size": self.marker_label_size.value(),
            "legend_font_size": self.legend_font_size.value(),
            "marker_offset": self.marker_offset.value(),
        }
