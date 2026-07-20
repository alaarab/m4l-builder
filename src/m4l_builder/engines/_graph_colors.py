"""Shared graph color defaults for EQ and spectrum-style jsui engines."""

DEFAULT_GRAPH_PANEL_COLOR = "0.24, 0.24, 0.25, 1.0"
DEFAULT_GRAPH_PLOT_COLOR = "0.07, 0.10, 0.15, 1.0"
DEFAULT_GRAPH_PLOT_BORDER_COLOR = "0.17, 0.22, 0.30, 1.0"

# Canonical per-band node palette, single-sourced for BOTH EQ engines
# (eq_curve + linear_phase_eq_display) so the same band index always shows
# the same color across the flagship EQs. (They had drifted at band 5.)
BAND_PALETTE = [
    [0.92, 0.36, 0.34, 1.0],
    [0.94, 0.62, 0.24, 1.0],
    [0.88, 0.84, 0.28, 1.0],
    [0.36, 0.80, 0.46, 1.0],
    [0.32, 0.76, 0.86, 1.0],
    [0.38, 0.56, 0.92, 1.0],
    [0.66, 0.46, 0.88, 1.0],
    [0.90, 0.42, 0.66, 1.0],
]


def band_palette_js():
    """Format BAND_PALETTE as a JS array literal for the `var BAND_COLORS`
    declaration in the EQ display engines (matches the prior hand-written
    layout so the generated JS is stable)."""
    rows = ",\n    ".join(
        "[" + ", ".join(str(c) for c in col) + "]" for col in BAND_PALETTE
    )
    return "[\n    " + rows + "\n]"


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
