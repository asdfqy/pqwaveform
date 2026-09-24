"""JSON serialization for complete waveform-viewer history snapshots."""

from dataclasses import asdict
try:
    import json5
except ModuleNotFoundError:
    import json as _json
    import re as _re

    class _Json5Fallback:
        @staticmethod
        def loads(text):
            text = _re.sub(r"(?m)^\s*//.*$", "", text)
            return _json.loads(text)

        @staticmethod
        def dumps(value, **kwargs):
            kwargs.pop("quote_keys", None)
            return _json.dumps(value, **kwargs)

    json5 = _Json5Fallback()
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


def _relative_path(filename, base_directory):
    """Return a portable path relative to the history file directory."""
    path = Path(filename).expanduser()
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    try:
        return str(path.relative_to(base_directory))
    except ValueError:
        import os
        return os.path.relpath(path, base_directory)


def _resolved_path(filename, base_directory):
    """Resolve relative history paths while accepting legacy absolutes."""
    path = Path(filename).expanduser()
    if not path.is_absolute():
        path = base_directory / path
    return str(path.resolve())


def capture_model(model, base_directory=None):
    """Capture model state with portable paths relative to history."""
    base = Path(base_directory or ".").expanduser().resolve()
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
                    "marker_symbol": graph.marker_symbol,
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
                "path": _relative_path(data_file.path, base),
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


def restore_model(
    model, state, base_directory=None, build_saved_traces=True
):
    """Restore files and optionally the traces stored in the session."""
    base = Path(base_directory or ".").expanduser().resolve()
    model.blockSignals(True)
    model.files.clear()
    model.traces.clear()
    model.trace_order.clear()
    file_mapping = {}
    for item in state.get("files", []):
        for key, value in item.get("import_options", {}).items():
            setattr(model.options, key, value)
        current_id = model.load_file(
            _resolved_path(item["path"], base),
            aliases_from_comment=False,
        )
        file_mapping[item["uid"]] = current_id
    model.traces.clear()
    if not build_saved_traces:
        model.trace_order = []
        model.tabs = {0: "Tab 1"}
        model.tab_order = [0]
        model.active_tab_id = 0
        model.next_trace_id = 0
        model.active_trace_id = None
        model.add_trace("Trace 0")
        model.blockSignals(False)
        model.files_changed.emit()
        model.traces_changed.emit()
        model.tabs_changed.emit()
        model.aliases_changed.emit()
        return
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


def _multiline_to_json5(value):
    """Represent multiline strings as readable JSON5 line arrays."""
    if isinstance(value, str) and "\n" in value:
        return {"$multiline": value.splitlines()}
    if isinstance(value, dict):
        return {key: _multiline_to_json5(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_multiline_to_json5(item) for item in value]
    return value


def _multiline_from_json5(value):
    """Reconstruct multiline strings from the readable JSON5 form."""
    if isinstance(value, dict) and set(value) == {"$multiline"}:
        return "\n".join(value["$multiline"])
    if isinstance(value, dict):
        return {key: _multiline_from_json5(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_multiline_from_json5(item) for item in value]
    return value


def read_entries(filename=DEFAULT_HISTORY):
    """Read JSON5 history, including comments and legacy JSON files."""
    path = Path(filename)
    if not path.exists():
        return []
    payload = json5.loads(path.read_text(encoding="utf-8"))
    return _multiline_from_json5(payload).get("states", [])


def write_entries(entries, filename=DEFAULT_HISTORY):
    """Write commented JSON5 with readable multiline Python sections."""
    payload = _multiline_to_json5(
        _json_value({"version": 2, "states": entries})
    )
    Path(filename).write_text(
        json5.dumps(payload, indent=2, quote_keys=True),
        encoding="utf-8",
    )
