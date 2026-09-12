"""Custom pyqtgraph view box with modifier-specific wheel zooming."""

import pyqtgraph as pg
from PyQt6 import QtCore


class AxisZoomViewBox(pg.ViewBox):
    """Zoom X with Ctrl-wheel and Y with Ctrl-Shift-wheel."""

    def wheelEvent(self, event, axis=None):
        modifiers = event.modifiers()
        control = QtCore.Qt.KeyboardModifier.ControlModifier
        shift = QtCore.Qt.KeyboardModifier.ShiftModifier
        if modifiers & control:
            axis = 1 if modifiers & shift else 0
        super().wheelEvent(event, axis=axis)
