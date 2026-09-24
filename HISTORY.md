# PQWaveForm release history

## Version 4.2.5 additions

### Compact file tree

Source-file rows and the **Calculated graphs: _Trace name_** row span all
seven columns. The first column starts at 150 pixels instead of expanding to
fit long group names. Alias, color, X/delete, Y, width, and style controls use
explicit compact widths and are visible immediately when the GUI opens. Every
section remains manually resizable.

### Points-only rendering

The LS control now offers **Points only** for source columns and calculated
graphs. This mode draws only the samples actually present in the imported or
calculated arrays. It does not interpolate or connect adjacent samples.

From IPython:

```python
curve = add_graph(
    measured_y,
    x=measured_x,
    name="samples",
    style="points",
)

set_graph_style(curve, style="points-only", width=2.0)
project.set_column_style(file_id, column, style="points")
```

For points-only graphs, `width` influences the marker outline and marker size.

## Complete public model and console API

The embedded namespace contains NumPy as `np`, pandas as `pd`, the central
model as `project`, and the following convenience functions:

- `active_trace()` returns the active `Trace` object.
- `add_trace(name=None)` creates and activates an empty trace.
- `add_graph(...)` creates a calculated graph and returns its `Graph` object.
- `new_trace(...)` creates a trace and optionally its first graph.
- `remove_graph(graph_or_id, trace=None)` deletes a calculated graph.
- `set_graph_style(...)` changes graph name, alias, color, width, style, or
  visibility.
- `save_graph(...)` exports one graph or arbitrary X/Y arrays.
- `save_trace(trace_id, filename)` exports one trace.
- `save_traces(trace_ids, filename)` exports selected traces.
- `save_all_traces(filename)` exports every trace.
- `set_axis(trace_id=None, **changes)` changes axis and display settings.

The `project` object also provides these public model operations:

- `load_file(filename, aliases_from_comment=True)`
- `remove_file(file_id)`
- `set_active_trace(trace_id)`
- `set_x_column(file_id, column)`
- `set_y_column(file_id, column, visible)`
- `set_column_style(file_id, column, **changes)`
- `set_alias(file_id, column, value)`
- `find_graph(graph_or_id, trace=None)`
- `alias_arrays()`
- `visible_curves(trace_id)`
- `load_palette(filename)`

See the in-program **IPython API** help tab for signatures, behavior, and
examples. The **Shortcuts** tab is intentionally the leftmost help tab.

## Version 4.2.6 additions

### Trace tabs

Traces are organized in tabs. Use **Trace > Add trace tab** or
`Ctrl+Shift+T` to create a tab with its first trace. Tabs can be renamed or
closed. Closing a tab retains its traces by moving them to another tab. The
trace table shows the traces belonging to the active tab.

### Per-tab and per-trace file-tree state

Expanded file and calculated-graph leaves are remembered independently for
each tab and trace. A new trace starts with all leaves collapsed. Loading a
file opens its leaf when a default Y graph is visible, and `add_graph()` opens
the calculated-graphs leaf of the owning trace.

File-tree commands are available in the **View** menu:

- `Ctrl+Alt+E`: expand all leaves
- `Ctrl+Alt+C`: collapse all leaves
- `Ctrl+Alt+V`: open only leaves used by the active trace
- `Ctrl+Shift+E`: cycle through all, none, and visible-only modes

## Version 4.2.7 additions

### Fast virtualized file tree

The file tree now uses `QTreeView`, `QAbstractItemModel`, and a delegate. It no
longer creates thousands of persistent editors, buttons, and checkboxes for
wide files. Editors exist only while a cell is edited, and rows outside the
viewport are not painted. Repeated refresh requests are coalesced through the
Qt event loop. Tab changes reuse existing tab pages and trace widgets.

File and calculated-graph group rows span the full tree width. The first
column is narrower and displays the numeric source-column index followed by
the source label. Double-click Alias, LW, or LS to edit. Double-click the LC
color swatch to select a color. X and Y remain checkable columns.

### Calculated graph as X axis

The X checkbox of a calculated graph selects its Y array as the X axis for
source curves in that trace. Selecting a source X column clears calculated-X
selection. Deleting the selected calculated graph safely clears that choice.

Features 1, 2, 3, 15, and 16 are marked DONE in the wanted-feature list.

## Version 4.2.8 additions

Features 17 through 22 are complete. Failed or ambiguous imports open a retry
dialog for separator, comment prefix, header, skipped rows, and default X/Y
columns. The LS dialog can overlay original sample points on every line style.
The active trace supports a movable legend (`Ctrl+Alt+L`), editable display
names with HTML `<sub>` and `<sup>`, and an editable plot title. Alias and LW
cells in the QTreeView are editable by double-click or the edit key.

Selected traces can be exported as a multi-page PDF with white, black, or
transparent background through **File > Export traces as PDF** or
`Ctrl+Alt+S`. Plot titles are edited in the display-settings dialog.

## Version 4.2.9 additions

Features 10, 11, 12, and 23 are complete. Traces inside each tab now use a
vertical splitter, so every trace height can be adjusted manually. The Cursor
cell provides Off, Samples, and Interpolated modes; `I` toggles interpolation
for the active trace. Interpolation is optional and linearly tracks between
adjacent finite samples.

`H` and `V` add movable horizontal or vertical marker lines. Every crossing
with a displayed graph receives a marker point and draggable coordinate label.
The IPython API provides `add_marker_h(value, trace=None)` and
`add_marker_v(value, trace=None)`. Numeric SI notation remains ordinary Python,
for example `300e-3` and `3e-6`.

PDF pages are cropped to the visible plot area instead of an A4 sheet. The
plot, axes, title, legend, AB markers, and intersection markers are rendered.

## Version 4.3.0 additions

All remaining wanted features are complete. The active vertical trace label
uses the current Qt theme highlight colors. Calculated graphs have a context
menu for delete, graph export, and trace export. Source-file context menus and
`Ctrl+Alt+A` / `Ctrl+Alt+N` show or hide all non-X columns.

Each source file now retains its own selected X column per trace. Engineering
SI tick labels also work on logarithmic axes. `Ctrl+H` and `Ctrl+V` select
horizontal or vertical A/B measurement layout, and the Cursor table cell
combines sample/interpolated tracking with that orientation. Ctrl-wheel zooms
only X; Ctrl-Shift-wheel zooms only Y.

Python files can be loaded into the live IPython namespace from the File menu
or repeatedly with `--python-file FILE`. `Ctrl+R` reloads the selected source
file, or all files if no source file is selected, and reloads user scripts.

PDF export now starts from pyqtgraph's SVGExporter and renders that SVG to a
cropped PDF through QtSvg. This preserves plot vectors, legends, and marker
graphics. Marker label foreground and fill colors adapt to the chosen PDF
background.

## Version 4.3.1 correction

PDF export now changes pyqtgraph `TextItem.fill` brushes directly because
`TextItem` has no `setFill()` method. Original marker label fills and text
colors are captured before SVG export and restored afterwards.

## Version 4.3.2 corrections

PDF export now maps SVG output to the complete PDF paint rectangle at a fixed
96 DPI, preventing oversized pages with a tiny plot. Export is fully opaque
for frames, marker lines, and marker points; only transparent output remains
transparent. Marker label colors are restored after export.

`Ctrl+Shift+A` and `Ctrl+Shift+N` are application-wide and retain the last
selected source file after focus moves to a trace. Active trace labels are
painted directly with the Qt highlight palette. `-p`, `--python`, and
`--python-file` load Python files. All marker labels use the configured marker
font size.

Double-click the Trace cell to edit its plot title. Cursor choices now control
nearest-sample versus interpolated tracking and horizontal versus vertical A/B
measurement layout. H and V immediately place an intersection marker at the
mouse coordinate; double-click or right-click its line to edit the value.

## Version 4.3.3 additions

Features 26 through 31 are complete. PDF output remains an SVG-to-PDF vector
pipeline and explicitly rejects SVG image elements. Plot titles, axis titles,
ticks, legends, curves, and marker graphics are exported. Marker TextItems no
longer have rectangular fill brushes, so their backgrounds are transparent in
the trace and PDF.

The built-in dark-background palette contains 40 contrasting colors. Marker
label positions survive curve refreshes and font changes. The A/B measuring
line and arrows form a movable graphics group. Display settings provide left
or right marker-text alignment for tracker, A/B, result, H, and V labels.

**File > History states** (`Ctrl+Shift+H`) manages named and described states
in `pqwaveform_history.json` in the current working directory. The searchable
dialog can save or restore states. **Open history file** accepts another JSON
file. States include source paths and import options, columns, styles, graphs,
traces, tabs, ranges, tree expansion, legends, markers, label positions, and
splitter sizes. The latest session is stored automatically when closing.

## Version 4.3.4 corrections

A/B labels are placed above the movable measurement group and remain directly
draggable. Grid toggling updates plots in place and no longer rebuilds trace
widgets, preserving all markers and labels. Ctrl+E now removes A/B and H/V
markers.

History actions ignore QAction's boolean signal argument, and JSON conversion
is recursive for NumPy scalars and nested view state. The history selector is
a two-column Name/Description table. Saving the current state writes the
default JSON history file without interpreting a boolean as a path.

PDF export renders the complete PlotWidget scene rectangle to vector SVG, so
X/Y axis titles, tick labels, plot titles, legends, markers, and curves are
included before conversion to the cropped PDF page.

## Version 4.3.5 additions and corrections

Features 32 through 36 are complete. The A/B helper group is constrained to
vertical movement in H mode and horizontal movement in V mode. Its default
label offset is smaller, manual result-label positions survive refreshes, and
A/B markers can be cleared separately from H/V markers.

H/V marker lines are selectable and can be removed individually with Delete
or Backspace. Editing a marker coordinate reuses existing labels instead of
creating duplicate label graphics. Ctrl+E still clears every marker.

The raster-image rejection in PDF export was removed so valid SVG/PDF output
is not blocked. The History table now has Date, Name, and Description columns;
date is searchable, multiple states can be selected, and Delete selected
removes them from the JSON file.

New tabs and their initial traces are created atomically. Ctrl+T therefore
adds a trace only to the active tab. Closing a tab deletes the traces owned by
that tab instead of moving them into another tab.

## Version 4.3.7 correction

Axis labels are QGraphicsTextItem objects. Plot theming now uses
`setDefaultTextColor()` for X/Y axis labels instead of the unavailable
`setAttr()` method. Title and legend labels continue using their pyqtgraph
label APIs. Version 4.3.7 also retains the background and relative marker-label
features introduced for 4.3.6.

## Version 4.3.8 interaction and theme corrections

H/V marker lines now sit above the A/B measurement group, use the full hover
band as their mouse shape, and explicitly take selection and keyboard focus at
mouse press and throughout dragging. This prevents the previously moved A/B
helper from continuing to receive a drag intended for an H/V line.

Black/white theming now includes plot-title text, A/B helper lines and arrows,
A/B reference lines, H/V marker lines, marker circles, axis labels, legend
text, and all marker labels. Qt QGraphicsTextItem objects use
`setDefaultTextColor()` through a type-safe helper.

## Version 4.3.9 interaction architecture

The movable native `QGraphicsItemGroup` used for the A/B helper was replaced
by a native pyqtgraph `InfiniteLine` whose visible span is restricted to the
A/B interval. The helper remains draggable only in the intended direction,
while right-click, zoom, pan, and H/V marker events remain available to the
plot. Existing history files remain compatible through the stored two-value
helper offset.

H/V markers again rely on the original `InfiniteLine` hover and drag behavior.
Their line and hover widths are 1.5 pixels, matching the compact interaction
of v4.3.2. Right-click editing and left-click selection are claimed only as
clicks and do not replace native drag handling. Marker colors remain yellow,
orange, and teal; background theming changes axes, title, legend, and neutral
text only. Plot-title color is applied to the contained Qt text item as well
as the pyqtgraph label wrapper. Interactive marker items are in
`marker_items.py`, and text theming is in `plot_theme.py`.

## Version 4.3.11 viewport marker interaction

H/V marker dragging now uses a PlotWidget viewport event filter, based on the
verified standalone test. Hit testing is performed in viewport pixels with a
constant five-pixel grab radius. The displayed marker remains an InfiniteLine,
but it is not responsible for mouse-event ownership. This removes dependency
on InfiniteLine bounding-rectangle caching and pyqtgraph MouseDragEvent
generation. A horizontal double-arrow cursor is shown for vertical markers,
and a vertical double-arrow cursor for horizontal markers. Pan, wheel zoom,
and plot right-click remain available outside a marker's grab zone.

The same controller handles right-click and double-click coordinate editing,
selection, Delete/Backspace, multiple markers, and controller cleanup. Features
40 through 43 are also complete: plot titles and A/B helpers follow the theme,
the A/B helper is inset below its arrows, Ctrl+G refreshes grid checkboxes, the
PDF source rectangle uses viewport coordinates, and the active trace can be
exported as SVG from File > Export active trace as SVG or Ctrl+Alt+G.

## Version 4.3.11 marker-controller lifecycle correction

The viewport event filter no longer calls `plot.viewport()` while handling an
event. Qt may already have deleted the PlotWidget C++ object while deferred
events are still being dispatched. MarkerController now stores the viewport
once, uses it as its QObject parent, and compares the watched object only with
that cached Python reference. Plot and viewport `destroyed` signals deactivate
the controller, clear markers, and discard all Qt references. Trace rebuilding
also calls `shutdown()` before scheduling old pages with `deleteLater()`.

## Version 4.3.11 marker deletion signal correction

`TraceWidget` now declares `marker_delete_requested` as a class-level PyQt
signal before its constructor connects the MarkerController. The signal relays
a selected IntersectionMarker to MainWindow, which unregisters the marker and
removes its line, points, and labels. A static regression test verifies that
the declaration cannot be omitted again.

## Corrected v4.3.11 marker-signal build

This corrected v4.3.11 build declares the TraceWidget marker deletion relay as
a class-level PyQt signal before connecting MarkerController. Marker removal
is idempotent and unregisters the controller reference before deleting any
graphics item. A dedicated AST regression test validates signal declaration,
connection, controller shutdown, and deletion order without requiring a GUI.

## Version 4.3.11 completed features

Features 48 through 55 are complete. PDF and SVG now share pyqtgraph's native
SVGExporter output before QtSvg converts selected traces to PDF. Theme changes
apply title color immediately and once more after the event loop. H/V vertex
crossings are deduplicated; Backspace works through the focused viewport.

The trace table has compact Zoom, Cursor, Legend, Log Axis, and Grid controls
and an editable wide Title column. Cursor choices are Off, Sampled, and
Interpolated; A/B orientation remains controlled by Ctrl+H and Ctrl+V. Marker
labels, cursor values, and A/B results use SI engineering notation whenever
engineering axes are enabled.

History states can include a selectable suffix of IPython commands. The
`load_python_file()` API is published in IPython and logged when scripts are
loaded. Ctrl+Q saves the final state and code, while Ctrl+Shift+Q exits without
a final history snapshot. Delete no longer removes a trace; F fits the active
plot.


## Version 4.3.12

Features 56 through 61 are complete. History code is stored in an editable
text area, calculated graphs are recreated only after the user reviews the
stored code and presses Run, and legend visibility plus position survive a
history round trip. Trace titles are directly editable in the Title cell.
Plot appearance is applied through one centralized theme function.

PDF and SVG now share one Export plots dialog and selected traces are stacked
on one vector sheet. In the file tree, Ctrl+mouse wheel changes line width in
0.5 steps or cycles the palette over LC cells; tooltips describe these hidden
controls. Engineering labels use pyqtgraph.siFormat with a compatibility
fallback.


## Version 4.3.13

The plot legend now uses a deterministic native pyqtgraph LegendItem lifecycle.
Entries are explicitly rebuilt, and native label color and font-size APIs keep
the legend consistent with black and white plot backgrounds. Legend font size
is adjustable in Display settings.

Ctrl+Alt+B clears A/B markers, and Ctrl+Alt+D opens Display settings. The old
global marker-label alignment has been removed. Right-click any persistent A,
B, result, H, or V marker label to choose Left, Center, or Right independently.
Each label's position and alignment are stored and restored by History.


## Version 4.3.14

Feature 63 is complete. Backspace is routed to the active trace marker
controller, Ctrl+E clears markers only in the active trace, and persistent
marker labels reliably claim right-clicks for individual alignment. H/V line
widths use one consistent normal and hover policy.

Legend color and font size are forced immediately after entries are rebuilt
and again by the centralized queued theme pass. Display-dialog title changes
are synchronized with the trace table. History code is divided into a setup
section and per-trace sections. Selected central history text can be copied to
any section. Restore requests consent once, runs setup after files and aliases
exist, then activates each trace before running its assigned code.

## Version 4.3.15

- Fixed TextItem hover handling without calling a missing base hoverEvent.
- Protected the virtual tree from stale trace, file, and graph indexes.
- Restored trace code before rebuilding widgets and restoring marker state.
- Added Clear traces, Clear file, and Clear all files menu commands.
- Added alias clearing and pruning APIs for the embedded IPython namespace.
- Moved version notes from README.md into HISTORY.md.

## Version 4.3.16

- History now stores every user-editable calculated-graph metadata field while
  continuing to exclude numerical X/Y arrays.
- After trace-specific Python recreates graphs, restore matches them by alias
  or by name plus occurrence and restores name, alias, color, line width, line
  style, visibility, sample-point overlay, legend name, and X selection.
- Graph metadata is applied before trace widgets and markers are restored.

## Version 4.3.17

- PDF/SVG export clips temporary polyline copies to the visible X/Y rectangle
  with Liang-Barsky clipping and always restores original plot-item data.
- History stores window geometry, dock layout and visibility, console
  visibility, main splitter sizes, and per-tab trace splitter sizes.
- Legend positions are PlotItem-relative and restored after layout settles.

## Version 4.3.18
- Preserves existing markers and legend positions when traces are added.
- Keeps clipped export polylines contiguous so dash patterns remain visible.
- Replaces Points only with None and adds six sample-marker symbols.
- Handles missing delegate style options on affected Linux Qt builds.
- Adds Open advanced with a live 20-row import preview and CLI option.
- Sets the default line width to 1.0 and enables automatic peak downsampling.

## Version 4.3.19
- History deletion now updates the list without closing the dialog.
- The advanced import dialog and its preview table are substantially larger.
- History stores source files relative to the history JSON directory and still accepts legacy absolute paths.
- View capture ignores stale trace widgets during asynchronous model and GUI rebuilds, preventing KeyError.

## Version 4.3.20
- Existing history states can be overwritten after an explicit confirmation.
- Dock widgets now have stable object names, removing QMainWindow saveState warnings.
- File-tree refreshes preserve horizontal and vertical scrollbar positions.
- Source and graph rows support persistent multi-selection, multiple ranges, Ctrl+RMB addition, and bulk color, width, and line-style changes.

## Version 4.3.21
- Persistent multi-selection is highlighted with a blue row background and diamond marker.
- Left and optional right plot axes are aligned across traces in each tab and vector export.
- Stale file-tree nodes no longer raise KeyError after file removal or asynchronous refresh.
- History is written as commented JSON5; multiline Python is represented as readable line arrays.
- The history code dialog appears before saved traces are built and can skip them when code creates traces. Saved trace metadata is mapped to generated traces by name and order.

### Version 4.3.21 correction
- Removed an accidental recursive call from `align_tab_axes()`.
- Axis width measurement now uses the existing graphics geometry and never processes nested Qt events.

## Version 4.3.22
- Restores source aliases before approved history Python runs when saved traces are skipped.
- Deletes multi-selected calculated graphs together.
- Enables or disables Y for multi-selected source and calculated rows.
- New traces and files start without an automatically selected Y curve.
- History selection immediately fills all saved Python code editors.

## Version 4.3.23
- Builds History code tabs dynamically from the selected state and safely returns to the current trace structure for overwrite.
- Adds `--version` command-line output and documents it in help.
- Replaces scattered multi-selection actions with one complete editor dialog opened by RMB or double-click.
- Adds plot-focus `O`, a trace-table Options button, and per-setting Apply-to-tab checkboxes.
- Corrects repeated HISTORY headings using the preserved feature and regression-test chronology.

## Version 4.3.24
- Doubles the Display settings width and narrows the Apply-to-tab column.
- Adds unlimited movable numbered point markers with draggable coordinate labels and History persistence.
- Adds per-trace V lock to synchronize vertical markers by X coordinate across locked traces in a tab.

## Version 4.3.25
- Makes `O` the application-wide menu shortcut for title and axis settings.
- Applies Marker font changes to numbered point-marker labels.
- Constrains numbered markers to visible curves in sampled or interpolated mode.
- Adds Show current session code and preserves current editor contents in History.
