"""Load user Python files into the embedded IPython namespace."""

from pathlib import Path


class UserScriptLoader:
    """Execute user files in the live IPython user namespace."""

    def __init__(self, console):
        self.console = console
        self.loaded_files = []
        self.audit_log = []

    def load(self, filename):
        """Execute a UTF-8 Python file and retain its path for reloading."""
        path = str(Path(filename).expanduser().resolve())
        shell = self.console.kernel_manager.kernel.shell
        source = Path(path).read_text(encoding="utf-8")
        code = compile(source, path, "exec")
        exec(code, shell.user_ns, shell.user_ns)
        if path not in self.loaded_files:
            self.loaded_files.append(path)
        command = f'load_python_file({path!r})'
        if not self.audit_log or self.audit_log[-1] != command:
            self.audit_log.append(command)
        return path

    def reload_all(self):
        """Re-execute every previously loaded user file."""
        for path in tuple(self.loaded_files):
            self.load(path)
