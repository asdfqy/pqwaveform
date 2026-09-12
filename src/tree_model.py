"""Virtualized file and graph tree for large data sets."""

from dataclasses import dataclass, field

from PyQt6 import QtCore, QtGui, QtWidgets


HEADERS = ("Column", "Alias", "LC", "X", "Y", "LW", "LS")
STYLE_NAMES = ("Solid", "Dash", "Dot", "Dash-dot", "Points only")


@dataclass
class TreeNode:
    """Small non-widget node used by the item model."""

    kind: str
    key: tuple
    label: str
    parent: object = None
    children: list = field(default_factory=list)


class FileGraphTreeModel(QtCore.QAbstractItemModel):
    """Expose source columns and graphs without per-cell widgets."""

    action_requested = QtCore.pyqtSignal(tuple, int)

    def __init__(self, project, parent=None):
        super().__init__(parent)
        self.project = project
        self.trace_id = project.active_trace_id
        self.root = TreeNode("root", (), "")
        self.rebuild()

    def rebuild(self, trace_id=None):
        """Recreate lightweight nodes for the selected trace."""
        if trace_id is not None:
            self.trace_id = trace_id
        self.beginResetModel()
        self.root.children = []
        trace = self.project.traces.get(self.trace_id)
        if trace is None:
            self.endResetModel()
            return
        for file_id, data_file in self.project.files.items():
            group = TreeNode(
                "file", ("file", file_id), data_file.name, self.root
            )
            group.children = [
                TreeNode(
                    "source",
                    ("source", file_id, column),
                    str(column),
                    group,
                )
                for column in range(len(data_file.labels))
            ]
            self.root.children.append(group)
        group = TreeNode(
            "calculated",
            ("calculated", self.trace_id),
            f"Calculated graphs: {trace.name}",
            self.root,
        )
        group.children = [
            TreeNode("graph", ("graph", graph.uid), graph.name, group)
            for graph in trace.graphs
        ]
        self.root.children.append(group)
        self.endResetModel()

    def node(self, index):
        """Return the node represented by an index."""
        return index.internalPointer() if index.isValid() else self.root

    def index(self, row, column, parent=QtCore.QModelIndex()):
        parent_node = self.node(parent)
        if 0 <= row < len(parent_node.children):
            return self.createIndex(row, column, parent_node.children[row])
        return QtCore.QModelIndex()

    def parent(self, index):
        if not index.isValid():
            return QtCore.QModelIndex()
        parent_node = self.node(index).parent
        if parent_node is None or parent_node is self.root:
            return QtCore.QModelIndex()
        grandparent = parent_node.parent
        row = grandparent.children.index(parent_node)
        return self.createIndex(row, 0, parent_node)

    def rowCount(self, parent=QtCore.QModelIndex()):
        if parent.isValid() and parent.column() != 0:
            return 0
        return len(self.node(parent).children)

    def columnCount(self, parent=QtCore.QModelIndex()):
        del parent
        return len(HEADERS)

    def headerData(self, section, orientation, role):
        if (
            orientation == QtCore.Qt.Orientation.Horizontal
            and role == QtCore.Qt.ItemDataRole.DisplayRole
        ):
            return HEADERS[section]
        return None

    def flags(self, index):
        if not index.isValid():
            return QtCore.Qt.ItemFlag.NoItemFlags
        node = self.node(index)
        flags = QtCore.Qt.ItemFlag.ItemIsEnabled
        flags |= QtCore.Qt.ItemFlag.ItemIsSelectable
        if node.kind in ("source", "graph"):
            if index.column() in (1, 5):
                flags |= QtCore.Qt.ItemFlag.ItemIsEditable
            if index.column() in (3, 4):
                flags |= QtCore.Qt.ItemFlag.ItemIsUserCheckable
        return flags

    def data(self, index, role=QtCore.Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        node = self.node(index)
        column = index.column()
        if role == QtCore.Qt.ItemDataRole.UserRole:
            return node.key
        if role == QtCore.Qt.ItemDataRole.ToolTipRole:
            return self._tooltip(node, column)
        if role == QtCore.Qt.ItemDataRole.FontRole and node.parent is self.root:
            font = QtGui.QFont()
            font.setBold(True)
            return font
        if role == QtCore.Qt.ItemDataRole.CheckStateRole:
            return self._check_state(node, column)
        if role in (
            QtCore.Qt.ItemDataRole.DisplayRole,
            QtCore.Qt.ItemDataRole.EditRole,
        ):
            return self._display(node, column)
        if role == QtCore.Qt.ItemDataRole.DecorationRole and column == 2:
            color = self._color(node)
            if color is not None:
                return QtGui.QColor(*color)
        return None

    def _objects(self, node):
        trace = self.project.traces.get(self.trace_id)
        if trace is None:
            return None, None
        if node.kind == "source":
            _, file_id, column = node.key
            style = trace.styles.get(file_id, {}).get(column)
            return style, None
        if node.kind == "graph":
            _, graph_id = node.key
            try:
                _, graph = self.project.find_graph(
                    graph_id, self.trace_id
                )
            except KeyError:
                return None, None
            return graph, graph
        return None, None

    def _display(self, node, column):
        if column == 0:
            if node.kind == "source":
                _, file_id, source_column = node.key
                label = self.project.files[file_id].labels[source_column]
                return f"{source_column}: {label}"
            return node.label
        style, graph = self._objects(node)
        if style is None:
            return ""
        if column == 1:
            return style.alias
        if column == 2:
            return ""
        if column == 5:
            return f"{style.width:g}"
        if column == 6:
            return STYLE_NAMES[style.line_style - 1]
        if graph is not None and column == 3:
            return ""
        return ""

    def _check_state(self, node, column):
        style, graph = self._objects(node)
        if style is None or column not in (3, 4):
            return None
        checked = QtCore.Qt.CheckState.Checked
        clear = QtCore.Qt.CheckState.Unchecked
        if column == 3:
            if graph is not None:
                trace = self.project.traces[self.trace_id]
                return checked if trace.x_graph_id == graph.uid else clear
            return checked if style.is_x else clear
        if graph is not None:
            return checked if graph.visible else clear
        return checked if style.is_y else clear

    def _color(self, node):
        style, _ = self._objects(node)
        if style is None:
            return None
        values = tuple(style.color)
        return values if len(values) == 4 else values + (255,)

    def _tooltip(self, node, column):
        if node.kind == "file":
            return self.project.files[node.key[1]].path
        if column == 2 and node.kind in ("source", "graph"):
            return (
                "Double-click to choose a color; Ctrl+wheel cycles colors"
            )
        if column == 5 and node.kind in ("source", "graph"):
            return (
                "Double-click to edit; Ctrl+wheel changes width by 0.5"
            )
        if column in (3, 4) and node.kind in ("source", "graph"):
            return "Click the checkbox to change X selection or visibility"
        if column == 6 and node.kind in ("source", "graph"):
            return "Double-click to choose line style and sample markers"
        if node.kind == "graph" and column == 3:
            return "Use this calculated graph's Y array as source X axis"
        return None

    def setData(self, index, value, role=QtCore.Qt.ItemDataRole.EditRole):
        node = self.node(index)
        column = index.column()
        try:
            if node.kind == "source":
                _, file_id, source_column = node.key
                if column == 1:
                    self.project.set_alias(file_id, source_column, str(value))
                elif column == 3:
                    self.project.set_x_column(file_id, source_column)
                elif column == 4:
                    checked = value in (
                        QtCore.Qt.CheckState.Checked,
                        QtCore.Qt.CheckState.Checked.value,
                    )
                    self.project.set_y_column(
                        file_id, source_column, checked
                    )
                elif column == 5:
                    self.project.set_column_style(
                        file_id, source_column, width=float(value)
                    )
                elif column == 6:
                    self.project.set_column_style(
                        file_id,
                        source_column,
                        line_style=self._style_number(value),
                    )
                else:
                    return False
            elif node.kind == "graph":
                _, graph_id = node.key
                if column == 1:
                    self.project.set_graph_style(graph_id, alias=str(value))
                elif column == 3:
                    self.project.set_graph_as_x(graph_id)
                elif column == 4:
                    checked = value in (
                        QtCore.Qt.CheckState.Checked,
                        QtCore.Qt.CheckState.Checked.value,
                    )
                    self.project.set_graph_style(
                        graph_id, visible=checked
                    )
                elif column == 5:
                    self.project.set_graph_style(
                        graph_id, width=float(value)
                    )
                elif column == 6:
                    self.project.set_graph_style(
                        graph_id, line_style=self._style_number(value)
                    )
                else:
                    return False
            else:
                return False
        except (KeyError, TypeError, ValueError):
            return False
        self.dataChanged.emit(index, index)
        return True

    @staticmethod
    def _style_number(value):
        text = str(value)
        if text in STYLE_NAMES:
            return STYLE_NAMES.index(text) + 1
        return int(value)


class FileGraphDelegate(QtWidgets.QStyledItemDelegate):
    """Open lightweight editors and action dialogs on demand."""

    def editorEvent(self, event, model, option, index):
        if event.type() == QtCore.QEvent.Type.Wheel:
            control = QtCore.Qt.KeyboardModifier.ControlModifier
            if event.modifiers() & control and index.column() in (2, 5):
                payload = index.data(QtCore.Qt.ItemDataRole.UserRole)
                if not payload or payload[0] not in ("source", "graph"):
                    return False
                node = model.node(index)
                style, _graph = model._objects(node)
                direction = 1 if event.angleDelta().y() > 0 else -1
                if index.column() == 5:
                    value = max(0.5, style.width + 0.5 * direction)
                    return model.setData(index, value)
                palette = list(model.project.palette)
                current = tuple(style.color)
                normalized = [tuple(color) for color in palette]
                try:
                    position = normalized.index(current)
                except ValueError:
                    position = -1
                color = palette[(position + direction) % len(palette)]
                if payload[0] == "source":
                    model.project.set_column_style(
                        payload[1], payload[2], color=color
                    )
                else:
                    model.project.set_graph_style(payload[1], color=color)
                model.dataChanged.emit(index, index)
                return True
        if event.type() == QtCore.QEvent.Type.MouseButtonDblClick:
            if index.column() in (2, 6):
                payload = index.data(QtCore.Qt.ItemDataRole.UserRole)
                model.action_requested.emit(payload, index.column())
                return True
        return super().editorEvent(event, model, option, index)
