"""Shared engineering-notation formatting."""

import math

import pyqtgraph as pg

SI_PREFIXES = {
    -24: "y", -21: "z", -18: "a", -15: "f", -12: "p", -9: "n",
    -6: "u", -3: "m", 0: "", 3: "k", 6: "M", 9: "G", 12: "T",
    15: "P", 18: "E", 21: "Z", 24: "Y",
}


def engineering_text(value, digits=7):
    """Return a compact value using pyqtgraph's SI formatter."""
    value = float(value)
    if not math.isfinite(value):
        return "inf" if value > 0 else "-inf"
    if value == 0:
        return "0"
    try:
        text = pg.siFormat(
            value, precision=digits, suffix="", space=False
        )
        number = text.rstrip("yzafpnumkMGTPEZY")
        prefix = text[len(number):]
        if "." in number:
            number = number.rstrip("0").rstrip(".")
        return number + prefix
    except (AttributeError, TypeError, ValueError):
        exponent = int(math.floor(math.log10(abs(value)) / 3) * 3)
        exponent = max(-24, min(24, exponent))
        scaled = value / (10.0 ** exponent)
        return f"{scaled:.{digits}g}{SI_PREFIXES[exponent]}"

def display_text(value, engineering=False, digits=7):
    """Format a value either ordinarily or in engineering notation."""
    if engineering:
        return engineering_text(value, digits)
    value = float(value)
    if not math.isfinite(value):
        return "inf" if value > 0 else "-inf"
    return f"{value:.{digits}g}"
