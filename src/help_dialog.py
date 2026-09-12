"""Tabbed Markdown help for PQWaveForm."""

from PyQt6 import QtWidgets


class HelpDialog(QtWidgets.QDialog):
    """Present application help and the complete public API."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PQWaveForm Help")
        self.resize(900, 680)
        layout = QtWidgets.QVBoxLayout(self)
        tabs = QtWidgets.QTabWidget()
        layout.addWidget(tabs)

        for title, markdown in self._pages().items():
            browser = QtWidgets.QTextBrowser()
            browser.setOpenExternalLinks(True)
            browser.setMarkdown(markdown)
            tabs.addTab(browser, title)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Close
        )
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @staticmethod
    def _pages():
        """Return ordered topic-specific Markdown pages."""
        return {
            "Shortcuts": """# Shortcuts

- `Ctrl+O`: open data files
- `Ctrl+D`: remove the selected file or calculated graph
- `Ctrl+T`: add a trace to the active tab
- `Ctrl+Shift+T`: add a trace tab
- `Ctrl+Alt+E`: expand all file-tree leaves
- `Ctrl+Alt+C`: collapse all file-tree leaves
- `Ctrl+Alt+V`: open leaves used by the active trace
- `Ctrl+Shift+E`: cycle file-tree leaf modes
- `Delete`: delete the active trace
- `Ctrl+G`: toggle all grids
- `Ctrl+L`: link or unlink all X axes
- `T`: toggle trackers
- `I`: toggle interpolated tracking for the active trace
- `H`: place a horizontal intersection marker at the mouse
- `V`: place a vertical intersection marker at the mouse
- `A`, `B`: place measurement markers
- `Ctrl+Alt+B`: clear A/B markers only
- `Ctrl+Alt+D`: open display and axis settings
- `Ctrl+E`: clear all markers in the active trace
- `Backspace`: remove the selected H/V marker line
- `Ctrl+S`: export the active trace
- `Ctrl+Shift+S`: export all traces
- `Ctrl+Alt+S`: export selected traces together as PDF or SVG
- - `Ctrl+Alt+L`: toggle the movable active-trace legend
- `Ctrl+R`: reload selected data, all data, and user scripts
- `Ctrl+Shift+H`: open searchable JSON history states
- `Ctrl+H`: horizontal A/B measurement layout
- `Ctrl+V`: vertical A/B measurement layout
- `Ctrl+mouse wheel`: horizontal-only zoom
- `Ctrl+Shift+mouse wheel`: vertical-only zoom
- `Ctrl+Shift+A`: show all non-X columns of the selected file
- `Ctrl+Shift+N`: hide all non-X columns of the selected file
- `Ctrl+Q`: exit
- `Tab`: IPython completion
- `Up`, `Down`: IPython history
""",
            "Overview": """# PQWaveForm

PQWaveForm is a multi-trace waveform viewer based on **PyQt6**,
**PyQtGraph**, and an embedded **IPython QtConsole**. Source columns and
calculated graphs share plotting, styling, alias, and export facilities.
""",
            "Getting started": """# Getting started

1. Open data with **Ctrl+O**.
2. Expand a full-width file row.
3. Select one **X** column and one or more **Y** columns.
4. Activate a trace by clicking its vertical label.
5. Use the resizable IPython console for calculations.

Uncompressed input supports UTF-8, UTF-8 BOM, UTF-16, CP1252, and Latin-1.
Pandas handles supported compressed input according to its file extension.
If automatic import fails, a settings dialog allows separator, comment,
header, skipped rows, and default X/Y columns to be corrected and retried.
Use Ctrl+R to reload changed source files while preserving display styles.
The File menu can clear the selected file or reset all files and aliases.
""",
            "File tree": """# File tree

The columns are `File / Graph`, `Alias`, `LC`, `X`, `Y`, `LW`, and `LS`.
File rows and the **Calculated graphs** row span all columns. The virtualized
QTreeView creates no persistent per-cell widgets, so files with hundreds of
columns remain responsive. The compact first column starts with the numeric
source-column index. Double-click Alias, LW, or LS to edit and double-click LC
to choose a color. Ctrl+wheel over LW changes width by 0.5 and
over LC cycles colors. X and Y are directly checkable.

`LS` supports **Solid**, **Dash**, **Dot**, **Dash-dot**, and
**Points only**. Points only draws a marker at every finite X/Y sample and
adds no connecting line. The LS dialog also offers **Show original
measurement points**, which overlays actual samples on any line style.
Alias and LW are editable by double-click or the edit key. Each loaded file
has its own X selection in every trace. Right-click a file to show or hide all
non-X columns or reload it.
""",
            "Calculated graphs": """# Calculated graphs

Calculated graphs appear below **Calculated graphs: _Trace name_** for the
active trace. Each graph owns independent X/Y arrays and supports:

- graph name and project-wide unique alias
- line or point color
- direct deletion in the tree
- persistent visibility
- line width or point size
- five line styles, including points only
- X selection, using the graph's Y array as source-curve X values

Right-click a calculated graph to delete it, save it, or save its trace.
Deleting a calculated graph removes its plot item, tree entry, and alias.
Deleting a trace removes every calculated graph owned by that trace.
""",
            "Traces": """# Traces

The trace table provides delete, X/Y links, fit, cursor, logarithmic axes,
and grid controls. At least one trace is always retained. A vertical trace
label activates a trace; double-clicking it opens display settings. Trace
heights are manually adjustable with the splitter handles between plots.
The Cursor cell selects Off, Sampled, or Interpolated tracking. Ctrl+H and
Ctrl+V independently change the A/B layout. Compact Legend and Grid checkboxes
and an editable Title column are also available. New
tabs own their traces, and closing a tab deletes its traces. **Clear traces**
replaces all traces in the current tab with one empty trace.
""",
            "IPython API": """# Complete IPython API

The console publishes `np`, `pd`, `project`, and these functions:

## `active_trace()`

Returns the active `Trace` object.

## `add_trace(name=None)`

Creates and activates an empty trace and returns its integer ID.

## `add_graph(y, x=None, name="graph", trace=None, alias="",
color=None, width=1.5, style=1, visible=True)`

Adds a calculated graph to the active or selected trace and returns a `Graph`.
If `x` is omitted, the selected source X array is reused when lengths match.
For a result one sample shorter, `x[1:]` is used; otherwise an index is made.
Styles accept `solid`, `dash`, `dot`, `dash-dot`, `points`, and
`points-only`.

```python
curve = add_graph(
    vout / vin,
    x=time,
    name="gain",
    alias="gain_curve",
    style="points",
)
```

## `new_trace(y=None, x=None, name="graph", trace_name=None, **style)`

Creates a trace and optionally adds its first calculated graph.

## `remove_graph(graph_or_id, trace=None)`

Deletes a calculated graph by object or UID and returns success as `bool`.

## `set_graph_style(graph_or_id, trace=None, **changes)`

Changes `name`, `alias`, `color`, `width`, `style`, `line_style`, or
`visible`, then updates plot, tree, and aliases.

## `add_marker_h(value, trace=None)`
Adds a movable horizontal line and draggable labels at every graph crossing.
## `add_marker_v(value, trace=None)`
Adds a movable vertical line and draggable labels at every graph crossing.
Use Python SI values such as `300e-3` and `3e-6`.
## `load_python_file(filename)`
Loads a Python file into the live namespace and records the operation for
history snapshots.
## `save_graph(graph_or_y, filename, x=None, x_name="x", y_name=None)`

Exports one `Graph` or an arbitrary Y array, optionally with an X array.
Compression is inferred from the filename.

## `save_trace(trace_id, filename)`

Exports all visible source and calculated curves of one trace.

## `save_traces(trace_ids, filename)`

Exports selected traces. Arrays of different lengths are padded with NaN.

## `save_all_traces(filename)`

Exports all traces through the same model export path.

## `set_axis(trace_id=None, **changes)`

Sets axis names, units, engineering mode, fonts, logs, or other trace fields.
`engineering=True` is accepted as an alias for `engineering_axes=True`.

## `clear_alias(name)`, `clear_all_aliases()`, and `prune_aliases()`
Remove one alias, every alias, or stale file references and synchronize the
embedded IPython namespace.

## `clear_traces(tab=None)` and `clear_all_files()`
Reset one tab's traces or reset the complete data and alias namespace.

The `project` object additionally exposes model operations such as
`load_file`, `remove_file`, `set_active_trace`, `set_alias`,
`set_column_style`, `set_x_column`, `set_y_column`, `find_graph`,
`alias_arrays`, `visible_curves`, and `load_palette`.
""",
            "User Python files": """# User Python files
Use **File > Load Python file into IPython** or repeat `-p FILE`,
`--python FILE`, or `--python-file FILE` on
the command line. Files execute in the live IPython namespace. Ctrl+R reloads
previously loaded files together with source data.
""",
            "Legends and titles": """# Legends and titles
Use **Ctrl+Alt+L** to toggle the movable legend. Legend display names are
editable through the View menu and accept HTML `<sub>` and `<sup>` tags.
Legend font size is selected in Display settings. The plot title is edited in
**Trace > Display and axis settings** or by
double-clicking the Trace cell in the trace list.
""",
            "Saving": """# Saving

```python
save_graph(curve, "gain.csv.gz")
save_trace(0, "trace.csv")
save_traces([0, 2], "selected.csv.xz")
save_all_traces("all_traces.csv.gz")
```

Exports contain visible source curves and visible calculated graphs. PDF and
SVG clip curves to the current data rectangle without changing model arrays.
""",
            "Axes and units": """# Axes and engineering units

```python
set_axis(
    x_name="Time",
    x_unit="s",
    y_name="Voltage",
    y_unit="V",
    engineering=True,
)
```

Engineering ticks use powers of 1000 and SI prefixes on linear and logarithmic
axes. Display settings also
control axis-title, tick-label, marker-label, legend-label fonts, and
differential-label layout. Persistent marker labels have individual RMB
alignment controls.
""",
            "Markers": """# Tracker and markers

Move the tracker near a visible curve and press **A** or **B**. Marker labels
and the result label are draggable. The result displays `dx`, `dy`, `1/dx`,
`1/dy`, and slope `k`. Optional interpolation tracks between finite samples.
`H` and `V` immediately create movable intersection lines at the current mouse
coordinate. Double-click or right-click a line to enter an exact value. Every
intersection label uses the configured Marker font. **Ctrl+E** clears A/B and
all H/V intersection markers. Marker label backgrounds are transparent and
their positions survive
refreshes. The A/B measurement line and arrows can be dragged together. In H
mode they move vertically; in V mode they move horizontally. The View menu can
clear only A/B markers, while Ctrl+E clears every marker. Select an H/V line
and press Delete or Backspace to remove that marker alone. Marker deletion
is relayed by a class-level signal of the owning trace widget. It
unregisters the marker before removing its line, points, and labels.
H/V lines retain
their yellow marker color. A five-pixel viewport grab zone
provides reliable dragging independently of InfiniteLine hit testing. Vertical
markers show a horizontal double-arrow cursor and horizontal markers show a
vertical double-arrow cursor. A click selects a line for Delete or Backspace;
right-click or double-click opens exact coordinate editing. The A/B helper is
a finite-looking native pyqtgraph line, so it does not block plot pan, zoom,
right-click, or H/V marker interaction outside the displayed helper
span.
""",
            "History": """# History
**File > History states** searches, saves, and restores named states with short
descriptions. The selector uses Date, Name, and Description columns. Dates use
`YYYY-MM-DD HH:MM` and are searchable. Multiple rows can be selected and
removed with **Delete selected**. The
default `pqwaveform_history.json` is in the current working
directory. A state includes files, columns, graphs, axes, traces, tabs, ranges,
Python code is stored as setup code and per-trace code. During restore,
setup runs first. Each trace is then activated before its assigned code
runs. The closing state is saved automatically. **Open history file**
selects another JSON file.

To save a reproducible state:
1. Enter a name and description.
2. Review the editable central **Source** command history.
3. Copy shared initialization into **Before traces**.
4. Copy graph-building commands into each matching trace code tab.
5. Review every section and press **Save current**.

Restore asks once before running code. Files and aliases are restored first.
Each trace is created, activated, and its assigned code is executed. Saved
graph metadata is applied before widgets and visual state is restored.
This includes titles, legends, ranges,
splitters, A/B and H/V markers, coordinates, label positions, and alignments.
Window geometry, dock and console visibility, splitter dimensions, and
size-independent legend positions are restored before markers.
Canceling code execution still restores the non-code state.
""",
            "Palettes": """# Color palettes

Palette files are CSV or TXT tables with `R`, `G`, and `B` columns. `A` or
`ALPHA` is optional. RGB values receive alpha 255 automatically.
The built-in palette provides 40 contrasting colors designed for dark
plot backgrounds.
""",
        }
