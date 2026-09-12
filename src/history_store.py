"""JSON serialization for complete waveform-viewer history snapshots."""

from dataclasses import asdict
import json
from pathlib import Path

import numpy as np

from models import Graph, Style, Trace


DEFAULT_HISTORY = "pqwaveform_history.json"


def _json_value(value):
    """Recursively convert model and Qt-adjacent values for JSON."""
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list, set)):
        return [_json_value(item) for item in value]
    return value


def capture_model(model):
    """Capture model-owned files, traces, tabs, styles, and graphs."""
    traces = []
    for trace_id in model.trace_order:
        trace = model.traces[trace_id]
        values = asdict(trace)
        values["styles"] = {
            str(file_id): {
                str(column): {
                    key: _json_value(value)
                    for key, value in asdict(style).items()
                }
                for column, style in styles.items()
            }
            for file_id, styles in trace.styles.items()
        }
        # Numerical graph arrays are recreated by the stored Python code.
        # Persist all user-editable graph metadata separately and identify
        # duplicate names by their zero-based occurrence in this trace.
        graph_styles = []
        for index, graph in enumerate(trace.graphs):
            occurrence = sum(
                previous.name == graph.name
                for previous in trace.graphs[:index]
            )
            graph_styles.append(
                {
                    "name": graph.name,
                    "alias": graph.alias,
                    "occurrence": occurrence,
                    "color": _json_value(graph.color),
                    "width": graph.width,
                    "line_style": graph.line_style,
                    "visible": graph.visible,
                    "show_points": graph.show_points,
                    "legend_name": graph.legend_name,
                    "selected_as_x": trace.x_graph_id == graph.uid,
                }
            )
        values["graph_styles"] = graph_styles
        values["graphs"] = []
        values["x_graph_id"] = None
        traces.append(values)
    return {
        "files": [
            {
                "uid": data_file.uid,
                "path": data_file.path,
                "import_options": data_file.import_options,
            }
            for data_file in model.files.values()
        ],
        "traces": traces,
        "trace_order": model.trace_order,
        "active_trace_id": model.active_trace_id,
        "tabs": {str(key): value for key, value in model.tabs.items()},
        "tab_order": model.tab_order,
        "active_tab_id": model.active_tab_id,
        "palette": [list(color) for color in model.palette],
    }


def restore_model(model, state):
    """Restore files first, then exact trace and graph configuration."""
    model.blockSignals(True)
    model.files.clear()
    model.traces.clear()
    model.trace_order.clear()
    file_mapping = {}
    for item in state.get("files", []):
        for key, value in item.get("import_options", {}).items():
            setattr(model.options, key, value)
        current_id = model.load_file(
            item["path"], aliases_from_comment=False
        )
        file_mapping[item["uid"]] = current_id
    model.traces.clear()
    model.trace_order = list(state.get("trace_order", []))
    for source_values in state.get("traces", []):
        values = dict(source_values)
        # Accept history files created before per-label alignment replaced
        # the former trace-wide marker_text_alignment setting.
        values.pop("marker_text_alignment", None)
        values.pop("graph_styles", None)
        styles = {}
        for old_file, columns in values.pop("styles", {}).items():
            mapped = file_mapping.get(int(old_file), int(old_file))
            styles[mapped] = {
                int(column): Style(**style)
                for column, style in columns.items()
            }
        graphs = []
        for graph in values.pop("graphs", []):
            graph["x"] = np.asarray(graph["x"], dtype=float)
            graph["y"] = np.asarray(graph["y"], dtype=float)
            graphs.append(Graph(**graph))
        trace = Trace(**values)
        trace.styles = styles
        trace.graphs = graphs
        model.traces[trace.uid] = trace
    model.active_trace_id = state.get("active_trace_id")
    model.tabs = {
        int(key): value for key, value in state.get("tabs", {}).items()
    }
    model.tab_order = list(state.get("tab_order", [0]))
    model.active_tab_id = state.get("active_tab_id", 0)
    model.palette = [tuple(color) for color in state.get("palette", [])]
    model.next_file_id = max(model.files, default=-1) + 1
    model.next_trace_id = max(model.traces, default=-1) + 1
    graph_ids = [
        graph.uid
        for trace in model.traces.values()
        for graph in trace.graphs
    ]
    model.next_graph_id = max(graph_ids, default=-1) + 1
    model.blockSignals(False)
    model.files_changed.emit()
    model.traces_changed.emit()
    model.tabs_changed.emit()
    model.aliases_changed.emit()


def read_entries(filename=DEFAULT_HISTORY):
    """Read a history file or return an empty list."""
    path = Path(filename)
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8")).get("states", [])


def write_entries(entries, filename=DEFAULT_HISTORY):
    """Write named history entries as readable JSON."""
    Path(filename).write_text(
        json.dumps(
            _json_value({"version": 1, "states": entries}),
            indent=2,
        ),
        encoding="utf-8",
    )
