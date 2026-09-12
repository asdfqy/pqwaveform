"""Deterministic Qt 6 user-interface construction."""

from PyQt6 import QtCore, QtGui, QtWidgets


class UiMainWindow:
    """Create every runtime widget explicitly."""

    def setup_ui(self, window):
        """Build plots, resizable IPython pane, docks, menus, and actions."""
        window.resize(1450, 920)
        window.setWindowTitle("PQWaveForm Qt 6 with IPython")
        central = QtWidgets.QWidget(window)
        layout = QtWidgets.QVBoxLayout(central)
        layout.setContentsMargins(2, 2, 2, 2)
        self.main_splitter = QtWidgets.QSplitter(
            QtCore.Qt.Orientation.Vertical
        )
        self.trace_tabs = QtWidgets.QTabWidget()
        self.trace_tabs.setTabsClosable(True)
        self.trace_tabs.setDocumentMode(True)
        self.console_host = QtWidgets.QWidget()
        self.console_layout = QtWidgets.QVBoxLayout(self.console_host)
        self.console_layout.setContentsMargins(0, 0, 0, 0)
        self.main_splitter.addWidget(self.trace_tabs)
        self.main_splitter.addWidget(self.console_host)
        self.main_splitter.setCollapsible(0, False)
        self.main_splitter.setCollapsible(1, True)
        self.main_splitter.setStretchFactor(0, 5)
        self.main_splitter.setStretchFactor(1, 2)
        self.main_splitter.setSizes([650, 270])
        layout.addWidget(self.main_splitter)
        window.setCentralWidget(central)
        self.file_dock = QtWidgets.QDockWidget("Files and graphs", window)
        self.file_tree = QtWidgets.QTreeView()
        self.file_tree.setUniformRowHeights(True)
        self.file_tree.setAlternatingRowColors(True)
        self.file_tree.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.DoubleClicked
            | QtWidgets.QAbstractItemView.EditTrigger.EditKeyPressed
        )
        self.file_dock.setWidget(self.file_tree)
        window.addDockWidget(
            QtCore.Qt.DockWidgetArea.LeftDockWidgetArea, self.file_dock
        )
        self.trace_dock = QtWidgets.QDockWidget("Traces", window)
        self.trace_table = QtWidgets.QTableWidget(0, 10)
        self.trace_table.setHorizontalHeaderLabels(
            [
                "Trace",
                "Delete",
                "XLockedTo",
                "YLockedTo",
                "Zoom",
                "Cursor",
                "Legend",
                "Log Axis",
                "Grid",
                "Title",
            ]
        )
        self.trace_dock.setWidget(self.trace_table)
        window.addDockWidget(
            QtCore.Qt.DockWidgetArea.TopDockWidgetArea, self.trace_dock
        )
        fm = window.menuBar().addMenu("File")
        tm = window.menuBar().addMenu("Trace")
        vm = window.menuBar().addMenu("View")
        hm = window.menuBar().addMenu("Help")
        self.open_action = self._action(fm, "Open...", "Ctrl+O")
        self.delete_file_action = self._action(
            fm, "Remove selected file", "Ctrl+D"
        )
        self.clear_file_action = self._action(
            fm, "Clear file"
        )
        self.clear_all_files_action = self._action(
            fm, "Clear all files"
        )
        self.reload_action = self._action(
            fm, "Reload data", "Ctrl+R"
        )
        self.load_script_action = self._action(
            fm, "Load Python file into IPython..."
        )
        self.load_palette_action = self._action(fm, "Load color palette...")
        self.history_action = self._action(
            fm, "History states...", "Ctrl+Shift+H"
        )
        self.open_history_action = self._action(
            fm, "Open history file..."
        )
        self.export_action = self._action(
            fm, "Export active trace...", "Ctrl+S"
        )
        self.export_all_action = self._action(
            fm, "Export all traces...", "Ctrl+Shift+S"
        )
        self.export_plot_action = self._action(
            fm, "Export plots...", "Ctrl+Alt+S"
        )
        self.exit_action = self._action(
            fm, "Exit and save history", "Ctrl+Q"
        )
        self.exit_without_history_action = self._action(
            fm, "Exit without saving history", "Ctrl+Shift+Q"
        )
        self.add_trace_action = self._action(tm, "Add trace", "Ctrl+T")
        self.add_tab_action = self._action(tm, "Add trace tab", "Ctrl+Shift+T")
        self.rename_tab_action = self._action(tm, "Rename current tab")
        self.close_tab_action = self._action(tm, "Close current tab")
        self.delete_trace_action = self._action(
            tm, "Delete active trace"
        )
        self.clear_traces_action = self._action(
            tm, "Clear traces"
        )
        self.fit_action = self._action(vm, "Fit active trace", "F")
        self.display_settings_action = self._action(
            tm, "Display and axis settings...", "Ctrl+Alt+D"
        )
        self.toggle_files_action = self._check(vm, "File tree", True)
        self.toggle_traces_action = self._check(vm, "Trace list", True)
        self.toggle_console_action = self._check(vm, "IPython console", True)
        self.grid_all_action = self._action(vm, "Toggle all grids", "Ctrl+G")
        self.link_x_all_action = self._action(vm, "Link all X axes", "Ctrl+L")
        self.tracker_action = self._action(vm, "Toggle trackers", "T")
        self.interpolate_action = self._action(
            vm, "Toggle tracker interpolation", "I"
        )
        self.marker_h_action = self._action(
            vm, "Add horizontal intersection marker", "H"
        )
        self.ab_horizontal_action = self._action(
            vm, "A/B horizontal measurement mode", "Ctrl+H"
        )
        self.ab_vertical_action = self._action(
            vm, "A/B vertical measurement mode", "Ctrl+V"
        )
        self.marker_v_action = self._action(
            vm, "Add vertical intersection marker", "V"
        )
        self.legend_action = self._action(
            vm, "Toggle active-trace legend", "Ctrl+Alt+L"
        )
        self.edit_legend_action = self._action(
            vm, "Edit active-trace legend names..."
        )
        self.marker_a_action = self._action(vm, "Place marker A", "A")
        self.marker_b_action = self._action(vm, "Place marker B", "B")
        self.clear_ab_action = self._action(
            vm, "Clear A/B markers", "Ctrl+Alt+B"
        )
        self.clear_markers_action = self._action(
            vm, "Clear all markers in active trace", "Ctrl+E"
        )
        self.delete_marker_action = self._action(
            vm, "Delete selected H/V marker", "Backspace"
        )
        self.expand_tree_action = self._action(
            vm, "Expand all file-tree leaves", "Ctrl+Alt+E"
        )
        self.collapse_tree_action = self._action(
            vm, "Collapse all file-tree leaves", "Ctrl+Alt+C"
        )
        self.visible_tree_action = self._action(
            vm, "Show leaves used by active trace", "Ctrl+Alt+V"
        )
        self.cycle_tree_action = self._action(
            vm, "Cycle file-tree leaf mode", "Ctrl+Shift+E"
        )
        self.show_file_columns_action = self._action(
            vm, "Show all columns of selected file", "Ctrl+Shift+A"
        )
        self.hide_file_columns_action = self._action(
            vm, "Hide all columns of selected file", "Ctrl+Shift+N"
        )
        self.help_action = self._action(hm, "Help and shortcuts")

    @staticmethod
    def _action(menu, text, shortcut=None):
        """Create a menu action with an optional shortcut."""
        action = QtGui.QAction(text, menu)
        if shortcut:
            action.setShortcut(shortcut)
            action.setShortcutContext(
                QtCore.Qt.ShortcutContext.ApplicationShortcut
            )
        menu.addAction(action)
        return action

    @staticmethod
    def _check(menu, text, checked):
        """Create a checkable menu action."""
        action = UiMainWindow._action(menu, text)
        action.setCheckable(True)
        action.setChecked(checked)
        return action
