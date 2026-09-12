"""Viewport-level interaction for H/V intersection markers."""

import pyqtgraph as pg
from PyQt6 import QtCore


class MarkerController(QtCore.QObject):
    """Move marker lines using native PlotWidget viewport events."""

    marker_moved = QtCore.pyqtSignal(object)
    marker_drag_finished = QtCore.pyqtSignal(object)
    marker_edit_requested = QtCore.pyqtSignal(object)
    marker_delete_requested = QtCore.pyqtSignal(object)

    def __init__(self, plot, grab_radius=5.0):
        viewport = plot.viewport()
        super().__init__(viewport)
        self.plot = plot
        self.viewport = viewport
        self.view_box = plot.getViewBox()
        self._active = True
        self.grab_radius = float(grab_radius)
        self.markers = []
        self.active_marker = None
        self.hover_marker = None
        self.selected_marker = None
        viewport.setMouseTracking(True)
        viewport.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        viewport.installEventFilter(self)
        viewport.destroyed.connect(self._deactivate)
        plot.destroyed.connect(self._deactivate)

    def _deactivate(self, *_args):
        """Stop using Qt wrappers as soon as the plot starts destruction."""
        self._active = False
        self.active_marker = None
        self.hover_marker = None
        self.selected_marker = None
        self.markers.clear()
        self.plot = None
        self.viewport = None
        self.view_box = None

    def shutdown(self):
        """Detach before the owning TraceWidget is deleted."""
        if not self._active:
            return
        viewport = self.viewport
        self._active = False
        if viewport is not None:
            try:
                viewport.removeEventFilter(self)
                viewport.unsetCursor()
            except RuntimeError:
                pass
        self.active_marker = None
        self.hover_marker = None
        self.selected_marker = None
        self.markers.clear()
        self.plot = None
        self.viewport = None
        self.view_box = None

    def add_marker(self, marker):
        """Register an IntersectionMarker already added to the plot."""
        if marker not in self.markers:
            self.markers.append(marker)

    def remove_marker(self, marker):
        """Forget a marker and clear controller references to it."""
        if marker in self.markers:
            self.markers.remove(marker)
        if self.active_marker is marker:
            self.active_marker = None
        if self.hover_marker is marker:
            self.hover_marker = None
        if self.selected_marker is marker:
            self.selected_marker = None
        self._update_cursor(None)

    def _scene_position(self, event):
        point = event.position().toPoint()
        return self.plot.mapToScene(point)

    def _pixel_distance(self, marker, scene_position):
        mouse_view = self.view_box.mapSceneToView(scene_position)
        line = marker.line
        if marker.orientation == "v":
            reference = QtCore.QPointF(line.value(), mouse_view.y())
        else:
            reference = QtCore.QPointF(mouse_view.x(), line.value())
        marker_scene = self.view_box.mapViewToScene(reference)
        marker_pixel = self.plot.mapFromScene(marker_scene)
        mouse_pixel = self.plot.mapFromScene(scene_position)
        if marker.orientation == "v":
            return abs(marker_pixel.x() - mouse_pixel.x())
        return abs(marker_pixel.y() - mouse_pixel.y())

    def _nearest_marker(self, scene_position):
        best_marker = None
        best_distance = self.grab_radius + 1.0
        for marker in self.markers:
            if not marker.line.isVisible():
                continue
            distance = self._pixel_distance(marker, scene_position)
            if distance <= self.grab_radius and distance < best_distance:
                best_marker = marker
                best_distance = distance
        return best_marker

    @staticmethod
    def _normal_pen(marker):
        return pg.mkPen(marker.line_color, width=marker.line_width)

    @staticmethod
    def _hover_pen(marker):
        return pg.mkPen(marker.hover_color, width=marker.hover_width)

    def _update_cursor(self, marker):
        previous = self.hover_marker
        if previous is not None and previous is not marker:
            previous.line.setPen(self._normal_pen(previous))
        self.hover_marker = marker
        viewport = self.viewport
        if viewport is None:
            return
        if marker is None:
            viewport.unsetCursor()
            return
        marker.line.setPen(self._hover_pen(marker))
        cursor = (
            QtCore.Qt.CursorShape.SizeHorCursor
            if marker.orientation == "v"
            else QtCore.Qt.CursorShape.SizeVerCursor
        )
        viewport.setCursor(cursor)

    def _move_marker(self, marker, scene_position):
        position = self.view_box.mapSceneToView(scene_position)
        value = position.x() if marker.orientation == "v" else position.y()
        marker.line.setValue(value)
        self.marker_moved.emit(marker)

    def _mouse_move(self, event):
        scene_position = self._scene_position(event)
        left = QtCore.Qt.MouseButton.LeftButton
        if self.active_marker is not None and event.buttons() & left:
            self._move_marker(self.active_marker, scene_position)
            return True
        self._update_cursor(self._nearest_marker(scene_position))
        return False

    def _mouse_press(self, event):
        marker = self._nearest_marker(self._scene_position(event))
        if marker is None:
            self.selected_marker = None
            return False
        left = QtCore.Qt.MouseButton.LeftButton
        right = QtCore.Qt.MouseButton.RightButton
        if event.button() == left:
            self.active_marker = marker
            self.selected_marker = marker
            self._update_cursor(marker)
            if self.viewport is not None:
                self.viewport.setFocus()
            return True
        if event.button() == right:
            self.selected_marker = marker
            self.marker_edit_requested.emit(marker)
            return True
        return False

    def _mouse_release(self, event):
        left = QtCore.Qt.MouseButton.LeftButton
        if event.button() != left or self.active_marker is None:
            return False
        marker = self.active_marker
        self.active_marker = None
        self.marker_drag_finished.emit(marker)
        return True

    def _double_click(self, event):
        marker = self._nearest_marker(self._scene_position(event))
        if marker is None:
            return False
        self.selected_marker = marker
        self.marker_edit_requested.emit(marker)
        return True

    def delete_selected(self):
        """Delete the selected H/V marker regardless of keyboard focus."""
        if self.selected_marker is None:
            return False
        marker = self.selected_marker
        self.selected_marker = None
        self.marker_delete_requested.emit(marker)
        return True

    def _key_press(self, event):
        keys = (QtCore.Qt.Key.Key_Delete, QtCore.Qt.Key.Key_Backspace)
        if event.key() not in keys:
            return False
        return self.delete_selected()

    def eventFilter(self, watched, event):
        """Consume only gestures that target a registered marker line."""
        if not self._active or watched is not self.viewport:
            return False
        handlers = {
            QtCore.QEvent.Type.MouseMove: self._mouse_move,
            QtCore.QEvent.Type.MouseButtonPress: self._mouse_press,
            QtCore.QEvent.Type.MouseButtonRelease: self._mouse_release,
            QtCore.QEvent.Type.MouseButtonDblClick: self._double_click,
            QtCore.QEvent.Type.KeyPress: self._key_press,
        }
        handler = handlers.get(event.type())
        if handler is not None:
            return handler(event)
        if event.type() == QtCore.QEvent.Type.Leave:
            if self.active_marker is None:
                self._update_cursor(None)
        return False
