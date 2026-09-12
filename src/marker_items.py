"""Reusable interactive marker graphics for PQWaveForm."""

import pyqtgraph as pg
from PyQt6 import QtCore, QtWidgets


class DraggableTextItem(pg.TextItem):
    """Movable text with an individual RMB-selectable alignment."""

    ALIGNMENTS = {"left": 0.0, "center": 0.5, "right": 1.0}

    def __init__(self, *args, alignment="left", **kwargs):
        super().__init__(*args, **kwargs)
        flags = QtWidgets.QGraphicsItem.GraphicsItemFlag
        self.setFlag(flags.ItemIsMovable, True)
        self.setFlag(flags.ItemIsSelectable, True)
        buttons = (
            QtCore.Qt.MouseButton.LeftButton
            | QtCore.Qt.MouseButton.RightButton
        )
        self.setAcceptedMouseButtons(buttons)
        self.setCursor(QtCore.Qt.CursorShape.OpenHandCursor)
        self.alignment = "left"
        self.set_alignment(alignment)

    def set_alignment(self, alignment):
        """Set this label's horizontal anchor independently."""
        value = str(alignment).lower()
        if value not in self.ALIGNMENTS:
            value = "left"
        self.alignment = value
        self.setAnchor((self.ALIGNMENTS[value], 1))

    def _choose_alignment(self):
        """Open the alignment selector for this label only."""
        values = ["Left", "Center", "Right"]
        current = values.index(self.alignment.title())
        value, accepted = QtWidgets.QInputDialog.getItem(
            None,
            "Marker label alignment",
            "Horizontal alignment:",
            values,
            current,
            False,
        )
        if accepted:
            self.set_alignment(value.lower())

    def hoverEvent(self, event):
        """Claim RMB clicks so the plot ViewBox cannot consume them."""
        if not event.isExit():
            event.acceptClicks(QtCore.Qt.MouseButton.RightButton)

    def mouseClickEvent(self, event):
        """Open the individual alignment dialog on right click."""
        if event.button() == QtCore.Qt.MouseButton.RightButton:
            self._choose_alignment()
            event.accept()
            return
        super().mouseClickEvent(event)

    def contextMenuEvent(self, event):
        """Also support native Qt context-menu delivery."""
        self._choose_alignment()
        event.accept()

    def mousePressEvent(self, event):
        """Use native Qt movement for left-button dragging."""
        self.setCursor(QtCore.Qt.CursorShape.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        self.setCursor(QtCore.Qt.CursorShape.OpenHandCursor)


class EditableInfiniteLine(pg.InfiniteLine):
    """Native InfiniteLine behavior plus editing and deletion signals."""

    edit_requested = QtCore.pyqtSignal(object)
    delete_requested = QtCore.pyqtSignal(object)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        flags = QtWidgets.QGraphicsItem.GraphicsItemFlag
        self.setFlag(flags.ItemIsSelectable, True)
        self.setFlag(flags.ItemIsFocusable, True)

    def hoverEvent(self, event):
        if not event.isExit():
            event.acceptClicks(QtCore.Qt.MouseButton.LeftButton)
            event.acceptClicks(QtCore.Qt.MouseButton.RightButton)
        super().hoverEvent(event)

    def mouseClickEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.RightButton:
            self.edit_requested.emit(self)
            event.accept()
            return
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            scene = self.scene()
            if scene is not None:
                scene.clearSelection()
            self.setSelected(True)
            self.setFocus(QtCore.Qt.FocusReason.MouseFocusReason)
            event.accept()
            return
        super().mouseClickEvent(event)

    def mouseDoubleClickEvent(self, event):
        self.edit_requested.emit(self)
        event.accept()

    def keyPressEvent(self, event):
        keys = (QtCore.Qt.Key.Key_Delete, QtCore.Qt.Key.Key_Backspace)
        if event.key() in keys:
            self.delete_requested.emit(self)
            event.accept()
            return
        super().keyPressEvent(event)


class MeasurementLine(pg.InfiniteLine):
    """Finite-looking native drag handle for the A/B measurement span."""

    def __init__(self):
        super().__init__(
            pos=0.0,
            angle=0,
            movable=True,
            pen=pg.mkPen("w", width=2),
            hoverPen=pg.mkPen("w", width=3),
        )
        self.setZValue(20)
        self.hide()

    def configure(
        self, mode, position, start, stop, view_range, pixel_length=1
    ):
        """Set orientation, position, and visible fractional span."""
        if mode == "horizontal":
            self.setAngle(0)
        else:
            self.setAngle(90)
        low, high = view_range
        width = high - low
        if width:
            first = (min(start, stop) - low) / width
            second = (max(start, stop) - low) / width
            inset = min(0.02, 7.0 / max(1, pixel_length))
            if second - first > 2 * inset:
                first += inset
                second -= inset
            self.setSpan(first, second)
        self.setValue(position)
        self.show()
