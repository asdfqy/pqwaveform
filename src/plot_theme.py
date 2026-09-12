"""Plot background and text theming without changing marker identities."""

from PyQt6 import QtGui


def foreground_for(background):
    """Return readable axis text for a plot background."""
    return "#101010" if background == "white" else "#d8d8d8"


def set_graphics_text_color(item, color):
    """Color a Qt text item or a pyqtgraph label wrapper reliably."""
    target = getattr(item, "item", item)
    if hasattr(target, "setDefaultTextColor"):
        target.setDefaultTextColor(QtGui.QColor(color))
    if hasattr(item, "setAttr"):
        item.setAttr("color", color)
    item.update()


def apply_plot_appearance(widget, background):
    """Apply one consistent foreground to axes, title, legend, and helpers."""
    foreground = foreground_for(background)
    widget.plot.setBackground(background)
    pen = QtGui.QPen(QtGui.QColor(foreground))
    for axis in (widget.bottom, widget.left):
        axis.setPen(pen)
        axis.setTextPen(pen)
        set_graphics_text_color(axis.label, foreground)
    title = widget.model.traces[widget.tid].title
    widget.plot.setTitle(title, color=foreground)
    set_graphics_text_color(widget.plot.plotItem.titleLabel, foreground)
    legend = widget.plot.plotItem.legend
    if legend is not None:
        trace = widget.model.traces[widget.tid]
        if hasattr(legend, "setLabelTextColor"):
            legend.setLabelTextColor(foreground)
        if hasattr(legend, "setLabelTextSize"):
            legend.setLabelTextSize(f"{trace.legend_font_size}pt")
        for _sample, label in legend.items:
            if hasattr(label, "setText"):
                label.setText(
                    label.text,
                    color=foreground,
                    size=f"{trace.legend_font_size}pt",
                )
            set_graphics_text_color(label, foreground)
        if hasattr(legend, "updateSize"):
            legend.updateSize()
        legend.update()
    widget.tracker.set_text_theme(foreground)
    for marker in widget.intersection_markers:
        marker.set_text_theme(foreground)
    return foreground
