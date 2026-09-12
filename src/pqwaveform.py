"""Qt6 application entry point."""

import argparse, sys
from PyQt6 import QtWidgets
from main_window import MainWindow


def parse_arguments():
    """Parse original-compatible options."""
    p = argparse.ArgumentParser()
    p.add_argument("data", nargs="*")
    p.add_argument("-x", "--xcolumn", type=int, default=0)
    p.add_argument("-y", "--ycolumn", nargs="+", type=int, default=[1])
    p.add_argument("-xl", "--xaxis", default="lin")
    p.add_argument("-yl", "--yaxis", default="lin")
    p.add_argument("-lw", "--linewidth", type=int, default=0)
    p.add_argument("-ls", "--linestyle", type=int, default=0)
    p.add_argument("-lc", "--linecolor", type=int, default=-1)
    p.add_argument("-ds", "--dseparator", default=r"\s+")
    p.add_argument("-dsb", "--dskipbegin", type=int, default=0)
    p.add_argument("-dse", "--dskipend", type=int, default=0)
    p.add_argument("-dh", "--dheader", type=int, default=-1)
    p.add_argument("-dc", "--dcomment", default="#")
    p.add_argument(
        "-p",
        "--python",
        action="append",
        default=[],
        help="Python file loaded into the embedded IPython namespace",
    )
    return p.parse_args()


def main():
    """Create and run the application."""
    options = parse_arguments()
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow(options)
    for script in options.python:
        try:
            window.load_python_file(script)
        except Exception as error:
            print(error, file=sys.stderr)
    for name in options.data:
        try:
            window.model.load_file(name)
        except Exception as error:
            print(error, file=sys.stderr)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
