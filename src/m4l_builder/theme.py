"""Theme system for coordinated M4L device styling."""

from dataclasses import dataclass


@dataclass
class Theme:
    """Coordinated color theme for M4L devices.

    Provides background layers, text colors, and an accent color that
    automatically derives dial, tab, and toggle styling. Pass to
    Device(theme=...) for automatic application.
    """

    # Background layers (dark to light)
    bg: list           # Device background
    surface: list      # Raised section bg
    section: list      # Grouped area bg

    # Text
    text: list         # Primary text
    text_dim: list     # Secondary/label text

    # Accent (ONE color that means "active/selected")
    accent: list

    # Font
    fontname: str = "Ableton Sans Medium"
    fontname_bold: str = "Ableton Sans Bold"

    # Dial colors (derived from accent by default)
    dial_color: list = None       # activedialcolor
    needle_color: list = None     # activeneedlecolor

    # Tab colors
    tab_bg: list = None           # bgcolor for unselected
    tab_bg_on: list = None        # bgoncolor for selected
    tab_text: list = None
    tab_text_on: list = None

    def __post_init__(self):
        if self.dial_color is None:
            self.dial_color = list(self.accent)
        if self.needle_color is None:
            self.needle_color = list(self.text)
        if self.tab_bg is None:
            self.tab_bg = list(self.surface)
        if self.tab_bg_on is None:
            self.tab_bg_on = list(self.accent)
        if self.tab_text is None:
            self.tab_text = list(self.text_dim)
        if self.tab_text_on is None:
            self.tab_text_on = list(self.text)


MIDNIGHT = Theme(
    bg=[0.07, 0.07, 0.08, 1.0],
    surface=[0.10, 0.10, 0.11, 1.0],
    section=[0.14, 0.14, 0.15, 1.0],
    text=[0.88, 0.88, 0.88, 1.0],
    text_dim=[0.50, 0.50, 0.52, 1.0],
    accent=[0.45, 0.75, 0.65, 1.0],
)

WARM = Theme(
    bg=[0.09, 0.08, 0.07, 1.0],
    surface=[0.13, 0.11, 0.10, 1.0],
    section=[0.17, 0.15, 0.13, 1.0],
    text=[0.95, 0.92, 0.85, 1.0],
    text_dim=[0.55, 0.50, 0.45, 1.0],
    accent=[0.85, 0.55, 0.25, 1.0],
)

COOL = Theme(
    bg=[0.06, 0.07, 0.09, 1.0],
    surface=[0.09, 0.10, 0.13, 1.0],
    section=[0.12, 0.14, 0.17, 1.0],
    text=[0.85, 0.88, 0.92, 1.0],
    text_dim=[0.45, 0.50, 0.55, 1.0],
    accent=[0.35, 0.60, 0.90, 1.0],
)

LIGHT = Theme(
    bg=[0.92, 0.92, 0.93, 1.0],
    surface=[0.86, 0.86, 0.87, 1.0],
    section=[0.80, 0.80, 0.82, 1.0],
    text=[0.12, 0.12, 0.14, 1.0],
    text_dim=[0.40, 0.40, 0.42, 1.0],
    accent=[0.20, 0.50, 0.85, 1.0],
)
