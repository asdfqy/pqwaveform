"""Central data model for source files, traces, and calculated graphs."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import keyword
import re
from typing import Any, Iterable

import numpy as np
import pandas as pd
from PyQt6 import QtCore

LINE_STYLES = {
    "solid": 1,
    "dash": 2,
    "dot": 3,
    "dash-dot": 4,
    "none": 5,
    "points": 5,
    "points-only": 5,
}
COMPRESSED_SUFFIXES = (".gz", ".bz2", ".zip", ".xz", ".zst", ".tar")


@dataclass
class Style:
    """Display and alias settings for a source column."""

    is_x: bool = False
    is_y: bool = False
    alias: str = ""
    color: Any = (0, 170, 255, 255)
    width: float = 1.0
    line_style: int = 1
    show_points: bool = False
    marker_symbol: str = "o"
    legend_name: str = ""


@dataclass
class DataFile:
    """One loaded numeric table."""

    uid: int
    path: str
    labels: list[str]
    data: np.ndarray
    import_options: dict = field(default_factory=dict)

    @property
    def name(self) -> str:
        return Path(self.path).name


@dataclass
class Graph:
    """A calculated graph owned by exactly one trace."""

    uid: int
    name: str
    x: np.ndarray
    y: np.ndarray
    alias: str = ""
    color: Any = (255, 170, 0, 255)
    width: float = 1.0
    line_style: int = 1
    visible: bool = True
    show_points: bool = False
    marker_symbol: str = "o"
    legend_name: str = ""


@dataclass
class Trace:
    """One plot, its source styles, calculated graphs, and axis settings."""

    uid: int
    name: str
    styles: dict = field(default_factory=dict)
    graphs: list[Graph] = field(default_factory=list)
    x_link: str = "none"
    y_link: str = "none"
    cursor_enabled: bool = True
    x_log: bool = False
    y_log: bool = False
    grid_enabled: bool = False
    x_name: str = ""
    x_unit: str = ""
    y_name: str = ""
    y_unit: str = ""
    engineering_axes: bool = True
    axis_label_size: int = 10
    axis_tick_size: int = 9
    marker_label_size: int = 10
    marker_offset: float = 0.04
    tab_id: int = 0
    x_graph_id: int | None = None
    title: str = ""
    legend_visible: bool = False
    legend_font_size: int = 10
    tracker_interpolation: bool = False
    marker_mode: str = "horizontal"
    background: str = "black"
    vertical_marker_lock: bool = False


class ProjectModel(QtCore.QObject):
    """Own all project state and expose the IPython graph and save APIs."""

    files_changed = QtCore.pyqtSignal()
    traces_changed = QtCore.pyqtSignal()
    trace_changed = QtCore.pyqtSignal(int)
    active_trace_changed = QtCore.pyqtSignal(int)
    aliases_changed = QtCore.pyqtSignal()
    links_changed = QtCore.pyqtSignal()
    tabs_changed = QtCore.pyqtSignal()
    active_tab_changed = QtCore.pyqtSignal(int)
    tree_leaf_requested = QtCore.pyqtSignal(str, int, int)
    marker_requested = QtCore.pyqtSignal(str, float, int)

    def __init__(self, options, parent=None):
        super().__init__(parent)
        self.options = options
        self.files: dict[int, DataFile] = {}
        self.traces: dict[int, Trace] = {}
        self.trace_order: list[int] = []
        self.active_trace_id: int | None = None
        self.next_file_id = 0
        self.next_trace_id = 0
        self.next_graph_id = 0
        self.tabs = {0: "Tab 1"}
        self.tab_order = [0]
        self.active_tab_id = 0
        self.next_tab_id = 1
        self.palette = [
            (0, 191, 255, 255),
            (255, 107, 107, 255),
            (80, 227, 194, 255),
            (255, 209, 102, 255),
            (179, 136, 255, 255),
            (255, 140, 66, 255),
            (77, 208, 225, 255),
            (240, 98, 146, 255),
            (174, 213, 129, 255),
            (255, 241, 118, 255),
            (126, 87, 194, 255),
            (38, 166, 154, 255),
            (239, 83, 80, 255),
            (66, 165, 245, 255),
            (236, 64, 122, 255),
            (102, 187, 106, 255),
            (255, 167, 38, 255),
            (171, 71, 188, 255),
            (38, 198, 218, 255),
            (212, 225, 87, 255),
            (92, 107, 192, 255),
            (141, 110, 99, 255),
            (41, 182, 246, 255),
            (156, 204, 101, 255),
            (255, 112, 67, 255),
            (120, 144, 156, 255),
            (192, 202, 51, 255),
            (186, 104, 200, 255),
            (0, 229, 255, 255),
            (255, 64, 129, 255),
            (118, 255, 3, 255),
            (255, 234, 0, 255),
            (124, 77, 255, 255),
            (29, 233, 182, 255),
            (255, 82, 82, 255),
            (68, 138, 255, 255),
            (224, 64, 251, 255),
            (105, 240, 174, 255),
            (255, 171, 64, 255),
            (24, 255, 255, 255),
        ]
        self.add_trace()

    def add_tab(self, name=None) -> int:
        """Create a tab and its initial trace as one atomic operation."""
        uid = self.next_tab_id
        self.next_tab_id += 1
        self.tabs[uid] = name or f"Tab {uid + 1}"
        self.tab_order.append(uid)
        self.active_tab_id = uid
        trace_id = self.next_trace_id
        self.next_trace_id += 1
        trace = Trace(trace_id, f"Trace {trace_id}", tab_id=uid)
        self.traces[trace_id] = trace
        self.trace_order.append(trace_id)
        for file_id in self.files:
            self._initialize_styles(trace, file_id)
        self.active_trace_id = trace_id
        self.tabs_changed.emit()
        self.traces_changed.emit()
        self.active_tab_changed.emit(uid)
        self.active_trace_changed.emit(trace_id)
        return uid

    def rename_tab(self, uid, name) -> None:
        """Rename an existing trace tab."""
        if uid in self.tabs and str(name).strip():
            self.tabs[uid] = str(name).strip()
            self.tabs_changed.emit()

    def set_active_tab(self, uid) -> None:
        """Activate a tab and one of its traces when available."""
        if uid not in self.tabs:
            return
        self.active_tab_id = uid
        traces = [
            tid
            for tid in self.trace_order
            if self.traces[tid].tab_id == uid
        ]
        if traces and self.active_trace_id not in traces:
            self.active_trace_id = traces[0]
            self.active_trace_changed.emit(self.active_trace_id)
        self.active_tab_changed.emit(uid)

    def remove_tab(self, uid) -> bool:
        """Remove a tab together with every trace owned by that tab."""
        if uid not in self.tabs or len(self.tab_order) <= 1:
            return False
        owned = [
            trace_id
            for trace_id in self.trace_order
            if self.traces[trace_id].tab_id == uid
        ]
        for trace_id in owned:
            del self.traces[trace_id]
            self.trace_order.remove(trace_id)
        del self.tabs[uid]
        self.tab_order.remove(uid)
        self.active_tab_id = self.tab_order[0]
        remaining = [
            trace_id
            for trace_id in self.trace_order
            if self.traces[trace_id].tab_id == self.active_tab_id
        ]
        if not self.trace_order:
            self.add_trace()
        elif remaining:
            self.active_trace_id = remaining[0]
        else:
            self.active_trace_id = self.trace_order[0]
            self.active_tab_id = self.traces[self.active_trace_id].tab_id
        self.tabs_changed.emit()
        self.traces_changed.emit()
        self.active_tab_changed.emit(self.active_tab_id)
        self.active_trace_changed.emit(self.active_trace_id)
        self.aliases_changed.emit()
        return True

    def add_trace(self, name=None) -> int:
        """Create and activate a new trace."""
        uid = self.next_trace_id
        self.next_trace_id += 1
        trace = Trace(
            uid,
            name or f"Trace {uid}",
            tab_id=self.active_tab_id,
        )
        self.traces[uid] = trace
        self.trace_order.append(uid)
        for file_id in self.files:
            self._initialize_styles(trace, file_id)
        self.active_trace_id = uid
        self.traces_changed.emit()
        self.active_trace_changed.emit(uid)
        return uid

    def remove_trace(self, uid: int) -> bool:
        """Delete a trace and all graphs and aliases owned by it."""
        if uid not in self.traces or len(self.trace_order) <= 1:
            return False
        position = self.trace_order.index(uid)
        del self.traces[uid]
        self.trace_order.remove(uid)
        self.active_trace_id = self.trace_order[
            min(position, len(self.trace_order) - 1)
        ]
        self.traces_changed.emit()
        self.active_trace_changed.emit(self.active_trace_id)
        self.aliases_changed.emit()
        return True

    def set_active_trace(self, uid: int) -> None:
        if uid in self.traces:
            self.active_trace_id = uid
            self.active_trace_changed.emit(uid)

    @staticmethod
    def _is_compressed(filename) -> bool:
        return str(filename).lower().endswith(COMPRESSED_SUFFIXES)

    @staticmethod
    def _detect_encoding(filename) -> str:
        """Detect BOM, UTF-16 NUL patterns, UTF-8, CP1252, then Latin-1."""
        with open(filename, "rb") as stream:
            sample = stream.read(65536)
        if sample.startswith(b"\xef\xbb\xbf"):
            return "utf-8-sig"
        if sample.startswith((b"\xff\xfe", b"\xfe\xff")):
            return "utf-16"
        even_nuls = sample[:512:2].count(0)
        odd_nuls = sample[1:512:2].count(0)
        if max(even_nuls, odd_nuls) >= 4:
            return "utf-16-le" if odd_nuls > even_nuls else "utf-16-be"
        try:
            sample.decode("utf-8")
            return "utf-8"
        except UnicodeDecodeError:
            try:
                sample.decode("cp1252")
                return "cp1252"
            except UnicodeDecodeError:
                return "latin-1"

    def _comment_labels(self, filename, encoding) -> list[str]:
        if self._is_compressed(filename):
            return []
        labels = []
        try:
            with open(filename, encoding=encoding, errors="replace") as stream:
                for raw_line in stream:
                    line = raw_line.strip()
                    if line.startswith(self.options.dcomment):
                        content = line[len(self.options.dcomment) :].strip()
                        if self.options.dseparator in (",", ";", "\t"):
                            fields = content.split(self.options.dseparator)
                        else:
                            fields = re.split(self.options.dseparator, content)
                        labels = [field.strip().strip('"') for field in fields]
                    elif line:
                        break
        except OSError:
            pass
        return labels

    def load_file(self, filename, aliases_from_comment=True) -> int:
        """Load uncompressed or compressed numeric data."""
        encoding = (
            "utf-8"
            if self._is_compressed(filename)
            else self._detect_encoding(filename)
        )
        labels = self._comment_labels(filename, encoding)
        header = None if self.options.dheader < 0 else self.options.dheader
        frame = pd.read_csv(
            filename,
            sep=self.options.dseparator,
            header=header,
            skiprows=self.options.dskipbegin,
            skipfooter=self.options.dskipend,
            comment=self.options.dcomment,
            engine="python",
            compression="infer",
            on_bad_lines="warn",
            encoding=encoding,
            encoding_errors="replace",
        ).apply(pd.to_numeric, errors="coerce")
        if frame.empty:
            raise ValueError("No numeric data was found.")
        if len(labels) == frame.shape[1]:
            frame.columns = labels
        uid = self.next_file_id
        self.next_file_id += 1
        self.files[uid] = DataFile(
            uid,
            str(filename),
            list(map(str, frame.columns)),
            frame.to_numpy(float),
            {
                "dseparator": self.options.dseparator,
                "dcomment": self.options.dcomment,
                "dheader": self.options.dheader,
                "dskipbegin": self.options.dskipbegin,
                "dskipend": self.options.dskipend,
            },
        )
        for trace in self.traces.values():
            self._initialize_styles(trace, uid)
        if aliases_from_comment and len(labels) == frame.shape[1]:
            self._apply_comment_aliases(uid, labels)
        self.files_changed.emit()
        for trace_id in self.trace_order:
            self.trace_changed.emit(trace_id)
        self.aliases_changed.emit()
        for trace_id, trace in self.traces.items():
            if any(style.is_y for style in trace.styles[uid].values()):
                self.tree_leaf_requested.emit("file", uid, trace_id)
        return uid

    def _apply_comment_aliases(self, file_id, labels) -> None:
        """Create unique aliases once, in the active trace."""
        trace = self.traces[self.active_trace_id]
        used = set(self.alias_arrays())
        for column, label in enumerate(labels):
            alias = re.sub(r"\W+", "_", label).strip("_")
            if alias and alias[0].isdigit():
                alias = "_" + alias
            if (
                alias
                and alias.isidentifier()
                and not keyword.iskeyword(alias)
                and alias not in used
            ):
                trace.styles[file_id][column].alias = alias
                used.add(alias)

    def _initialize_styles(self, trace, file_id) -> None:
        data_file = self.files[file_id]
        width = max(0.5, float(self.options.linewidth or 1.0))
        line_style = max(1, min(5, int(self.options.linestyle or 1)))
        trace.styles[file_id] = {
            column: Style(
                color=self.palette[column % len(self.palette)],
                width=width,
                line_style=line_style,
            )
            for column in range(len(data_file.labels))
        }
        if data_file.labels:
            trace.styles[file_id][
                min(self.options.xcolumn, len(data_file.labels) - 1)
            ].is_x = True

    def remove_file(self, file_id: int) -> bool:
        if file_id not in self.files:
            return False
        del self.files[file_id]
        changed_traces = []
        for trace in self.traces.values():
            if trace.styles.pop(file_id, None) is not None:
                changed_traces.append(trace.uid)
        self.prune_aliases()
        self.files_changed.emit()
        for trace_id in changed_traces:
            self.trace_changed.emit(trace_id)
        self.aliases_changed.emit()
        return True

    def clear_alias(self, alias):
        """Clear one source or graph alias and synchronize IPython."""
        alias = str(alias).strip()
        changed = False
        for trace in self.traces.values():
            for styles in trace.styles.values():
                for style in styles.values():
                    if style.alias == alias:
                        style.alias = ""
                        changed = True
            for graph in trace.graphs:
                if graph.alias == alias:
                    graph.alias = ""
                    changed = True
        if changed:
            self.aliases_changed.emit()
        return changed

    def clear_all_aliases(self):
        """Clear every model-owned source and calculated-graph alias."""
        for trace in self.traces.values():
            for styles in trace.styles.values():
                for style in styles.values():
                    style.alias = ""
            for graph in trace.graphs:
                graph.alias = ""
        self.aliases_changed.emit()

    def prune_aliases(self):
        """Remove references and aliases whose owning files no longer exist."""
        removed = []
        for trace in self.traces.values():
            for file_id in list(trace.styles):
                if file_id not in self.files:
                    removed.extend(
                        style.alias
                        for style in trace.styles[file_id].values()
                        if style.alias
                    )
                    del trace.styles[file_id]
            if trace.x_graph_id is not None:
                graph_ids = {graph.uid for graph in trace.graphs}
                if trace.x_graph_id not in graph_ids:
                    trace.x_graph_id = None
        self.aliases_changed.emit()
        return removed

    def clear_traces(self, tab=None):
        """Replace all traces in one tab with one empty trace."""
        tab_id = self.active_tab_id if tab is None else int(tab)
        owned = [
            trace_id for trace_id in self.trace_order
            if self.traces[trace_id].tab_id == tab_id
        ]
        for trace_id in owned:
            del self.traces[trace_id]
            self.trace_order.remove(trace_id)
        previous_tab = self.active_tab_id
        self.active_tab_id = tab_id
        trace_id = self.add_trace()
        self.active_tab_id = (
            previous_tab if previous_tab in self.tabs else tab_id
        )
        self.set_active_tab(tab_id)
        self.aliases_changed.emit()
        return trace_id

    def clear_all_files(self):
        """Remove files, traces, graphs, and aliases; keep one trace."""
        self.files.clear()
        self.traces.clear()
        self.trace_order.clear()
        self.tabs = {0: "Tab 1"}
        self.tab_order = [0]
        self.active_tab_id = 0
        self.next_tab_id = 1
        self.active_trace_id = None
        self.add_trace()
        self.files_changed.emit()
        self.tabs_changed.emit()
        self.aliases_changed.emit()

    def set_x_column(self, file_id, column) -> None:
        trace = self.traces[self.active_trace_id]
        trace.x_graph_id = None
        for style in trace.styles[file_id].values():
            style.is_x = False
        trace.styles[file_id][column].is_x = True
        self.trace_changed.emit(trace.uid)

    def set_y_column(self, file_id, column, visible) -> None:
        trace = self.traces[self.active_trace_id]
        trace.styles[file_id][column].is_y = bool(visible)
        self.trace_changed.emit(trace.uid)

    def set_column_style(self, file_id, column, **changes) -> None:
        """Update display properties of one source column."""
        style = self.traces[self.active_trace_id].styles[file_id][column]
        if "style" in changes:
            changes["line_style"] = changes.pop("style")
        if "line_style" in changes:
            changes["line_style"] = self._line_style_number(
                changes["line_style"]
            )
        if "width" in changes:
            changes["width"] = float(changes["width"])
            if changes["width"] <= 0:
                raise ValueError("Line width must be positive.")
        allowed = {
            "color",
            "width",
            "line_style",
            "show_points",
            "marker_symbol",
            "legend_name",
            "is_x",
            "is_y",
        }
        unknown = set(changes) - allowed
        if unknown:
            raise ValueError(
                f"Unsupported source style properties: {sorted(unknown)}"
            )
        for name, value in changes.items():
            setattr(style, name, value)
        self.trace_changed.emit(self.active_trace_id)

    def _validate_alias(self, value, current="") -> str:
        value = value.strip()
        if value and (not value.isidentifier() or keyword.iskeyword(value)):
            raise ValueError(
                "Alias must be a valid Python identifier and not a keyword."
            )
        aliases = self.alias_arrays()
        if value and value in aliases and value != current:
            raise ValueError("Alias is already used in this project.")
        return value

    def set_alias(self, file_id, column, value) -> None:
        style = self.traces[self.active_trace_id].styles[file_id][column]
        style.alias = self._validate_alias(value, style.alias)
        self.aliases_changed.emit()
        self.trace_changed.emit(self.active_trace_id)

    def _selected_x(self, trace):
        if trace.x_graph_id is not None:
            try:
                _, graph = self.find_graph(trace.x_graph_id, trace.uid)
                return graph.y
            except KeyError:
                trace.x_graph_id = None
        for file_id, styles in trace.styles.items():
            for column, style in styles.items():
                if style.is_x and file_id in self.files:
                    return self.files[file_id].data[:, column]
        return None

    def _file_x(self, trace, file_id):
        """Return the X array selected for one source file."""
        if trace.x_graph_id is not None:
            return self._selected_x(trace)
        for column, style in trace.styles.get(file_id, {}).items():
            if style.is_x and file_id in self.files:
                return self.files[file_id].data[:, column]
        return None

    def set_graph_as_x(self, graph_or_id, trace=None) -> None:
        """Use a calculated graph's Y array as source-curve X axis."""
        trace_id, graph = self.find_graph(graph_or_id, trace)
        selected = self.traces[trace_id]
        for styles in selected.styles.values():
            for style in styles.values():
                style.is_x = False
        selected.x_graph_id = graph.uid
        self.trace_changed.emit(trace_id)

    def _line_style_number(self, value) -> int:
        if isinstance(value, str):
            key = value.lower().strip()
            if key not in LINE_STYLES:
                raise ValueError(f"Unknown line style: {value}")
            return LINE_STYLES[key]
        number = int(value)
        if number not in LINE_STYLES.values():
            raise ValueError(
                "Line style must be 1..5 or one of solid, dash, "
                "dot, dash-dot, or none."
            )
        return number

    def add_graph(
        self,
        y,
        x=None,
        name="graph",
        trace=None,
        alias="",
        color=None,
        width=1.0,
        style=1,
        visible=True,
    ) -> Graph:
        """Create a calculated graph owned by the selected trace."""
        trace_id = self.active_trace_id if trace is None else int(trace)
        if trace_id not in self.traces:
            raise KeyError(f"Unknown trace {trace_id}.")
        y_values = np.asarray(y, dtype=float).reshape(-1)
        base_x = self._selected_x(self.traces[trace_id])
        if x is not None:
            x_values = np.asarray(x, dtype=float).reshape(-1)
        elif base_x is not None and len(base_x) == len(y_values):
            x_values = base_x.copy()
        elif base_x is not None and len(base_x) == len(y_values) + 1:
            x_values = base_x[1:].copy()
        else:
            x_values = np.arange(len(y_values), dtype=float)
        if len(x_values) != len(y_values):
            raise ValueError("x and y lengths differ.")
        alias = self._validate_alias(alias)
        graph = Graph(
            uid=self.next_graph_id,
            name=str(name),
            x=x_values,
            y=y_values,
            alias=alias,
            color=color
            or self.palette[self.next_graph_id % len(self.palette)],
            width=float(width),
            line_style=self._line_style_number(style),
            visible=bool(visible),
        )
        self.next_graph_id += 1
        self.traces[trace_id].graphs.append(graph)
        self.trace_changed.emit(trace_id)
        if graph.alias:
            self.aliases_changed.emit()
        self.tree_leaf_requested.emit("calculated", trace_id, trace_id)
        return graph

    def new_trace(
        self, y=None, x=None, name="graph", trace_name=None, **style
    ) -> int:
        trace_id = self.add_trace(trace_name)
        if y is not None:
            self.add_graph(y, x=x, name=name, trace=trace_id, **style)
        return trace_id

    def find_graph(self, graph_or_id, trace=None):
        graph_id = (
            graph_or_id.uid
            if isinstance(graph_or_id, Graph)
            else int(graph_or_id)
        )
        trace_ids: Iterable[int] = (
            [int(trace)] if trace is not None else self.trace_order
        )
        for trace_id in trace_ids:
            for graph in self.traces[trace_id].graphs:
                if graph.uid == graph_id:
                    return trace_id, graph
        raise KeyError(f"Calculated graph {graph_id} was not found.")

    def remove_graph(self, graph_or_id, trace=None) -> bool:
        """Remove a calculated graph, its alias, tree entry, and plot curve."""
        try:
            trace_id, graph = self.find_graph(graph_or_id, trace)
        except KeyError:
            return False
        self.traces[trace_id].graphs.remove(graph)
        if self.traces[trace_id].x_graph_id == graph.uid:
            self.traces[trace_id].x_graph_id = None
        self.trace_changed.emit(trace_id)
        if graph.alias:
            self.aliases_changed.emit()
        return True

    def set_graph_style(self, graph_or_id, trace=None, **changes) -> Graph:
        """Update name, alias, color, width, line style, or visibility."""
        trace_id, graph = self.find_graph(graph_or_id, trace)
        if "alias" in changes:
            changes["alias"] = self._validate_alias(
                changes["alias"], graph.alias
            )
        if "style" in changes:
            changes["line_style"] = changes.pop("style")
        if "line_style" in changes:
            changes["line_style"] = self._line_style_number(
                changes["line_style"]
            )
        if "width" in changes:
            changes["width"] = float(changes["width"])
            if changes["width"] <= 0:
                raise ValueError("Line width must be positive.")
        allowed = {
            "name",
            "alias",
            "color",
            "width",
            "line_style",
            "visible",
            "show_points",
            "marker_symbol",
            "legend_name",
        }
        unknown = set(changes) - allowed
        if unknown:
            raise ValueError(
                f"Unsupported graph properties: {sorted(unknown)}"
            )
        alias_changed = "alias" in changes and changes["alias"] != graph.alias
        for name, value in changes.items():
            setattr(graph, name, value)
        self.trace_changed.emit(trace_id)
        if alias_changed:
            self.aliases_changed.emit()
        return graph

    def alias_arrays(self) -> dict[str, np.ndarray]:
        result = {}
        for trace in self.traces.values():
            for file_id, styles in trace.styles.items():
                if file_id not in self.files:
                    continue
                for column, style in styles.items():
                    if style.alias:
                        result[style.alias] = self.files[file_id].data[
                            :, column
                        ]
            for graph in trace.graphs:
                if graph.alias:
                    result[graph.alias] = graph.y
        return result

    def visible_curves(self, trace_id):
        trace = self.traces[trace_id]
        curves = []
        for file_id, styles in trace.styles.items():
            selected_x = self._file_x(trace, file_id)
            if file_id not in self.files:
                continue
            for column, style in styles.items():
                if not style.is_y:
                    continue
                y_values = self.files[file_id].data[:, column]
                x_values = (
                    selected_x
                    if selected_x is not None
                    and len(selected_x) == len(y_values)
                    else np.arange(len(y_values))
                )
                curves.append(
                    (
                        self.files[file_id].labels[column],
                        x_values,
                        y_values,
                        style,
                    )
                )
        curves.extend((g.name, g.x, g.y, g) for g in trace.graphs if g.visible)
        return curves

    def set_file_columns_visible(self, file_id, visible, trace=None):
        """Show or hide every non-X source column of one file."""
        trace_id = self.active_trace_id if trace is None else int(trace)
        styles = self.traces[trace_id].styles[int(file_id)]
        for style in styles.values():
            if not style.is_x:
                style.is_y = bool(visible)
        self.trace_changed.emit(trace_id)

    def reload_file(self, file_id):
        """Reload a source file in place while preserving trace styles."""
        file_id = int(file_id)
        original = self.files[file_id]
        saved = {
            trace_id: trace.styles[file_id]
            for trace_id, trace in self.traces.items()
        }
        path = original.path
        options = original.import_options
        for key, value in options.items():
            setattr(self.options, key, value)
        new_id = self.load_file(path, aliases_from_comment=False)
        replacement = self.files.pop(new_id)
        replacement.uid = file_id
        self.files[file_id] = replacement
        for trace_id, trace in self.traces.items():
            old_styles = saved[trace_id]
            new_styles = trace.styles.pop(new_id)
            trace.styles[file_id] = {
                column: old_styles.get(column, style)
                for column, style in new_styles.items()
            }
            self.trace_changed.emit(trace_id)
        self.files_changed.emit()
        self.aliases_changed.emit()
        return file_id

    def reload_all_files(self):
        """Reload every source file from disk."""
        for file_id in list(self.files):
            self.reload_file(file_id)

    def add_marker_h(self, value, trace=None) -> None:
        """Add a horizontal intersection marker to a selected trace."""
        trace_id = self.active_trace_id if trace is None else int(trace)
        if trace_id not in self.traces:
            raise KeyError(f"Unknown trace {trace_id}.")
        self.marker_requested.emit("h", float(value), trace_id)

    def add_marker_v(self, value, trace=None) -> None:
        """Add a vertical intersection marker to a selected trace."""
        trace_id = self.active_trace_id if trace is None else int(trace)
        if trace_id not in self.traces:
            raise KeyError(f"Unknown trace {trace_id}.")
        self.marker_requested.emit("v", float(value), trace_id)

    def save_graph(
        self, graph_or_y, filename, x=None, x_name="x", y_name=None
    ) -> None:
        if isinstance(graph_or_y, Graph):
            x_values, y_values, name = (
                graph_or_y.x,
                graph_or_y.y,
                graph_or_y.name,
            )
        else:
            y_values = np.asarray(graph_or_y)
            x_values = np.arange(len(y_values)) if x is None else np.asarray(x)
            name = "value"
        pd.DataFrame({x_name: x_values, y_name or name: y_values}).to_csv(
            filename,
            index=False,
            sep="\t" if str(filename).lower().endswith(".tsv") else ",",
            compression="infer",
        )

    def save_trace(self, trace_id, filename) -> None:
        self.save_traces([trace_id], filename)

    def save_traces(self, trace_ids, filename) -> None:
        columns = {}
        maximum_size = 0
        for trace_id in trace_ids:
            for index, (name, x_values, y_values, _) in enumerate(
                self.visible_curves(int(trace_id))
            ):
                columns[f"trace_{trace_id}_{index}_x"] = np.asarray(x_values)
                columns[f"trace_{trace_id}_{index}_{name}"] = np.asarray(
                    y_values
                )
                maximum_size = max(maximum_size, len(x_values), len(y_values))
        if not columns:
            raise ValueError("No visible curves are available for export.")
        padded = {
            name: np.pad(
                values.astype(float),
                (0, maximum_size - len(values)),
                constant_values=np.nan,
            )
            for name, values in columns.items()
        }
        separator = "\t" if str(filename).lower().endswith(".tsv") else ","
        pd.DataFrame(padded).to_csv(
            filename, index=False, sep=separator, compression="infer"
        )

    def save_all_traces(self, filename) -> None:
        self.save_traces(self.trace_order, filename)

    def set_axis(self, trace_id=None, **changes) -> None:
        trace = self.traces[
            self.active_trace_id if trace_id is None else int(trace_id)
        ]
        name_mapping = {"engineering": "engineering_axes"}
        for name, value in changes.items():
            setattr(trace, name_mapping.get(name, name), value)
        self.trace_changed.emit(trace.uid)

    def load_palette(self, filename) -> None:
        frame = pd.read_csv(filename)
        names = {str(column).upper(): column for column in frame.columns}
        missing = set("RGB") - set(names)
        if missing:
            raise ValueError("Palette requires R, G, and B columns.")
        alpha = names.get("A") or names.get("ALPHA")
        self.palette = [
            tuple(int(row[names[channel]]) for channel in "RGB")
            + ((int(row[alpha]) if alpha else 255),)
            for _, row in frame.iterrows()
        ]
