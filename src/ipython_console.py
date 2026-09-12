"""Embedded Jupyter QtConsole with live project API."""

import numpy as np
import pandas as pd
from qtconsole.inprocess import QtInProcessKernelManager
from qtconsole.rich_jupyter_widget import RichJupyterWidget


class IPythonConsole(RichJupyterWidget):
    """Run an in-process IPython kernel."""

    def __init__(self, model, parent=None):
        """Start kernel and publish API."""
        super().__init__(parent)
        self.model = model
        self.syntax_style = "monokai"
        self.style_sheet = (
            "QPlainTextEdit,QTextEdit{background:#000;color:#eee;}"
        )
        self._aliases = set()
        self.kernel_manager = QtInProcessKernelManager()
        self.kernel_manager.start_kernel(show_banner=False)
        self.kernel_manager.kernel.gui = "qt"
        self.kernel_client = self.kernel_manager.client()
        self.kernel_client.start_channels()
        model.aliases_changed.connect(self.refresh_namespace)
        self.refresh_namespace()

    def refresh_namespace(self):
        """Synchronize aliases and API."""
        shell = self.kernel_manager.kernel.shell
        aliases = self.model.alias_arrays()
        for name in self._aliases - set(aliases):
            shell.user_ns.pop(name, None)
        api = {
            name: getattr(self.model, name)
            for name in (
                "add_trace",
                "add_graph",
                "new_trace",
                "remove_graph",
                "set_graph_style",
                "set_graph_as_x",
                "add_marker_h",
                "add_marker_v",
                "save_graph",
                "save_trace",
                "save_traces",
                "save_all_traces",
                "set_axis",
                "clear_alias",
                "clear_all_aliases",
                "prune_aliases",
                "clear_traces",
                "clear_all_files",
            )
        }
        shell.push(
            {
                "np": np,
                "pd": pd,
                "project": self.model,
                "active_trace": lambda: self.model.traces[
                    self.model.active_trace_id
                ],
                **api,
                **aliases,
            }
        )
        self._aliases = set(aliases)

    def command_history(self):
        """Return interactive input cells from the in-process kernel."""
        manager = self.kernel_manager.kernel.shell.history_manager
        return [
            source
            for _session, _line, source in manager.get_range()
            if source.strip()
        ]

    def shutdown(self):
        """Stop kernel and channels."""
        if self.kernel_client:
            self.kernel_client.stop_channels()
            self.kernel_client = None
        if self.kernel_manager:
            self.kernel_manager.shutdown_kernel()
            self.kernel_manager = None
