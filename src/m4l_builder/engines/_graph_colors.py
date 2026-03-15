"""Shared graph color defaults for EQ and spectrum-style jsui engines."""

DEFAULT_GRAPH_PANEL_COLOR = "0.24, 0.24, 0.25, 1.0"
DEFAULT_GRAPH_PLOT_COLOR = "0.07, 0.10, 0.15, 1.0"
DEFAULT_GRAPH_PLOT_BORDER_COLOR = "0.17, 0.22, 0.30, 1.0"


def _rgba_alpha(color_string, fallback=1.0):
    """Return the alpha component of an RGBA string."""
    try:
        return float(color_string.split(",")[3].strip())
    except (IndexError, TypeError, ValueError):
        return fallback


def resolve_graph_panel_color(bg_color, panel_color):
    """Resolve the outer shell color for a graph widget.

    Transparent graph overlays keep a transparent shell unless an explicit
    panel color is supplied, preserving existing layered devices.
    """
    if panel_color is not None:
        return panel_color
    if _rgba_alpha(bg_color) <= 0.001:
        return bg_color
    return DEFAULT_GRAPH_PANEL_COLOR
