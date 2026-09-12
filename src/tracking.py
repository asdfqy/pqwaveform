"""Nearest-point cursor and persistent draggable A/B measurement graphics."""

import numpy as np
import pyqtgraph as pg
from PyQt6 import QtCore, QtGui, QtWidgets
from engineering import display_text
from marker_items import DraggableTextItem, MeasurementLine


class WaveformTracker:
    """Track curves and measure the difference between two selected points."""

    def __init__(self, plot_widget):
        """Create cursor, markers, labels, arrows, and result graphics."""
        self.plot = plot_widget
        self.curves = []
        self.enabled = True
        self.interpolation = False
        self.current = None
        self.points = {}
        self.label_points = {}
        self.result_reference = None
        self.marker_offset = 0.04
        self.measurement_mode = "horizontal"
        self.engineering = False

        self.cursor = pg.ScatterPlotItem(
            size=9,
            brush="#ffff66",
            pen="#202020",
        )
        self.cursor_text = pg.TextItem(
            anchor=(0, 1),
            color="w",
        )
        self.plot.addItem(self.cursor, ignoreBounds=True)
        self.plot.addItem(self.cursor_text, ignoreBounds=True)

        self.markers = {}
        self.labels = {}
        self.lines = {}
        for name, color in {"A": "#ff9f1c", "B": "#2ec4b6"}.items():
            self.markers[name] = pg.ScatterPlotItem(
                size=12,
                pen=pg.mkPen(color, width=2),
                brush=(20, 20, 20),
            )
            self.labels[name] = DraggableTextItem(
                anchor=(0, 1),
                color=color,
            )
            self.labels[name].setZValue(100)
            self.lines[name] = pg.InfiniteLine(
                angle=90,
                pen=pg.mkPen(
                    color,
                    style=QtCore.Qt.PenStyle.DashLine,
                ),
            )
            for item in (
                self.markers[name],
                self.labels[name],
                self.lines[name],
            ):
                self.plot.addItem(item, ignoreBounds=True)

        self.measurement_line = MeasurementLine()
        self.left_arrow = pg.ArrowItem(angle=0)
        self.right_arrow = pg.ArrowItem(angle=180)
        self.plot.addItem(self.measurement_line, ignoreBounds=True)
        self.plot.addItem(self.left_arrow, ignoreBounds=True)
        self.plot.addItem(self.right_arrow, ignoreBounds=True)
        self.left_arrow.setZValue(25)
        self.right_arrow.setZValue(25)
        self.helper_offset = 0.0
        self.helper_reference = None
        self.updating_helper = False
        self.measurement_line.sigPositionChanged.connect(
            self._measurement_line_moved
        )
        self.result = DraggableTextItem(
            anchor=(0.5, 1),
            color="w",
            alignment="center",
        )
        self.result.setZValue(100)
        self.plot.addItem(self.result, ignoreBounds=True)

        self.proxy = pg.SignalProxy(
            self.plot.scene().sigMouseMoved,
            rateLimit=60,
            slot=self._move,
        )
        self.plot.getViewBox().sigRangeChanged.connect(
            lambda *_args: self._update_measurement()
        )
        self.clear()
        self._hide_cursor()

    def set_text_theme(self, color):
        """Apply contrast to neutral text and the A/B measurement helper."""
        self.cursor_text.setColor(color)
        self.result.setColor(color)
        self.measurement_line.setPen(pg.mkPen(color, width=2))
        self.measurement_line.setHoverPen(pg.mkPen(color, width=3))
        brush = pg.mkBrush(color)
        pen = pg.mkPen(color)
        for arrow in (self.left_arrow, self.right_arrow):
            arrow.setBrush(brush)
            arrow.setPen(pen)

    def apply_settings(self, font_size, marker_offset):
        """Apply compact marker fonts and differential-label offset."""
        font = QtGui.QFont()
        font.setPointSize(int(font_size))
        self.cursor_text.setFont(font)
        self.result.setFont(font)
        for label in self.labels.values():
            label.setFont(font)
        self.marker_offset = float(marker_offset)

    def set_engineering(self, enabled):
        """Use engineering notation for tracker and marker labels."""
        self.engineering = bool(enabled)
        self._update_measurement()

    def set_enabled(self, enabled):
        """Enable or disable the moving nearest-point cursor."""
        self.enabled = bool(enabled)
        if not self.enabled:
            self._hide_cursor()

    def set_interpolation(self, enabled):
        """Enable optional linear tracking between adjacent samples."""
        self.interpolation = bool(enabled)

    def set_measurement_mode(self, mode):
        """Select horizontal or vertical A/B measurement graphics."""
        if mode not in ("horizontal", "vertical"):
            raise ValueError("Measurement mode must be horizontal or vertical.")
        self.measurement_mode = mode
        self.helper_offset = 0.0
        self.helper_reference = None
        self._update_measurement()

    def place(self, name):
        """Place marker A or B at the current tracking point."""
        if name not in self.markers:
            raise ValueError("Marker name must be 'A' or 'B'.")
        if self.current is not None:
            self.points[name] = self.current
            self._update_measurement()

    def clear(self):
        """Remove marker points and all differential graphics."""
        self.points.clear()
        self.label_points.clear()
        self.result_reference = None
        for name in "AB":
            self.markers[name].setData([], [])
            self.labels[name].hide()
            self.lines[name].hide()
        self.measurement_line.hide()
        self.helper_offset = 0.0
        self.helper_reference = None
        self.left_arrow.hide()
        self.right_arrow.hide()
        self.result.hide()

    def _hide_cursor(self):
        """Hide the temporary nearest-point cursor."""
        self.current = None
        self.cursor.setData([], [])
        self.cursor_text.hide()

    def _move(self, event):
        """Snap the moving cursor to the closest visible finite point."""
        if not self.enabled or not event:
            return
        scene_position = event[0]
        view_box = self.plot.getViewBox()
        if not view_box.sceneBoundingRect().contains(scene_position):
            self._hide_cursor()
            return

        mouse = view_box.mapSceneToView(scene_position)
        best = None
        best_distance = 24.0**2
        for curve in self.curves:
            x_values, y_values = curve.getData()
            if x_values is None or y_values is None or len(x_values) == 0:
                continue
            x_values = np.asarray(x_values)
            y_values = np.asarray(y_values)
            valid = np.flatnonzero(
                np.isfinite(x_values) & np.isfinite(y_values)
            )
            if valid.size == 0:
                continue
            if self.interpolation and valid.size > 1:
                order = np.argsort(x_values[valid])
                sorted_x = x_values[valid][order]
                sorted_y = y_values[valid][order]
                x_value = float(np.clip(mouse.x(), sorted_x[0], sorted_x[-1]))
                y_value = float(np.interp(x_value, sorted_x, sorted_y))
            else:
                index = valid[
                    np.argmin(np.abs(x_values[valid] - mouse.x()))
                ]
                x_value = float(x_values[index])
                y_value = float(y_values[index])
            point = view_box.mapViewToScene(
                QtCore.QPointF(x_value, y_value)
            )
            distance = (point.x() - scene_position.x()) ** 2 + (
                point.y() - scene_position.y()
            ) ** 2
            if distance <= best_distance:
                best_distance = distance
                best = x_value, y_value

        if best is None:
            self._hide_cursor()
            return

        self.current = best
        self.cursor.setData([best[0]], [best[1]])
        x_text = display_text(best[0], self.engineering)
        y_text = display_text(best[1], self.engineering)
        self.cursor_text.setText(f"x {x_text}\ny {y_text}")
        self.cursor_text.setPos(*best)
        self.cursor_text.show()

    def _measurement_line_moved(self):
        """Retain only the user displacement from the automatic position."""
        if self.updating_helper or self.helper_reference is None:
            return
        self.helper_offset = (
            float(self.measurement_line.value()) - self.helper_reference
        )
        self._update_measurement()

    def helper_state(self):
        """Return a history-compatible two-coordinate helper offset."""
        if self.measurement_mode == "horizontal":
            return [0.0, self.helper_offset]
        return [self.helper_offset, 0.0]

    def restore_helper_state(self, position):
        """Restore a legacy measurement-group offset from history."""
        if self.measurement_mode == "horizontal":
            self.helper_offset = float(position[1])
        else:
            self.helper_offset = float(position[0])
        self._update_measurement()

    def _update_measurement(self):
        """Update draggable labels, arrows, deltas, reciprocals, and slope."""
        for name, (x_value, y_value) in self.points.items():
            self.markers[name].setData([x_value], [y_value])
            x_text = display_text(x_value, self.engineering, 4)
            y_text = display_text(y_value, self.engineering, 4)
            self.labels[name].setText(
                f"{name}\nx {x_text}\ny {y_text}"
            )
            previous = self.label_points.get(name)
            if previous is None or not self.labels[name].isVisible():
                self.labels[name].setPos(x_value, y_value)
            elif previous != (x_value, y_value):
                self.labels[name].moveBy(
                    x_value - previous[0], y_value - previous[1]
                )
            self.label_points[name] = (x_value, y_value)
            self.labels[name].show()
            if self.measurement_mode == "horizontal":
                self.lines[name].setAngle(90)
                self.lines[name].setPos(x_value)
            else:
                self.lines[name].setAngle(0)
                self.lines[name].setPos(y_value)
            self.lines[name].show()

        if not all(name in self.points for name in "AB"):
            return

        x_a, y_a = self.points["A"]
        x_b, y_b = self.points["B"]
        delta_x = x_b - x_a
        delta_y = y_b - y_a
        inverse_x = 1.0 / delta_x if delta_x else np.inf
        inverse_y = 1.0 / delta_y if delta_y else np.inf
        slope = delta_y / delta_x if delta_x else np.inf

        x_range, y_range = self.plot.viewRange()
        y_span = abs(y_range[1] - y_range[0])
        if self.measurement_mode == "horizontal":
            automatic = max(y_a, y_b) + 0.06 * y_span
            self.helper_reference = automatic
            helper = automatic + self.helper_offset
            result_y = helper + self.marker_offset * y_span
            self.updating_helper = True
            self.measurement_line.configure(
                "horizontal",
                helper,
                x_a,
                x_b,
                x_range,
                self.plot.getViewBox().width(),
            )
            self.updating_helper = False
            self.left_arrow.setStyle(angle=0)
            self.right_arrow.setStyle(angle=180)
            self.left_arrow.setPos(min(x_a, x_b), helper)
            self.right_arrow.setPos(max(x_a, x_b), helper)
            result_position = ((x_a + x_b) / 2.0, result_y)
        else:
            x_span = abs(x_range[1] - x_range[0])
            automatic = max(x_a, x_b) + 0.06 * x_span
            self.helper_reference = automatic
            helper = automatic + self.helper_offset
            result_x = helper + self.marker_offset * x_span
            self.updating_helper = True
            self.measurement_line.configure(
                "vertical",
                helper,
                y_a,
                y_b,
                y_range,
                self.plot.getViewBox().height(),
            )
            self.updating_helper = False
            self.left_arrow.setStyle(angle=90)
            self.right_arrow.setStyle(angle=-90)
            self.left_arrow.setPos(helper, min(y_a, y_b))
            self.right_arrow.setPos(helper, max(y_a, y_b))
            result_position = (result_x, (y_a + y_b) / 2.0)
        self.left_arrow.show()
        self.right_arrow.show()

        def format_value(value):
            return display_text(value, self.engineering)

        self.result.setText(
            f"dx {format_value(delta_x)}   1/dx {format_value(inverse_x)}\n"
            f"dy {format_value(delta_y)}   1/dy {format_value(inverse_y)}\n"
            f"k {format_value(slope)}"
        )
        if self.result_reference is None or not self.result.isVisible():
            self.result.setPos(*result_position)
        else:
            self.result.moveBy(
                result_position[0] - self.result_reference[0],
                result_position[1] - self.result_reference[1],
            )
        self.result_reference = result_position
        self.result.show()

class IntersectionMarker:
    """Horizontal or vertical line with graph intersection points and labels."""

    def __init__(self, plot, orientation, value, curves):
        self.plot = plot
        self.orientation = orientation
        self.value = float(value)
        angle = 0 if orientation == "h" else 90
        self.line_color = "#ffd166"
        self.hover_color = "#fff2a8"
        self.line_width = 1.5
        self.hover_width = 1.5
        self.line = pg.InfiniteLine(
            pos=self.value,
            angle=angle,
            movable=False,
            pen=pg.mkPen(self.line_color, width=self.line_width),
        )
        self.line.setZValue(50)
        self.plot.addItem(self.line)
        self.points = pg.ScatterPlotItem(
            size=10,
            pen=pg.mkPen("#ffd166", width=2),
            brush=pg.mkBrush(20, 20, 20),
        )
        self.points.setZValue(200)
        plot.addItem(self.points)
        self.labels = []
        self.curves = curves
        self.font_size = 8
        self.text_color = "#d8d8d8"
        self.previous_intersections = []
        self.engineering = False
        self.line.sigPositionChanged.connect(self.update)
        self.update()

    def set_engineering(self, enabled):
        """Use engineering notation for intersection coordinates."""
        self.engineering = bool(enabled)
        self.update()

    def set_text_theme(self, color):
        """Apply contrast only to H/V coordinate labels."""
        self.text_color = color
        for label in self.labels:
            label.setColor(color)

    def set_font_size(self, font_size):
        """Apply one common font without changing label alignments."""
        self.font_size = int(font_size)
        font = QtGui.QFont()
        font.setPointSize(self.font_size)
        for label in self.labels:
            label.setFont(font)

    def edit_value(self, line=None):
        """Edit the marker coordinate after a double or right click."""
        del line
        axis = "Y" if self.orientation == "h" else "X"
        value, accepted = QtWidgets.QInputDialog.getDouble(
            None,
            "Intersection marker",
            f"{axis} coordinate:",
            self.value,
            decimals=12,
        )
        if accepted:
            self.line.setValue(value)

    @staticmethod
    def _crossings(x_values, y_values, orientation, value):
        """Return linearly interpolated crossings of a polyline and marker."""
        x_values = np.asarray(x_values, dtype=float)
        y_values = np.asarray(y_values, dtype=float)
        result = []
        for index in range(len(x_values) - 1):
            x_a, x_b = x_values[index : index + 2]
            y_a, y_b = y_values[index : index + 2]
            if not np.all(np.isfinite((x_a, x_b, y_a, y_b))):
                continue
            a, b = (y_a, y_b) if orientation == "h" else (x_a, x_b)
            if value < min(a, b) or value > max(a, b) or a == b:
                continue
            fraction = (value - a) / (b - a)
            x_value = x_a + fraction * (x_b - x_a)
            y_value = y_a + fraction * (y_b - y_a)
            result.append((float(x_value), float(y_value)))
        return result

    def update(self):
        """Recalculate intersections after moving the reference line."""
        self.value = float(self.line.value())
        intersections = []
        for curve in self.curves:
            x_values, y_values = curve.getData()
            if x_values is not None and y_values is not None:
                for point in self._crossings(
                    x_values, y_values, self.orientation, self.value
                ):
                    duplicate = any(
                        np.allclose(point, old, rtol=1e-10, atol=1e-14)
                        for old in intersections
                    )
                    if not duplicate:
                        intersections.append(point)
        self.points.setData(
            [point[0] for point in intersections],
            [point[1] for point in intersections],
        )
        old_label_count = len(self.labels)
        previously_visible = [label.isVisible() for label in self.labels]
        while len(self.labels) < len(intersections):
            label = DraggableTextItem(
                anchor=(0, 1),
                color=self.text_color,
            )
            font = QtGui.QFont()
            font.setPointSize(self.font_size)
            label.setFont(font)
            label.setZValue(100)
            self.plot.addItem(label)
            self.labels.append(label)
        for index, (label, point) in enumerate(
            zip(self.labels, intersections)
        ):
            x_text = display_text(point[0], self.engineering)
            y_text = display_text(point[1], self.engineering)
            label.setText(f"{x_text} / {y_text}")
            if index >= old_label_count or not previously_visible[index]:
                label.setPos(*point)
            elif index < len(self.previous_intersections):
                previous = self.previous_intersections[index]
                label.moveBy(point[0] - previous[0], point[1] - previous[1])
            label.show()
        for label in self.labels[len(intersections) :]:
            label.hide()
        self.previous_intersections = intersections
