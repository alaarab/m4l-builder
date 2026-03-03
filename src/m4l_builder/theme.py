"""Theme system for coordinated M4L device styling."""

from dataclasses import dataclass, field
from typing import List


@dataclass
class Theme:
    """Coordinated color theme for M4L devices.

    Provides background layers, text colors, and an accent color that
    automatically derives dial, tab, toggle, meter, and scope styling. Pass to
    Device(theme=...) for automatic application.
    """

    # Background layers (dark to light)
    bg: List[float]        # Device background
    surface: List[float]   # Raised section bg
    section: List[float]   # Grouped area bg

    # Text
    text: List[float]      # Primary text
    text_dim: List[float]  # Secondary/label text

    # Accent (ONE color that means "active/selected")
    accent: List[float]

    # Font
    fontname: str = "Ableton Sans Medium"
    fontname_bold: str = "Ableton Sans Bold"

    # Dial colors (derived from accent by default)
    dial_color: List[float] = None       # activedialcolor
    needle_color: List[float] = None     # activeneedlecolor

    # Tab colors
    tab_bg: List[float] = None           # bgcolor for unselected
    tab_bg_on: List[float] = None        # bgoncolor for selected
    tab_text: List[float] = None
    tab_text_on: List[float] = None

    # Meter colors
    meter_cold: List[float] = None   # Low level color (green-ish)
    meter_warm: List[float] = None   # Medium level color (yellow-ish)
    meter_hot: List[float] = None    # High level color (orange-ish)
    meter_over: List[float] = None   # Overload color (red)

    # Scope colors
    scope_color: List[float] = None    # Waveform/trace color
    scope_bgcolor: List[float] = None  # Scope background

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
        if self.meter_cold is None:
            self.meter_cold = [0.30, 0.70, 0.40, 1.0]
        if self.meter_warm is None:
            self.meter_warm = [0.75, 0.70, 0.20, 1.0]
        if self.meter_hot is None:
            self.meter_hot = [0.85, 0.45, 0.10, 1.0]
        if self.meter_over is None:
            self.meter_over = [0.85, 0.20, 0.15, 1.0]
        if self.scope_color is None:
            self.scope_color = list(self.accent)
        if self.scope_bgcolor is None:
            self.scope_bgcolor = list(self.bg)

    def meter_kwargs(self) -> dict:
        """Return meter color kwargs for this theme."""
        return {
            'coldcolor': self.meter_cold,
            'warmcolor': self.meter_warm,
            'hotcolor': self.meter_hot,
            'overloadcolor': self.meter_over,
        }


MIDNIGHT = Theme(
    bg=[0.07, 0.07, 0.08, 1.0],
    surface=[0.10, 0.10, 0.11, 1.0],
    section=[0.14, 0.14, 0.15, 1.0],
    text=[0.88, 0.88, 0.88, 1.0],
    text_dim=[0.50, 0.50, 0.52, 1.0],
    accent=[0.45, 0.75, 0.65, 1.0],
    # Teal-tinted greens for cold, golden yellows, orange, red
    meter_cold=[0.25, 0.72, 0.55, 1.0],
    meter_warm=[0.70, 0.72, 0.20, 1.0],
    meter_hot=[0.85, 0.48, 0.10, 1.0],
    meter_over=[0.85, 0.20, 0.15, 1.0],
)

WARM = Theme(
    bg=[0.09, 0.08, 0.07, 1.0],
    surface=[0.13, 0.11, 0.10, 1.0],
    section=[0.17, 0.15, 0.13, 1.0],
    text=[0.95, 0.92, 0.85, 1.0],
    text_dim=[0.55, 0.50, 0.45, 1.0],
    accent=[0.85, 0.55, 0.25, 1.0],
    # Warm greens for cold, golden yellows, orange, red
    meter_cold=[0.35, 0.68, 0.30, 1.0],
    meter_warm=[0.80, 0.72, 0.15, 1.0],
    meter_hot=[0.88, 0.50, 0.08, 1.0],
    meter_over=[0.85, 0.20, 0.15, 1.0],
)

COOL = Theme(
    bg=[0.06, 0.07, 0.09, 1.0],
    surface=[0.09, 0.10, 0.13, 1.0],
    section=[0.12, 0.14, 0.17, 1.0],
    text=[0.85, 0.88, 0.92, 1.0],
    text_dim=[0.45, 0.50, 0.55, 1.0],
    accent=[0.35, 0.60, 0.90, 1.0],
    # Blue-tinted greens for cold, blue for warm, violet for hot, red overload
    meter_cold=[0.25, 0.65, 0.75, 1.0],
    meter_warm=[0.30, 0.45, 0.85, 1.0],
    meter_hot=[0.55, 0.25, 0.80, 1.0],
    meter_over=[0.85, 0.20, 0.15, 1.0],
)

LIGHT = Theme(
    bg=[0.92, 0.92, 0.93, 1.0],
    surface=[0.86, 0.86, 0.87, 1.0],
    section=[0.80, 0.80, 0.82, 1.0],
    text=[0.12, 0.12, 0.14, 1.0],
    text_dim=[0.40, 0.40, 0.42, 1.0],
    accent=[0.20, 0.50, 0.85, 1.0],
    # Standard green/yellow/orange/red, slightly muted for light backgrounds
    meter_cold=[0.28, 0.62, 0.32, 1.0],
    meter_warm=[0.68, 0.62, 0.18, 1.0],
    meter_hot=[0.78, 0.40, 0.10, 1.0],
    meter_over=[0.80, 0.18, 0.12, 1.0],
)
