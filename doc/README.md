# PQWaveForm Qt6 with embedded IPython

PQWaveForm v4.3.17 is a PyQt6 and PyQtGraph waveform viewer with deterministic Python-built UI and an embedded Jupyter QtConsole. It supports multiple traces, source and calculated graphs, live aliases, engineering axes, movable measurement labels, compressed input, and data export.

## Installation and start

```bash
python -m pip install -r requirements.txt
python pqwaveform.py
python pqwaveform.py -x 0 -y 1 2 measurement.csv
```

The QtConsole is resizable with the horizontal splitter. It uses a dark Monokai-style presentation. Long in-process IPython calculations can temporarily block the GUI.

## Loading data and encodings

Use **File > Open** or `Ctrl+O`. Uncompressed CSV, TSV, TXT, and DAT files are detected as UTF-8, UTF-8 with BOM, UTF-16 LE/BE, Windows-1252, or Latin-1. Invalid isolated characters are replaced rather than aborting the numeric import. Pandas handles supported compressed inputs according to their extension.

A leading commented line can define labels and initial aliases:

```text
# time,vin,vout
0.0,0.1,1.2
0.1,0.2,1.4
```

Its field count must match the numeric columns. Invalid alias characters become underscores; duplicates and Python keywords are skipped.

## File tree

Each filename occupies a full-width merged row and the tooltip contains its full path. Expand the file to use:

- `Alias`: short live IPython name such as `time`, `vin`, or `vout`
- `LC`: line color from the loaded palette
- `X`: common X column for the active trace
- `Y`: visible source graph
- `LW`: line width
- `LS`: solid, dash, dot, or dash-dot style

The file row remains readable even when the compact control columns are narrow.

## Traces

Click a vertical trace label to activate it. Double-click it to open display settings. The trace table provides delete, X/Y links, fit, cursor, logarithmic axes, and grid controls. `Ctrl+T` adds a trace, `Ctrl+G` toggles all grids, and `Ctrl+L` toggles all X links.

## IPython console and graph API

The QtConsole provides shared input/output, history, completion, syntax highlighting, colored exceptions, pretty printing, magics, and object inspection. Use `%whos`, Tab, `name?`, and `name??`.

Preloaded names:

```python
np
pd
project
active_trace
add_trace
add_graph
new_trace
remove_graph
save_graph
save_trace
save_traces
save_all_traces
set_axis
```

Add a calculated graph to the active trace:

```python
gain = vout / vin
curve = add_graph(gain, x=time, name="gain", alias="gain")
```

With style settings:

```python
curve = add_graph(
    gain,
    x=time,
    name="gain",
    alias="gain_curve",
    color="#ff8800",
    width=2.0,
    style="dash",
)
```

Add to an existing trace:

```python
add_graph(vout - vin, x=time, name="difference", trace=1)
```

Create an empty trace or create one together with a graph:

```python
tid = add_trace("Calculated")
add_graph(np.gradient(vout, time), x=time, name="dvout_dt", trace=tid)

new_tid = new_trace(
    np.diff(vout),
    x=time[1:],
    name="dvout",
    trace_name="Derivative",
)
```

When `x` is omitted, the selected X column is used if its length matches. For a result one element shorter, its `x[1:]` values are used. Otherwise an index axis is generated.

Remove a calculated graph:

```python
remove_graph(curve)
remove_graph(curve.uid)
```

## Saving graphs and traces

```python
save_graph(curve, "gain.csv")
save_graph(curve, "gain.csv.gz")
save_graph(gain, "gain.tsv", x=time, x_name="time", y_name="gain")
save_trace(tid, "trace.csv")
save_traces([0, 2], "selected.csv.xz")
save_all_traces("all_traces.csv.gz")
```

The GUI offers active-trace export with `Ctrl+S` and all-trace export with `Ctrl+Shift+S`.

## Axes and engineering units

Use **Trace > Display and axis settings** or `set_axis()`:

```python
set_axis(
    x_name="Time",
    x_unit="s",
    y_name="Voltage",
    y_unit="V",
    engineering=True,
)
```

Engineering mode uses powers of 1000 and SI prefixes such as `p`, `n`, `u`, `m`, `k`, `M`, `G`, and `T`. Disable it with `set_axis(engineering=False)`. The dialog also controls axis-label, tick-label, and marker fonts plus the vertical differential-label offset.

## Tracking and markers

Move near a plotted curve and press `A` or `B`. Marker labels and the result label can be dragged. The compact result shows `dx`, `dy`, `1/dx`, `1/dy`, and slope `k`. `Ctrl+E` clears markers.

## Palettes

Palette files may be `.csv` or `.txt` and require `R`, `G`, and `B`; optional alpha is `A` or `ALPHA`.

## Tests

```bash
python tests/test_static.py
python tests/test_encodings.py
QT_QPA_PLATFORM=offscreen python tests/test_offscreen.py
```

## Calculated graphs in the file tree

Calculated graphs are owned by one trace and displayed below the separate
**Calculated graphs: _Trace name_** top-level row for the active trace. They do
not use the common source X radio button because every calculated graph stores
its own X array.

The tree provides the following controls for each calculated graph:

- editable, project-wide unique Python alias
- palette-based line color
- delete button in the X-column position
- persistent visibility checkbox
- line width editor
- solid, dash, dot, or dash-dot line style

Changes made in the tree update the plot and IPython namespace immediately.
The same properties can be changed from IPython:

```python
set_graph_style(
    curve.uid,
    alias="gain_curve",
    color=(0, 204, 136, 255),
    width=3.0,
    style="dot",
    visible=True,
)
```

`remove_graph(curve)` and `remove_graph(curve.uid)` remove the graph, tree row,
plot curve, and alias. Deleting a trace removes all calculated graphs and
aliases owned by that trace.

## Project data structure

`ProjectModel` owns loaded `DataFile` objects and all `Trace` objects. Each
trace owns source-column `Style` objects as well as its `Graph` list. A
calculated `Graph` stores independent X/Y arrays, alias, RGBA color, line
width, line style, and visibility. GUI code edits the model and reacts to model
signals rather than owning duplicate graph state.

## Validation

```bash
python tests/test_static.py
python tests/test_model.py
python tests/test_encodings.py
python -m py_compile *.py tests/*.py
```

The offscreen GUI test remains included but is not required for the v4.2.4
validation pass requested for this intermediate version.

## Saving a history state

1. Open **File > History states**.
2. Enter a descriptive state name and a short description.
3. Review the editable IPython command history in the **Source** tab.
4. Select shared setup code, choose **Before traces**, and press
   **Copy selection**. This section must not depend on an active trace.
5. Select graph-building commands for a trace, choose that trace as the
   destination, and press **Copy selection**.
6. Review all per-trace tabs and remove commands that must not be replayed.
7. Press **Save current**. Calculated graph arrays are recreated from code.
   Their metadata is stored independently: name, alias, color, line width,
   line style, visibility, sample-point overlay, legend name, and X selection.

Restore asks once for permission to execute all code. Files and aliases are
restored first. Every trace then exists in the model. For each trace, PQWaveForm
activates that trace and executes its assigned Python code. Only after all code
has finished, all saved calculated-graph metadata is applied. Widgets are
then rebuilt and the visual state is restored. The final pass
restores titles, legends, ranges, splitters, A/B markers, H/V markers, marker
coordinates, label positions, and label alignments. If code execution is
canceled, the application still restores the non-code state.

## Clearing data and aliases

- **Trace > Clear traces** replaces all traces in the active tab with one empty
  trace.
- **File > Clear file** removes the selected file and its source curves and
  aliases from every trace and from IPython.
- **File > Clear all files** resets files, calculated graphs, traces, and
  aliases, then creates one empty default trace.
- `clear_alias(name)` removes one named alias.
- `clear_all_aliases()` removes all model-owned aliases.
- `prune_aliases()` removes stale references and refreshes the IPython
  namespace.

Release notes are maintained in [HISTORY.md](HISTORY.md).

## Vector export clipping and GUI history

PDF and SVG clip temporary copies of visible polylines to the current X/Y
data rectangle. Original PlotDataItem arrays are restored in a `finally` block.
History stores window geometry, dock layout and visibility, console visibility,
main and trace splitter sizes. Legend positions are stored relative to current
PlotItem dimensions and restored after the saved GUI layout has settled.
