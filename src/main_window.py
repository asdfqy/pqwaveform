"""Main Qt6 waveform window with IPython, axes, markers, and graph controls."""

from datetime import datetime
import numpy as np
import pyqtgraph as pg
import pyqtgraph.exporters
from PyQt6 import QtCore, QtGui, QtSvg, QtWidgets
from axis_widgets import DisplaySettingsDialog, EngineeringAxisItem
from history_dialog import HistoryDialog
from history_store import (
    DEFAULT_HISTORY,
    capture_model,
    read_entries,
    restore_model,
    write_entries,
)
from import_dialog import ImportSettingsDialog, PlotExportDialog
from history_code_dialog import HistoryCodeDialog
from ipython_console import IPythonConsole
from marker_controller import MarkerController
from models import ProjectModel
from palette_dialog import PaletteDialog
from plot_theme import (
    apply_plot_appearance,
    foreground_for,
    set_graphics_text_color,
)
from plot_viewbox import AxisZoomViewBox
from script_loader import UserScriptLoader
from style_dialog import LineStyleDialog
from tracking import IntersectionMarker, WaveformTracker
from tree_model import FileGraphDelegate, FileGraphTreeModel
from ui_main_window import UiMainWindow

PENS = {
    1: QtCore.Qt.PenStyle.SolidLine,
    2: QtCore.Qt.PenStyle.DashLine,
    3: QtCore.Qt.PenStyle.DotLine,
    4: QtCore.Qt.PenStyle.DashDotLine,
}


class VerticalTraceLabel(QtWidgets.QWidget):
    """Draw a clickable vertical trace name."""

    clicked = QtCore.pyqtSignal()
    double_clicked = QtCore.pyqtSignal()

    def __init__(self, text):
        """Create the label."""
        super().__init__()
        self.text = text
        self.active = False
        self.setFixedWidth(32)

    def paintEvent(self, event):
        """Paint rotated text."""
        del event
        p = QtGui.QPainter(self)
        palette = self.palette()
        if self.active:
            background = palette.color(QtGui.QPalette.ColorRole.Highlight)
            foreground = palette.color(
                QtGui.QPalette.ColorRole.HighlightedText
            )
        else:
            background = palette.color(QtGui.QPalette.ColorRole.Window)
            foreground = palette.color(QtGui.QPalette.ColorRole.WindowText)
        p.fillRect(self.rect(), background)
        p.setPen(foreground)
        p.translate(0, self.height())
        p.rotate(-90)
        p.drawText(
            QtCore.QRect(0, 0, self.height(), self.width()),
            QtCore.Qt.AlignmentFlag.AlignCenter,
            self.text,
        )

    def mousePressEvent(self, event):
        """Activate trace."""
        del event
        self.clicked.emit()

    def mouseDoubleClickEvent(self, event):
        """Open display settings."""
        del event
        self.double_clicked.emit()

    def set_active(self, value):
        """Highlight the active trace using the current Qt theme."""
        self.active = bool(value)
        self.update()



class TraceWidget(QtWidgets.QWidget):
    """Display one trace with engineering axes and tracker."""

    activated = QtCore.pyqtSignal(int)
    marker_delete_requested = QtCore.pyqtSignal(object)

    def __init__(self, model, tid):
        """Create one trace widget."""
        super().__init__()
        self.model = model
        self.tid = tid
        self.items = []
        self.intersection_markers = []
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.label = VerticalTraceLabel(model.traces[tid].name)
        self.label.clicked.connect(lambda: self.activated.emit(tid))
        layout.addWidget(self.label)
        self.bottom = EngineeringAxisItem("bottom")
        self.left = EngineeringAxisItem("left")
        self.view_box = AxisZoomViewBox()
        self.plot = pg.PlotWidget(
            viewBox=self.view_box,
            axisItems={"bottom": self.bottom, "left": self.left},
        )
        layout.addWidget(self.plot)
        self.last_mouse_position = None
        self.mouse_proxy = pg.SignalProxy(
            self.plot.scene().sigMouseMoved,
            rateLimit=60,
            slot=self.remember_mouse_position,
        )
        self.tracker = WaveformTracker(self.plot)
        self.marker_controller = MarkerController(self.plot, grab_radius=5.0)
        self.marker_controller.marker_edit_requested.connect(
            lambda marker: marker.edit_value()
        )
        self.marker_controller.marker_delete_requested.connect(
            self.marker_delete_requested.emit
        )
        self.refresh()

    def remember_mouse_position(self, event):
        """Remember the latest cursor coordinate inside this plot."""
        if not event:
            return
        scene_position = event[0]
        view_box = self.plot.getViewBox()
        if view_box.sceneBoundingRect().contains(scene_position):
            self.last_mouse_position = view_box.mapSceneToView(scene_position)

    def marker_value_near_mouse(self, orientation):
        """Return a marker value at the cursor or plot-view center."""
        if self.last_mouse_position is not None:
            if orientation == "h":
                return float(self.last_mouse_position.y())
            return float(self.last_mouse_position.x())
        x_range, y_range = self.plot.viewRange()
        values = y_range if orientation == "h" else x_range
        return float(sum(values) / 2.0)

    def ensure_legend(self, trace):
        """Create or clear the native pyqtgraph LegendItem deterministically."""
        legend = self.plot.plotItem.legend
        if not trace.legend_visible:
            if legend is not None:
                legend.scene().removeItem(legend)
                self.plot.plotItem.legend = None
            return None
        if legend is None:
            legend = self.plot.addLegend(
                offset=None,
                labelTextSize=f"{trace.legend_font_size}pt",
                frame=False,
            )
        else:
            legend.clear()
        return legend

    def refresh(self):
        """Refresh curves and display settings."""
        for item in self.items:
            self.plot.removeItem(item)
        self.items = []
        trace = self.model.traces[self.tid]
        legend = self.ensure_legend(trace)
        for name, x_values, y_values, style in self.model.visible_curves(
            self.tid
        ):
            legend_name = style.legend_name or name
            if style.line_style == 5:
                item = self.plot.plot(
                    x_values,
                    y_values,
                    pen=None,
                    symbol="o",
                    symbolSize=max(4.0, 2.5 * style.width),
                    symbolPen=pg.mkPen(style.color, width=style.width),
                    symbolBrush=pg.mkBrush(style.color),
                )
            else:
                item = self.plot.plot(
                    x_values,
                    y_values,
                    pen=pg.mkPen(
                        style.color,
                        width=style.width,
                        style=PENS[style.line_style],
                    ),
                    symbol="o" if style.show_points else None,
                    symbolSize=max(4.0, 2.5 * style.width),
                    symbolPen=pg.mkPen(style.color, width=style.width),
                    symbolBrush=pg.mkBrush(style.color),
                )
            self.items.append(item)
            if legend is not None:
                legend.addItem(item, legend_name)
        self.apply_plot_theme(trace.background)
        self.tracker.curves = self.items
        for marker in self.intersection_markers:
            marker.curves = self.items
            marker.set_font_size(trace.marker_label_size)
            marker.set_engineering(trace.engineering_axes)
            marker.update()
        self.tracker.set_engineering(trace.engineering_axes)
        self.tracker.set_enabled(trace.cursor_enabled)
        self.tracker.set_interpolation(trace.tracker_interpolation)
        self.tracker.set_measurement_mode(trace.marker_mode)
        self.tracker.apply_settings(
            trace.marker_label_size, trace.marker_offset
        )
        self.bottom.engineering = trace.engineering_axes
        self.left.engineering = trace.engineering_axes
        label = {"font-size": f"{trace.axis_label_size}pt"}
        self.plot.setLabel("bottom", trace.x_name, units=trace.x_unit, **label)
        self.plot.setLabel("left", trace.y_name, units=trace.y_unit, **label)
        font = QtGui.QFont()
        font.setPointSize(trace.axis_tick_size)
        self.bottom.setTickFont(font)
        self.left.setTickFont(font)
        self.plot.setLogMode(trace.x_log, trace.y_log)
        self.plot.showGrid(
            x=trace.grid_enabled, y=trace.grid_enabled, alpha=0.3
        )
        foreground = foreground_for(trace.background)
        self.plot.setTitle(trace.title, color=foreground)
        self.apply_plot_theme(trace.background)

    def apply_plot_theme(self, background, queued = True):
        """Apply the centralized, consistent plot appearance policy."""
        foreground = apply_plot_appearance(self, background)
        if queued:
            QtCore.QTimer.singleShot(
                0, lambda: apply_plot_appearance(self, background)
            )
        return foreground


class MainWindow(QtWidgets.QMainWindow):
    """Coordinate UI, model, plots, aliases, and IPython."""

    def __init__(self, options):
        """Build and connect the complete application."""
        super().__init__()
        self.ui = UiMainWindow()
        self.ui.setup_ui(self)
        self.model = ProjectModel(options, self)
        self.console = IPythonConsole(self.model)
        self.script_loader = UserScriptLoader(self.console)
        shell = self.console.kernel_manager.kernel.shell
        shell.push({"load_python_file": self.load_python_file})
        self.ui.console_layout.addWidget(self.console)
        self.widgets = {}
        self.tab_views = {}
        self.tree_states = {}
        self.tree_mode_index = 0
        self.skip_history_on_close = False
        self.last_selected_file_id = None
        self._tree_refresh_pending = False
        self.tree_model = FileGraphTreeModel(self.model, self)
        self.tree_delegate = FileGraphDelegate(self.ui.file_tree)
        self.ui.file_tree.setModel(self.tree_model)
        self.ui.file_tree.setItemDelegate(self.tree_delegate)
        self.ui.file_tree.viewport().installEventFilter(self)
        self.ui.file_tree.setContextMenuPolicy(
            QtCore.Qt.ContextMenuPolicy.CustomContextMenu
        )
        self._connect()
        self._configure()
        self.rebuild_traces()
        self.rebuild_tree()

    def eventFilter(self, watched, event):
        """Handle documented Ctrl+wheel gestures in the file tree."""
        viewport = self.ui.file_tree.viewport()
        if watched is viewport and event.type() == QtCore.QEvent.Type.Wheel:
            index = self.ui.file_tree.indexAt(event.position().toPoint())
            if index.isValid() and self.tree_delegate.editorEvent(
                event, self.tree_model, None, index
            ):
                event.accept()
                return True
        return super().eventFilter(watched, event)

    def _configure(self):
        """Configure compact virtualized tree columns."""
        tree = self.ui.file_tree
        header = tree.header()
        header.setSectionsMovable(False)
        header.setStretchLastSection(False)
        for column in range(self.tree_model.columnCount()):
            header.setSectionResizeMode(
                column, QtWidgets.QHeaderView.ResizeMode.Interactive
            )
        widths = [112, 88, 30, 30, 30, 42, 74]
        for column, width in enumerate(widths):
            tree.setColumnWidth(column, width)
        tree.setMinimumWidth(sum(widths) + 28)
        self.ui.file_dock.setMinimumWidth(sum(widths) + 42)

    def _connect(self):
        """Connect model and actions."""
        m = self.model
        u = self.ui
        m.files_changed.connect(self.schedule_tree_refresh)
        m.traces_changed.connect(self.rebuild_traces)
        m.trace_changed.connect(self.refresh_trace)
        m.active_trace_changed.connect(self.activate)
        m.tabs_changed.connect(self.rebuild_traces)
        m.active_tab_changed.connect(self.activate_tab)
        m.tree_leaf_requested.connect(self.open_tree_leaf)
        m.marker_requested.connect(self.add_intersection_marker)
        u.open_action.triggered.connect(self.open_files)
        u.delete_file_action.triggered.connect(self.delete_file)
        u.clear_file_action.triggered.connect(self.delete_file)
        u.clear_all_files_action.triggered.connect(m.clear_all_files)
        u.reload_action.triggered.connect(self.reload_data)
        u.load_script_action.triggered.connect(self.choose_python_file)
        u.load_palette_action.triggered.connect(self.load_palette)
        u.history_action.triggered.connect(self.show_history)
        u.open_history_action.triggered.connect(self.open_history_file)
        u.export_action.triggered.connect(
            lambda: self.export([m.active_trace_id])
        )
        u.export_all_action.triggered.connect(
            lambda: self.export(m.trace_order)
        )
        u.export_plot_action.triggered.connect(self.export_plots)
        u.exit_action.triggered.connect(self.close_with_history)
        u.exit_without_history_action.triggered.connect(
            self.close_without_history
        )
        u.fit_action.triggered.connect(self.fit_active_trace)
        u.add_trace_action.triggered.connect(m.add_trace)
        u.add_tab_action.triggered.connect(self.add_tab)
        u.rename_tab_action.triggered.connect(self.rename_tab)
        u.close_tab_action.triggered.connect(self.close_tab)
        u.trace_tabs.currentChanged.connect(self.tab_changed)
        u.trace_tabs.tabCloseRequested.connect(self.close_tab_index)
        u.delete_trace_action.triggered.connect(
            lambda: m.remove_trace(m.active_trace_id)
        )
        u.display_settings_action.triggered.connect(self.settings)
        u.toggle_files_action.toggled.connect(u.file_dock.setVisible)
        u.toggle_traces_action.toggled.connect(u.trace_dock.setVisible)
        u.toggle_console_action.toggled.connect(u.console_host.setVisible)
        u.grid_all_action.triggered.connect(self.grid_all)
        u.link_x_all_action.triggered.connect(self.link_all)
        u.tracker_action.triggered.connect(self.trackers_all)
        u.interpolate_action.triggered.connect(self.toggle_interpolation)
        u.marker_h_action.triggered.connect(
            lambda: self.place_intersection_marker("h")
        )
        u.marker_v_action.triggered.connect(
            lambda: self.place_intersection_marker("v")
        )
        u.ab_horizontal_action.triggered.connect(
            lambda: self.set_marker_mode("horizontal")
        )
        u.ab_vertical_action.triggered.connect(
            lambda: self.set_marker_mode("vertical")
        )
        u.legend_action.triggered.connect(self.toggle_legend)
        u.edit_legend_action.triggered.connect(self.edit_legend_names)
        u.marker_a_action.triggered.connect(lambda: self.marker("A"))
        u.marker_b_action.triggered.connect(lambda: self.marker("B"))
        u.clear_ab_action.triggered.connect(self.clear_ab_markers)
        u.clear_markers_action.triggered.connect(self.clear_all_markers)
        u.delete_marker_action.triggered.connect(self.delete_selected_marker)
        u.expand_tree_action.triggered.connect(
            lambda: self.set_tree_mode("all")
        )
        u.collapse_tree_action.triggered.connect(
            lambda: self.set_tree_mode("none")
        )
        u.visible_tree_action.triggered.connect(
            lambda: self.set_tree_mode("visible")
        )
        u.cycle_tree_action.triggered.connect(self.cycle_tree_mode)
        u.file_tree.expanded.connect(self.tree_item_expanded)
        u.file_tree.collapsed.connect(self.tree_item_collapsed)
        u.file_tree.selectionModel().currentChanged.connect(
            self.remember_selected_file
        )
        self.tree_model.action_requested.connect(self.tree_action)
        u.file_tree.customContextMenuRequested.connect(
            self.file_tree_context_menu
        )
        u.show_file_columns_action.triggered.connect(
            lambda: self.toggle_selected_file(True)
        )
        u.hide_file_columns_action.triggered.connect(
            lambda: self.toggle_selected_file(False)
        )
        u.help_action.triggered.connect(self.show_help)

    def rebuild_traces(self):
        """Rebuild tab pages, plot widgets, and the active-tab trace table."""
        current_tab = self.model.active_tab_id
        tabs = self.ui.trace_tabs
        tabs.blockSignals(True)
        while tabs.count():
            page = tabs.widget(0)
            for widget in page.findChildren(TraceWidget):
                widget.marker_controller.shutdown()
            tabs.removeTab(0)
            page.deleteLater()
        self.widgets = {}
        self.tab_views = {}
        for tab_id in self.model.tab_order:
            page = QtWidgets.QWidget()
            page_layout = QtWidgets.QVBoxLayout(page)
            page_layout.setContentsMargins(0, 0, 0, 0)
            splitter = QtWidgets.QSplitter(
                QtCore.Qt.Orientation.Vertical
            )
            splitter.setChildrenCollapsible(False)
            page_layout.addWidget(splitter)
            self.tab_views[tab_id] = (page, splitter)
            tabs.addTab(page, self.model.tabs[tab_id])
        for tid in self.model.trace_order:
            trace = self.model.traces[tid]
            if trace.tab_id not in self.tab_views:
                trace.tab_id = self.model.tab_order[0]
            widget = TraceWidget(self.model, tid)
            widget.activated.connect(self.model.set_active_trace)
            widget.marker_delete_requested.connect(
                lambda marker, w=widget: self.remove_intersection_marker(
                    w, marker
                )
            )
            widget.label.double_clicked.connect(
                lambda t=tid: self.settings(t)
            )
            self.widgets[tid] = widget
            self.tab_views[trace.tab_id][1].addWidget(widget)
            widget.setMinimumHeight(90)
        active_index = self.model.tab_order.index(current_tab)
        tabs.setCurrentIndex(active_index)
        tabs.blockSignals(False)
        self.rebuild_trace_table()
        self.activate(self.model.active_trace_id)
        self.apply_links()

    def rebuild_trace_table(self):
        """Show trace controls for the currently active tab only."""
        table = self.ui.trace_table
        trace_ids = [
            tid for tid in self.model.trace_order
            if self.model.traces[tid].tab_id == self.model.active_tab_id
        ]
        table.setRowCount(len(trace_ids))
        try:
            table.itemChanged.disconnect(self.trace_table_item_changed)
        except TypeError:
            pass
        table.itemChanged.connect(self.trace_table_item_changed)
        choices = ["none", "all"] + [str(x) for x in trace_ids]
        for row, tid in enumerate(trace_ids):
            trace = self.model.traces[tid]
            item = QtWidgets.QTableWidgetItem(trace.name)
            item.setData(QtCore.Qt.ItemDataRole.UserRole, tid)
            table.setItem(row, 0, item)
            delete = QtWidgets.QToolButton()
            delete.setText("x")
            delete.clicked.connect(
                lambda _checked=False, t=tid: self.model.remove_trace(t)
            )
            table.setCellWidget(row, 1, delete)
            for column, attribute in ((2, "x_link"), (3, "y_link")):
                combo = QtWidgets.QComboBox()
                combo.addItems(choices)
                combo.setCurrentText(getattr(trace, attribute))
                combo.currentTextChanged.connect(
                    lambda value, t=tid, a=attribute: self.option(
                        t, **{a: value}
                    )
                )
                table.setCellWidget(row, column, combo)
            fit = QtWidgets.QToolButton()
            fit.setText("Fit")
            fit.clicked.connect(
                lambda _checked=False, t=tid: self.widgets[t].plot.autoRange()
            )
            table.setCellWidget(row, 4, fit)
            cursor = QtWidgets.QComboBox()
            cursor.addItems(["Off", "Sampled", "Interpolated"])
            if not trace.cursor_enabled:
                cursor.setCurrentIndex(0)
            else:
                cursor.setCurrentIndex(
                    2 if trace.tracker_interpolation else 1
                )
            cursor.currentIndexChanged.connect(
                lambda index, t=tid: self.option(
                    t,
                    cursor_enabled=index > 0,
                    tracker_interpolation=index == 2,
                )
            )
            table.setCellWidget(row, 5, cursor)
            legend = QtWidgets.QCheckBox()
            legend.setChecked(trace.legend_visible)
            legend.toggled.connect(
                lambda value, t=tid: self.option(
                    t, legend_visible=value
                )
            )
            table.setCellWidget(row, 6, legend)
            log = QtWidgets.QComboBox()
            log.addItems(["Linear", "Log X", "Log Y", "Log X/Y"])
            log.setCurrentIndex(
                (1 if trace.x_log else 0) + (2 if trace.y_log else 0)
            )
            log.currentIndexChanged.connect(
                lambda index, t=tid: self.option(
                    t, x_log=bool(index & 1), y_log=bool(index & 2)
                )
            )
            table.setCellWidget(row, 7, log)
            grid = QtWidgets.QCheckBox()
            grid.setChecked(trace.grid_enabled)
            grid.toggled.connect(
                lambda value, t=tid: self.option(t, grid_enabled=value)
            )
            table.setCellWidget(row, 8, grid)
            title = QtWidgets.QTableWidgetItem(trace.title)
            title.setFlags(title.flags() | QtCore.Qt.ItemFlag.ItemIsEditable)
            title.setData(QtCore.Qt.ItemDataRole.UserRole, tid)
            table.setItem(row, 9, title)
        for column in (1, 4, 5, 6, 7, 8):
            table.resizeColumnToContents(column)
        table.setColumnWidth(9, 220)

    def edit_trace_title(self, item):
        """Edit the selected trace title from the trace-name cell."""
        if item.column() not in (0, 9):
            return
        trace_id = item.data(QtCore.Qt.ItemDataRole.UserRole)
        trace = self.model.traces[trace_id]
        title, accepted = QtWidgets.QInputDialog.getText(
            self,
            "Trace title",
            "Plot title:",
            text=trace.title,
        )
        if accepted:
            trace.title = title
            self.model.trace_changed.emit(trace_id)

    def trace_table_item_changed(self, item):
        """Apply direct edits from the trace table title column."""
        if item.column() != 9:
            return
        trace_id = item.data(QtCore.Qt.ItemDataRole.UserRole)
        if trace_id not in self.model.traces:
            return
        title = item.text()
        if title != self.model.traces[trace_id].title:
            self.model.traces[trace_id].title = title
            self.model.trace_changed.emit(trace_id)

    def option(self, tid, **changes):
        """Update trace settings."""
        for k, v in changes.items():
            setattr(self.model.traces[tid], k, v)
        self.model.trace_changed.emit(tid)
        self.apply_links()

    def apply_links(self):
        """Apply direct or all-axis links."""
        if not self.widgets:
            return
        master = self.model.trace_order[0]
        for tid, w in self.widgets.items():
            trace = self.model.traces[tid]
            w.plot.setXLink(None)
            w.plot.setYLink(None)
            for axis, value in (("X", trace.x_link), ("Y", trace.y_link)):
                target = (
                    master
                    if value == "all"
                    else int(value) if value.isdigit() else None
                )
                if target in self.widgets and target != tid:
                    getattr(w.plot, f"set{axis}Link")(
                        self.widgets[target].plot
                    )

    def activate(self, tid):
        """Highlight the active trace and select its owning tab."""
        if tid in self.model.traces:
            tab_id = self.model.traces[tid].tab_id
            if tab_id != self.model.active_tab_id:
                self.model.set_active_tab(tab_id)
        for key, widget in self.widgets.items():
            widget.label.set_active(key == tid)
        self.rebuild_trace_table()
        self.schedule_tree_refresh()

    def refresh_trace(self, tid):
        """Refresh one trace."""
        if tid in self.widgets:
            self.widgets[tid].refresh()
        if tid == self.model.active_trace_id:
            self.schedule_tree_refresh()

    def schedule_tree_refresh(self):
        """Coalesce repeated model signals into one tree refresh."""
        if self._tree_refresh_pending:
            return
        self._tree_refresh_pending = True
        QtCore.QTimer.singleShot(0, self.refresh_tree_model)

    def refresh_tree_model(self):
        """Reset lightweight tree nodes and restore expansion state."""
        self._tree_refresh_pending = False
        trace_id = self.model.active_trace_id
        if trace_id not in self.model.traces:
            return
        self.tree_model.rebuild(trace_id)
        tree = self.ui.file_tree
        state = self.current_tree_state()
        for row in range(self.tree_model.rowCount()):
            index = self.tree_model.index(row, 0)
            payload = index.data(QtCore.Qt.ItemDataRole.UserRole)
            tree.setFirstColumnSpanned(row, QtCore.QModelIndex(), True)
            tree.setExpanded(index, payload in state)

    def rebuild_tree(self):
        """Compatibility entry point for a scheduled virtual-tree refresh."""
        self.schedule_tree_refresh()

    def current_tree_state(self):
        """Return remembered leaves for the current tab and trace."""
        key = (self.model.active_tab_id, self.model.active_trace_id)
        return self.tree_states.setdefault(key, set())

    def tree_item_expanded(self, index):
        """Remember one expanded top-level leaf."""
        if index.parent().isValid():
            return
        payload = index.data(QtCore.Qt.ItemDataRole.UserRole)
        if payload:
            self.current_tree_state().add(payload)

    def tree_item_collapsed(self, index):
        """Remember one collapsed top-level leaf."""
        if index.parent().isValid():
            return
        payload = index.data(QtCore.Qt.ItemDataRole.UserRole)
        self.current_tree_state().discard(payload)

    def set_tree_mode(self, mode):
        """Expand all, none, or only leaves used by the active trace."""
        state = self.current_tree_state()
        state.clear()
        trace = self.model.traces[self.model.active_trace_id]
        if mode == "all":
            state.update(("file", file_id) for file_id in self.model.files)
            state.add(("calculated", trace.uid))
        elif mode == "visible":
            for file_id, styles in trace.styles.items():
                if any(style.is_y for style in styles.values()):
                    state.add(("file", file_id))
            if any(graph.visible for graph in trace.graphs):
                state.add(("calculated", trace.uid))
        self.schedule_tree_refresh()

    def cycle_tree_mode(self):
        """Cycle all expanded, all collapsed, and visible-only leaves."""
        modes = ("all", "none", "visible")
        self.set_tree_mode(modes[self.tree_mode_index])
        self.tree_mode_index = (self.tree_mode_index + 1) % len(modes)

    def open_tree_leaf(self, kind, object_id, trace_id):
        """Remember a leaf requested by file loading or add_graph()."""
        if trace_id not in self.model.traces:
            return
        tab_id = self.model.traces[trace_id].tab_id
        payload = (
            ("file", object_id)
            if kind == "file"
            else ("calculated", trace_id)
        )
        self.tree_states.setdefault((tab_id, trace_id), set()).add(payload)
        if trace_id == self.model.active_trace_id:
            self.schedule_tree_refresh()

    def tree_action(self, payload, column):
        """Handle color and detailed line-style dialogs."""
        if not payload or payload[0] not in ("source", "graph"):
            return
        if payload[0] == "source":
            style = self.model.traces[self.model.active_trace_id].styles[
                payload[1]
            ][payload[2]]
        else:
            _, style = self.model.find_graph(payload[1])
        if column == 2:
            dialog = PaletteDialog(self.model.palette, self)
            if not dialog.exec():
                return
            changes = {"color": dialog.selected_color}
        elif column == 6:
            dialog = LineStyleDialog(
                style.line_style, style.show_points, self
            )
            if not dialog.exec():
                return
            line_style, show_points = dialog.values()
            changes = {
                "line_style": line_style,
                "show_points": show_points,
            }
        else:
            return
        if payload[0] == "source":
            self.model.set_column_style(payload[1], payload[2], **changes)
        else:
            self.model.set_graph_style(payload[1], **changes)

    def add_tab(self):
        """Create a new tab and its first trace atomically."""
        self.model.add_tab()

    def rename_tab(self):
        """Rename the current trace tab."""
        old = self.model.tabs[self.model.active_tab_id]
        name, accepted = QtWidgets.QInputDialog.getText(
            self, "Rename trace tab", "Tab name", text=old
        )
        if accepted:
            self.model.rename_tab(self.model.active_tab_id, name)

    def close_tab(self):
        """Close the current tab and retain its traces in another tab."""
        self.model.remove_tab(self.model.active_tab_id)

    def close_tab_index(self, index):
        """Close a tab selected through its close button."""
        if 0 <= index < len(self.model.tab_order):
            self.model.remove_tab(self.model.tab_order[index])

    def tab_changed(self, index):
        """Activate a tab; signal handlers perform one UI refresh."""
        if 0 <= index < len(self.model.tab_order):
            self.model.set_active_tab(self.model.tab_order[index])

    def activate_tab(self, tab_id):
        """Synchronize the tab widget without rebuilding tab pages."""
        if tab_id not in self.model.tab_order:
            return
        target = self.model.tab_order.index(tab_id)
        blocker = QtCore.QSignalBlocker(self.ui.trace_tabs)
        self.ui.trace_tabs.setCurrentIndex(target)
        del blocker
        self.rebuild_trace_table()
        self.schedule_tree_refresh()

    def settings(self, tid=None):
        """Open axis and marker settings."""
        tid = (
            self.model.active_trace_id
            if tid is None or isinstance(tid, bool)
            else tid
        )
        dialog = DisplaySettingsDialog(self.model.traces[tid], self)
        if dialog.exec():
            for k, v in dialog.values().items():
                setattr(self.model.traces[tid], k, v)
            self.model.trace_changed.emit(tid)

    def marker(self, name):
        """Place marker in active trace."""
        self.widgets[self.model.active_trace_id].tracker.place(name)

    def grid_all(self):
        """Toggle all grids."""
        value = not self.model.traces[self.model.active_trace_id].grid_enabled
        for tid in self.model.trace_order:
            self.option(tid, grid_enabled=value)
        self.rebuild_trace_table()

    def link_all(self):
        """Toggle all X links."""
        value = self.model.traces[self.model.active_trace_id].x_link != "all"
        for trace in self.model.traces.values():
            trace.x_link = "all" if value else "none"
        self.rebuild_traces()

    def trackers_all(self):
        """Toggle trackers."""
        value = not self.model.traces[
            self.model.active_trace_id
        ].cursor_enabled
        for trace in self.model.traces.values():
            trace.cursor_enabled = value
        self.rebuild_traces()

    def toggle_interpolation(self):
        """Toggle optional interpolated tracking for the active trace."""
        trace = self.model.traces[self.model.active_trace_id]
        trace.tracker_interpolation = not trace.tracker_interpolation
        self.model.trace_changed.emit(trace.uid)

    def place_intersection_marker(self, orientation):
        """Place an intersection marker immediately near the mouse cursor."""
        trace_id = self.model.active_trace_id
        widget = self.widgets[trace_id]
        value = widget.marker_value_near_mouse(orientation)
        function = (
            self.model.add_marker_h
            if orientation == "h"
            else self.model.add_marker_v
        )
        function(value, trace=trace_id)

    def add_intersection_marker(self, orientation, value, trace_id):
        """Create a movable line and labels at every curve crossing."""
        if trace_id not in self.widgets:
            return
        widget = self.widgets[trace_id]
        marker = IntersectionMarker(
            widget.plot, orientation, value, widget.items
        )
        trace = self.model.traces[trace_id]
        marker.set_font_size(trace.marker_label_size)
        marker.set_engineering(trace.engineering_axes)
        marker.set_text_theme(foreground_for(trace.background))
        widget.marker_controller.add_marker(marker)
        widget.intersection_markers.append(marker)

    @staticmethod
    def remove_intersection_marker(widget, marker):
        """Unregister one H/V marker, then remove all owned graphics."""
        if marker not in widget.intersection_markers:
            return
        widget.marker_controller.remove_marker(marker)
        widget.intersection_markers.remove(marker)
        widget.plot.removeItem(marker.line)
        widget.plot.removeItem(marker.points)
        for label in marker.labels:
            widget.plot.removeItem(label)

    def clear_ab_markers(self):
        """Clear only A/B markers and retain H/V intersection markers."""
        for widget in self.widgets.values():
            widget.tracker.clear()

    def clear_all_markers(self):
        """Clear every marker in the active trace only."""
        widget = self.widgets.get(self.model.active_trace_id)
        if widget is None:
            return
        widget.tracker.clear()
        for marker in list(widget.intersection_markers):
            self.remove_intersection_marker(widget, marker)

    def delete_selected_marker(self):
        """Route Backspace to the active trace's MarkerController."""
        widget = self.widgets.get(self.model.active_trace_id)
        if widget is not None:
            widget.marker_controller.delete_selected()

    def set_marker_mode(self, mode):
        """Select horizontal or vertical A/B measurement mode."""
        trace = self.model.traces[self.model.active_trace_id]
        trace.marker_mode = mode
        self.model.trace_changed.emit(trace.uid)

    def choose_python_file(self):
        """Choose and execute one Python file in the IPython namespace."""
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Load Python file", "", "Python (*.py);;All (*)"
        )
        if filename:
            self.load_python_file(filename)

    def load_python_file(self, filename):
        """Execute a Python file in the live console namespace."""
        return self.script_loader.load(filename)

    def reload_data(self):
        """Reload the selected file, or all files when none is selected."""
        file_id = self.selected_file_id()
        try:
            if file_id is None:
                self.model.reload_all_files()
            else:
                self.model.reload_file(file_id)
            self.script_loader.reload_all()
        except Exception as error:
            QtWidgets.QMessageBox.warning(self, "Reload", str(error))

    def remember_selected_file(self, current, previous):
        """Retain the selected file when focus moves to a trace widget."""
        del previous
        payload = current.data(QtCore.Qt.ItemDataRole.UserRole)
        if payload and payload[0] in ("file", "source"):
            self.last_selected_file_id = payload[1]

    def selected_file_id(self):
        """Return the file owning the selected tree node."""
        index = self.ui.file_tree.currentIndex()
        payload = index.data(QtCore.Qt.ItemDataRole.UserRole)
        if not payload:
            return self.last_selected_file_id
        if payload[0] in ("file", "source"):
            return payload[1]
        return self.last_selected_file_id

    def toggle_selected_file(self, visible):
        """Show or hide all non-X columns of the selected file."""
        file_id = self.selected_file_id()
        if file_id is not None:
            self.model.set_file_columns_visible(file_id, visible)

    def file_tree_context_menu(self, position):
        """Show graph save/delete and source bulk-visibility actions."""
        index = self.ui.file_tree.indexAt(position)
        payload = index.data(QtCore.Qt.ItemDataRole.UserRole)
        if not payload:
            return
        menu = QtWidgets.QMenu(self)
        if payload[0] == "graph":
            graph_id = payload[1]
            trace_id, graph = self.model.find_graph(graph_id)
            menu.addAction(
                "Delete graph", lambda: self.model.remove_graph(graph_id)
            )
            menu.addAction(
                "Save graph...", lambda: self.save_one_graph(graph)
            )
            menu.addAction(
                "Save trace...", lambda: self.export([trace_id])
            )
        elif payload[0] in ("file", "source"):
            file_id = payload[1]
            menu.addAction(
                "Show all non-X columns",
                lambda: self.model.set_file_columns_visible(file_id, True),
            )
            menu.addAction(
                "Hide all non-X columns",
                lambda: self.model.set_file_columns_visible(file_id, False),
            )
            menu.addAction(
                "Reload file", lambda: self.model.reload_file(file_id)
            )
        if not menu.isEmpty():
            menu.exec(self.ui.file_tree.viewport().mapToGlobal(position))

    def save_one_graph(self, graph):
        """Choose a filename and save one calculated graph."""
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save graph", f"{graph.name}.csv", "CSV (*.csv);;TSV (*.tsv)"
        )
        if filename:
            self.model.save_graph(graph, filename)

    @staticmethod
    def _legend_position(widget):
        """Return absolute and size-independent legend coordinates."""
        legend = widget.plot.plotItem.legend
        if legend is None:
            return None
        position = legend.pos()
        bounds = widget.plot.plotItem.boundingRect()
        width = max(1.0, bounds.width())
        height = max(1.0, bounds.height())
        return {
            "position": [position.x(), position.y()],
            "relative": [position.x() / width, position.y() / height],
        }

    @staticmethod
    def _restore_legend_position(widget, saved):
        """Restore a legend in current PlotItem coordinates."""
        legend = widget.plot.plotItem.legend
        if legend is None or saved is None:
            return
        if isinstance(saved, dict) and saved.get("relative"):
            bounds = widget.plot.plotItem.boundingRect()
            relative = saved["relative"]
            position = (
                float(relative[0]) * max(1.0, bounds.width()),
                float(relative[1]) * max(1.0, bounds.height()),
            )
        elif isinstance(saved, dict):
            position = tuple(saved.get("position", (0, 0)))
        else:
            position = tuple(saved)
        legend.setPos(*position)

    def capture_view_state(self):
        """Capture ranges, markers, labels, legends, and splitter sizes."""
        traces = {}
        for trace_id, widget in self.widgets.items():
            tracker = widget.tracker
            traces[str(trace_id)] = {
                "range": widget.plot.viewRange(),
                "splitter": self.tab_views[
                    self.model.traces[trace_id].tab_id
                ][1].sizes(),
                "ab_points": tracker.points,
                "ab_labels": {
                    key: {
                        "position": [label.pos().x(), label.pos().y()],
                        "alignment": label.alignment,
                    }
                    for key, label in tracker.labels.items()
                },
                "result_alignment": tracker.result.alignment,
                "result": [
                    tracker.result.pos().x(), tracker.result.pos().y()
                ],
                "measurement_group": tracker.helper_state(),
                "legend_pos": self._legend_position(widget),
                "markers": [
                    {
                        "orientation": item.orientation,
                        "value": item.value,
                        "labels": [
                            {
                                "position": [label.pos().x(), label.pos().y()],
                                "alignment": label.alignment,
                            }
                            for label in item.labels
                        ],
                    }
                    for item in widget.intersection_markers
                ],
            }
        return {
            "traces": traces,
            "tree_states": self.json_tree_states(),
            "gui": self.capture_gui_state(),
        }

    def capture_gui_state(self):
        """Capture window, docks, console, and central splitter geometry."""
        def encode(value):
            return bytes(value.toBase64()).decode("ascii")
        return {
            "geometry": encode(self.saveGeometry()),
            "window_state": encode(self.saveState()),
            "main_splitter": self.ui.main_splitter.sizes(),
            "file_dock_visible": self.ui.file_dock.isVisible(),
            "trace_dock_visible": self.ui.trace_dock.isVisible(),
            "console_visible": self.ui.console_host.isVisible(),
        }

    def restore_gui_state(self, state):
        """Restore dimensions before position-dependent plot graphics."""
        gui = state.get("gui", {})
        def decode(text):
            data = text.encode("ascii")
            return QtCore.QByteArray.fromBase64(data)
        if gui.get("geometry"):
            self.restoreGeometry(decode(gui["geometry"]))
        if gui.get("window_state"):
            self.restoreState(decode(gui["window_state"]))
        self.ui.file_dock.setVisible(gui.get("file_dock_visible", True))
        self.ui.trace_dock.setVisible(gui.get("trace_dock_visible", True))
        self.ui.console_host.setVisible(gui.get("console_visible", True))
        sizes = gui.get("main_splitter")
        if sizes:
            self.ui.main_splitter.setSizes(sizes)
        self.ui.toggle_files_action.setChecked(
            self.ui.file_dock.isVisible()
        )
        self.ui.toggle_traces_action.setChecked(
            self.ui.trace_dock.isVisible()
        )
        self.ui.toggle_console_action.setChecked(
            self.ui.console_host.isVisible()
        )


    def json_tree_states(self):
        """Convert tuple-keyed tree expansion state to JSON values."""
        return [
            {
                "tab": key[0],
                "trace": key[1],
                "items": [list(item) for item in values],
            }
            for key, values in self.tree_states.items()
        ]

    def restore_view_state(self, state):
        """Restore ranges and every persistent marker graphic."""
        self.tree_states = {
            (item["tab"], item["trace"]): {
                tuple(value) for value in item.get("items", [])
            }
            for item in state.get("tree_states", [])
        }
        for key, values in state.get("traces", {}).items():
            trace_id = int(key)
            if trace_id not in self.widgets:
                continue
            widget = self.widgets[trace_id]
            tab_id = self.model.traces[trace_id].tab_id
            sizes = values.get("splitter")
            if sizes:
                self.tab_views[tab_id][1].setSizes(sizes)
            QtWidgets.QApplication.processEvents()
            ranges = values.get("range")
            if ranges:
                widget.plot.setRange(
                    xRange=ranges[0], yRange=ranges[1], padding=0
                )
            tracker = widget.tracker
            tracker.points = {
                name: tuple(point)
                for name, point in values.get("ab_points", {}).items()
            }
            tracker._update_measurement()
            for name, saved in values.get("ab_labels", {}).items():
                if isinstance(saved, dict):
                    tracker.labels[name].setPos(*saved["position"])
                    tracker.labels[name].set_alignment(
                        saved.get("alignment", "left")
                    )
                else:
                    tracker.labels[name].setPos(*saved)
            tracker.result.setPos(*values.get("result", [0, 0]))
            tracker.result.set_alignment(
                values.get("result_alignment", "center")
            )
            tracker.restore_helper_state(
                values.get("measurement_group", [0, 0])
            )
            legend_position = values.get("legend_pos")
            self._restore_legend_position(widget, legend_position)
            QtCore.QTimer.singleShot(
                0,
                lambda w=widget, pos=legend_position:
                self._restore_legend_position(w, pos),
            )
            for marker in values.get("markers", []):
                self.add_intersection_marker(
                    marker["orientation"], marker["value"], trace_id
                )
                created = widget.intersection_markers[-1]
                for label, saved in zip(
                    created.labels, marker.get("labels", [])
                ):
                    if isinstance(saved, dict):
                        label.setPos(*saved["position"])
                        label.set_alignment(
                            saved.get("alignment", "left")
                        )
                    else:
                        label.setPos(*saved)

    def history_entry(self, name, description):
        """Build one complete named history entry."""
        return {
            "name": name or datetime.now().strftime("State %Y-%m-%d %H:%M"),
            "description": description,
            "saved": datetime.now().isoformat(timespec="seconds"),
            "model": capture_model(self.model),
            "view": self.capture_view_state(),
        }

    def show_history(self, filename=DEFAULT_HISTORY):
        """Search, save, and restore states in one JSON history file."""
        if isinstance(filename, bool) or filename is None:
            filename = DEFAULT_HISTORY
        entries = read_entries(filename)
        commands = self.console.command_history()
        commands.extend(self.script_loader.audit_log)
        traces = [
            (trace_id, self.model.traces[trace_id].name)
            for trace_id in self.model.trace_order
        ]
        dialog = HistoryDialog(entries, commands, traces, self)
        result = dialog.exec()
        if result == HistoryDialog.SAVE_CURRENT:
            entry = self.history_entry(
                dialog.name.text(),
                dialog.description.toPlainText(),
            )
            entry["ipython_code"] = dialog.selected_code()
            entry["python_sections"] = dialog.code_sections()
            entries.append(entry)
            write_entries(entries, filename)
        elif result == HistoryDialog.DELETE_SELECTED:
            selected = set(dialog.selected_indices)
            entries = [
                entry
                for index, entry in enumerate(entries)
                if index not in selected
            ]
            write_entries(entries, filename)
        elif result and dialog.selected_index is not None:
            entry = entries[dialog.selected_index]
            restore_model(self.model, entry["model"])
            sections = entry.get("python_sections")
            if sections is None:
                legacy = entry.get("ipython_code", "")
                if isinstance(legacy, list):
                    legacy = "\n".join(legacy)
                sections = {
                    "before_traces": "",
                    "traces": {
                        str(self.model.active_trace_id): legacy,
                    },
                }
            has_code = sections.get("before_traces", "").strip()
            has_code = has_code or any(
                code.strip() for code in sections.get("traces", {}).values()
            )
            if has_code:
                names = {
                    trace_id: trace.name
                    for trace_id, trace in self.model.traces.items()
                }
                code_dialog = HistoryCodeDialog(sections, names, self)
                if code_dialog.exec() == HistoryCodeDialog.RUN_CODE:
                    self.run_history_code(code_dialog.reviewed_sections())
            self.restore_calculated_graph_styles(entry["model"])
            view_state = entry.get("view", {})
            self.restore_gui_state(view_state)
            self.rebuild_traces()
            QtWidgets.QApplication.processEvents()
            self.restore_view_state(view_state)

    def restore_calculated_graph_styles(self, model_state):
        """Apply stored metadata after Python recreated calculated graphs."""
        saved_traces = {
            int(trace["uid"]): trace
            for trace in model_state.get("traces", [])
        }
        alias_changed = False
        for trace_id, trace in self.model.traces.items():
            saved_trace = saved_traces.get(trace_id)
            if saved_trace is None:
                continue
            by_name = {}
            for graph in trace.graphs:
                by_name.setdefault(graph.name, []).append(graph)
            trace.x_graph_id = None
            for saved in saved_trace.get("graph_styles", []):
                graph = self._match_calculated_graph(saved, by_name)
                if graph is None:
                    continue
                old_alias = graph.alias
                graph.name = str(saved.get("name", graph.name))
                graph.alias = str(saved.get("alias", graph.alias))
                graph.color = tuple(saved.get("color", graph.color))
                graph.width = max(0.5, float(
                    saved.get("width", graph.width)
                ))
                graph.line_style = int(
                    saved.get("line_style", graph.line_style)
                )
                graph.visible = bool(
                    saved.get("visible", graph.visible)
                )
                graph.show_points = bool(
                    saved.get("show_points", graph.show_points)
                )
                graph.legend_name = str(
                    saved.get("legend_name", graph.legend_name)
                )
                if saved.get("selected_as_x", False):
                    trace.x_graph_id = graph.uid
                alias_changed = alias_changed or old_alias != graph.alias
        if alias_changed:
            self.model.aliases_changed.emit()

    @staticmethod
    def _match_calculated_graph(saved, graphs_by_name):
        """Match by alias first, then name and duplicate occurrence."""
        candidates = graphs_by_name.get(saved.get("name", ""), [])
        alias = str(saved.get("alias", ""))
        if alias:
            for graph in candidates:
                if graph.alias == alias:
                    return graph
        occurrence = int(saved.get("occurrence", 0))
        if 0 <= occurrence < len(candidates):
            return candidates[occurrence]
        return None

    def run_history_code(self, sections):
        """Run setup once, then trace-owned code with each trace active."""
        shell = self.console.kernel_manager.kernel.shell
        before = sections.get("before_traces", "")
        try:
            if before.strip():
                shell.run_cell(before, store_history=True)
            for trace_id in self.model.trace_order:
                code = sections.get("traces", {}).get(str(trace_id), "")
                if not code.strip():
                    continue
                self.model.set_active_trace(trace_id)
                shell.run_cell(code, store_history=True)
        except Exception as error:
            QtWidgets.QMessageBox.warning(self, "History code", str(error))

    def open_history_file(self):
        """Choose an arbitrary JSON history file."""
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Open history", "", "JSON (*.json)"
        )
        if filename:
            self.show_history(filename)

    def autosave_history(self):
        """Append the closing state to the default history file."""
        entries = read_entries(DEFAULT_HISTORY)
        entry = self.history_entry("Last session", "Automatic save")
        commands = self.console.command_history()
        commands.extend(self.script_loader.audit_log)
        entry["ipython_code"] = commands
        entry["python_sections"] = {
            "before_traces": "",
            "traces": {
                str(self.model.active_trace_id): "\n".join(commands),
            },
        }
        entries.append(entry)
        write_entries(entries[-100:], DEFAULT_HISTORY)

    def show_help(self):
        """Open the complete tabbed help dialog."""
        from help_dialog import HelpDialog

        HelpDialog(self).exec()

    def open_files(self):
        """Open source files."""
        names, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self,
            "Open",
            "",
            "Data (*.csv *.tsv *.txt *.dat *.gz *.bz2 *.zip "
            "*.xz *.zst);;All (*)",
        )
        for name in names:
            self.open_file_with_retry(name)

    def open_file_with_retry(self, name):
        """Load a file and offer editable import settings on failure."""
        try:
            self.model.load_file(name)
            return
        except Exception as error:
            dialog = ImportSettingsDialog(
                self.model.options, name, error, self
            )
        if not dialog.exec():
            return
        try:
            for key, value in dialog.values().items():
                setattr(self.model.options, key, value)
            self.model.load_file(name)
        except Exception as error:
            QtWidgets.QMessageBox.warning(self, "Open", str(error))

    def delete_file(self):
        """Remove the selected source file or calculated graph safely."""
        index = self.ui.file_tree.currentIndex()
        if not index.isValid():
            return
        payload = index.data(QtCore.Qt.ItemDataRole.UserRole)
        if not payload:
            return
        kind = payload[0]
        if kind == "graph":
            self.model.remove_graph(payload[1])
        elif kind == "file":
            self.model.remove_file(payload[1])
        elif kind == "source":
            self.model.remove_file(payload[1])

    def load_palette(self):
        """Load CSV/TXT palette."""
        name, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Palette", "", "Palette (*.csv *.txt)"
        )
        if name:
            self.model.load_palette(name)

    def export(self, tids):
        """Export selected traces."""
        name, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export", "waveforms.csv", "CSV (*.csv);;TSV (*.tsv)"
        )
        if name:
            self.model.save_traces(tids, name)

    def toggle_legend(self):
        """Toggle the movable legend of the active trace."""
        trace = self.model.traces[self.model.active_trace_id]
        trace.legend_visible = not trace.legend_visible
        self.model.trace_changed.emit(trace.uid)

    def edit_legend_names(self):
        """Edit display names used by the active trace legend."""
        trace_id = self.model.active_trace_id
        entries = self.model.visible_curves(trace_id)
        if not entries:
            return
        labels = [style.legend_name or name for name, _, _, style in entries]
        text, accepted = QtWidgets.QInputDialog.getMultiLineText(
            self,
            "Legend names",
            "One name per visible graph. HTML sub/sup tags are supported:",
            "\n".join(labels),
        )
        if not accepted:
            return
        values = text.splitlines()
        for value, entry in zip(values, entries):
            entry[3].legend_name = value.strip()
        self.model.trace_changed.emit(trace_id)

    @staticmethod
    def _clip_segment(x0, y0, x1, y1, bounds):
        """Clip one segment to a rectangle using Liang-Barsky."""
        xmin, xmax, ymin, ymax = bounds
        dx = x1 - x0
        dy = y1 - y0
        low = 0.0
        high = 1.0
        for p_value, q_value in (
            (-dx, x0 - xmin),
            (dx, xmax - x0),
            (-dy, y0 - ymin),
            (dy, ymax - y0),
        ):
            if p_value == 0:
                if q_value < 0:
                    return None
                continue
            ratio = q_value / p_value
            if p_value < 0:
                low = max(low, ratio)
            else:
                high = min(high, ratio)
            if low > high:
                return None
        return (
            x0 + low * dx,
            y0 + low * dy,
            x0 + high * dx,
            y0 + high * dy,
        )

    @classmethod
    def _clipped_curve_data(cls, x_values, y_values, bounds):
        """Return clipped polylines separated by NaN values."""
        x_values = np.asarray(x_values, dtype=float)
        y_values = np.asarray(y_values, dtype=float)
        clipped_x = []
        clipped_y = []
        for index in range(max(0, len(x_values) - 1)):
            points = (
                x_values[index], y_values[index],
                x_values[index + 1], y_values[index + 1],
            )
            if not np.all(np.isfinite(points)):
                continue
            segment = cls._clip_segment(*points, bounds)
            if segment is None:
                continue
            x0, y0, x1, y1 = segment
            if clipped_x:
                clipped_x.append(np.nan)
                clipped_y.append(np.nan)
            clipped_x.extend((x0, x1))
            clipped_y.extend((y0, y1))
        return np.asarray(clipped_x), np.asarray(clipped_y)

    @classmethod
    def _prepare_export_curves(cls, widget):
        """Replace curves temporarily with clipped copies."""
        x_range, y_range = widget.plot.viewRange()
        bounds = (x_range[0], x_range[1], y_range[0], y_range[1])
        saved = []
        for item in widget.items:
            x_values, y_values = item.getData()
            if x_values is None or y_values is None:
                continue
            saved.append(
                (item, np.asarray(x_values).copy(),
                 np.asarray(y_values).copy())
            )
            pen = item.opts.get("pen")
            if pen is None:
                x_array = np.asarray(x_values, dtype=float)
                y_array = np.asarray(y_values, dtype=float)
                inside = (
                    np.isfinite(x_array)
                    & np.isfinite(y_array)
                    & (x_array >= bounds[0])
                    & (x_array <= bounds[1])
                    & (y_array >= bounds[2])
                    & (y_array <= bounds[3])
                )
                item.setData(x_array[inside], y_array[inside])
            else:
                clipped = cls._clipped_curve_data(
                    x_values, y_values, bounds
                )
                item.setData(*clipped)
        return saved

    @staticmethod
    def _restore_export_curves(saved):
        """Restore PlotDataItems after success or failure."""
        for item, x_values, y_values in saved:
            item.setData(x_values, y_values)

    @classmethod
    def svg_for_pdf(cls, widget, background):
        """Export vector output with curves clipped to the data rectangle."""
        del background
        saved = cls._prepare_export_curves(widget)
        try:
            widget.plot.scene().update()
            QtWidgets.QApplication.processEvents()
            exporter = pg.exporters.SVGExporter(widget.plot.plotItem)
            parameters = exporter.parameters()
            if "width" in parameters:
                parameters["width"] = max(320, widget.plot.width())
            data = exporter.export(toBytes=True)
        finally:
            cls._restore_export_curves(saved)
            widget.plot.scene().update()
        if isinstance(data, str):
            data = data.encode("utf-8")
        elif isinstance(data, QtCore.QByteArray):
            data = bytes(data)
        size = QtCore.QSize(
            max(320, widget.plot.width()),
            max(200, widget.plot.height()),
        )
        return bytes(data), size

    def export_plots(self):
        """Export selected traces together on one vector PDF or SVG sheet."""
        dialog = PlotExportDialog(self.model, self)
        if not dialog.exec():
            return
        trace_ids, file_format, background = dialog.values()
        if not trace_ids:
            return
        suffix = file_format
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Export plots",
            f"traces.{suffix}",
            f"{file_format.upper()} (*.{suffix})",
        )
        if not filename:
            return
        self._write_combined_vector(
            filename, trace_ids, file_format, background
        )

    def _write_combined_vector(
        self, filename, trace_ids, file_format, background
    ):
        """Stack native SVGExporter plots vertically and paint one sheet."""
        rendered = []
        width = 0
        height = 0
        for trace_id in trace_ids:
            widget = self.widgets[trace_id]
            original = self.model.traces[trace_id].background
            
            legend = widget.plot.plotItem.legend
            legend_position = None
            
            if legend is not None:
                position = legend.pos()
                legend_position = (position.x(), position.y())
                
            widget.apply_plot_theme(background, queued=False)

            if legend is not None and legend_position is not None:
                legend.setPos(*legend_position)

            QtWidgets.QApplication.processEvents()

            if legend is not None and legend_position is not None:
                legend.setPos(*legend_position)
                    
            svg, size = self.svg_for_pdf(widget, background)            

            widget.apply_plot_theme(original, queued=False)
            
            if legend is not None and legend_position is not None:
                legend.setPos(*legend_position)
                
            rendered.append((svg, size))
            width = max(width, size.width())
            height += size.height()
        colors = {
            "white": QtGui.QColor("white"),
            "black": QtGui.QColor("black"),
            "transparent": QtGui.QColor(0, 0, 0, 0),
        }
        if file_format == "pdf":
            device = QtGui.QPdfWriter(filename)
            device.setResolution(96)
            factor = 72.0 / device.resolution()
            page_size = QtGui.QPageSize(
                QtCore.QSizeF(width * factor, height * factor),
                QtGui.QPageSize.Unit.Point,
                "Combined plots",
                QtGui.QPageSize.SizeMatchPolicy.ExactMatch,
            )
            device.setPageSize(page_size)
            device.setPageMargins(
                QtCore.QMarginsF(), QtGui.QPageLayout.Unit.Point
            )
        else:
            device = QtSvg.QSvgGenerator()
            device.setFileName(filename)
            device.setSize(QtCore.QSize(width, height))
            device.setViewBox(QtCore.QRect(0, 0, width, height))
            device.setTitle("PQWaveForm plots")
        painter = QtGui.QPainter(device)
        painter.fillRect(
            QtCore.QRectF(0, 0, width, height), colors[background]
        )
        offset = 0
        for svg, size in rendered:
            renderer = QtSvg.QSvgRenderer(QtCore.QByteArray(svg))
            target = QtCore.QRectF(0, offset, width, size.height())
            renderer.render(painter, target)
            offset += size.height()
        painter.end()

    def fit_active_trace(self):
        """Fit the active trace to all visible data."""
        trace_id = self.model.active_trace_id
        if trace_id in self.widgets:
            self.widgets[trace_id].plot.autoRange()

    def close_with_history(self):
        """Close normally and store the final history state."""
        self.skip_history_on_close = False
        self.close()

    def close_without_history(self):
        """Close without appending a final history state."""
        self.skip_history_on_close = True
        self.close()

    def closeEvent(self, event):
        """Stop embedded kernel."""
        if not self.skip_history_on_close:
            try:
                self.autosave_history()
            except (OSError, TypeError, ValueError):
                pass
        self.console.shutdown()
        event.accept()
