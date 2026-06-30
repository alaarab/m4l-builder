"""Theme system for coordinated M4L device styling."""

import colorsys
from dataclasses import dataclass
from typing import Optional


def js_color(color) -> str:
    """Format an RGBA color list as a ``"r, g, b, a"`` string for jsui/v8ui kwargs.

    Components are rounded to 4 decimals (the convention every flagship used when
    it defined this helper inline).
    """
    return ", ".join(str(round(c, 4)) for c in color)


def alpha(color, value) -> list:
    """Return a copy of an RGB(A) color with its alpha replaced by ``value``."""
    return [color[0], color[1], color[2], value]


@dataclass
class Theme:
    """Coordinated color theme for M4L devices.

    Provides background layers, text colors, and an accent color that
    automatically derives dial, tab, toggle, meter, and scope styling. Pass to
    Device(theme=...) for automatic application.
    """

    # Background layers (dark to light)
    bg: list[float]        # Device background
    surface: list[float]   # Raised section bg
    section: list[float]   # Grouped area bg

    # Text
    text: list[float]      # Primary text
    text_dim: list[float]  # Secondary/label text

    # Accent (the PRIMARY color that means "active/selected")
    accent: list[float]

    # Second accent — the SELECTION/secondary color (Rupture's pink-on-cyan).
    # Two-accent devices read far more premium than one-accent ones. Defaults to
    # accent (single-accent) when omitted.
    accent2: Optional[list[float]] = None

    # v8ui panel gradient (the ui_kit premium top-lit panel_bg). Derived from
    # surface (top, lit) and bg (bottom) when omitted.
    panel_hi: Optional[list[float]] = None
    panel_lo: Optional[list[float]] = None
    panel_border: Optional[list[float]] = None

    # Font
    fontname: str = "Ableton Sans Medium"
    fontname_bold: str = "Ableton Sans Bold"

    # Dial colors (derived from accent by default)
    dial_color: Optional[list[float]] = None       # activedialcolor
    needle_color: Optional[list[float]] = None     # activeneedlecolor

    # Tab colors
    tab_bg: Optional[list[float]] = None           # bgcolor for unselected
    tab_bg_on: Optional[list[float]] = None        # bgoncolor for selected
    tab_text: Optional[list[float]] = None
    tab_text_on: Optional[list[float]] = None

    # Meter colors
    meter_cold: Optional[list[float]] = None   # Low level color (green-ish)
    meter_warm: Optional[list[float]] = None   # Medium level color (yellow-ish)
    meter_hot: Optional[list[float]] = None    # High level color (orange-ish)
    meter_over: Optional[list[float]] = None   # Overload color (red)

    # Scope colors
    scope_color: Optional[list[float]] = None    # Waveform/trace color
    scope_bgcolor: Optional[list[float]] = None  # Scope background

    # Compiled graph-display colors (spectroscope~ / filtergraph~)
    spectrum_color: Optional[list[float]] = None  # Spectrum fill/line (neutral grey)
    grid_color: Optional[list[float]] = None      # Graph grid lines

    # LCD numbox/readout colors (appearance=4 — the dominant premium numbox look)
    lcd_on: Optional[list[float]] = None    # lcdcolor — the lit digit
    lcd_bg: Optional[list[float]] = None    # lcdbgcolor — the dark readout field
    lcd_off: Optional[list[float]] = None   # inactivelcdcolor — dim/unlit segments

    def __post_init__(self):
        if self.accent2 is None:
            self.accent2 = list(self.accent)
        if self.panel_lo is None:
            self.panel_lo = [self.bg[0], self.bg[1], self.bg[2], 1.0]
        if self.panel_hi is None:
            self.panel_hi = [min(self.surface[0] + 0.03, 1.0),
                             min(self.surface[1] + 0.03, 1.0),
                             min(self.surface[2] + 0.03, 1.0), 1.0]
        if self.panel_border is None:
            self.panel_border = alpha(self.text_dim, 0.5)
        if self.dial_color is None:
            self.dial_color = list(self.accent)
        if self.needle_color is None:
            self.needle_color = list(self.text)
        if self.lcd_bg is None:
            # a dark recessed readout field, slightly darker than the panel bg
            self.lcd_bg = [max(self.bg[0] - 0.03, 0.0),
                           max(self.bg[1] - 0.03, 0.0),
                           max(self.bg[2] - 0.03, 0.0), 1.0]
        if self.lcd_on is None:
            self.lcd_on = list(self.accent)            # lit digits = the accent
        if self.lcd_off is None:
            self.lcd_off = alpha(self.text_dim, 0.35)  # dim unlit segments
        if self.tab_bg is None:
            self.tab_bg = list(self.surface)
        if self.tab_bg_on is None:
            # Two-accent premium: the SELECTED tab uses accent2 (the selection
            # color, Rupture's pink-on-cyan), the primary accent stays for dials/
            # bars. Single-accent themes set accent2 == accent above, so they are
            # visually unchanged; only a distinct-accent2 theme gets the second hue.
            self.tab_bg_on = list(self.accent2)
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
        if self.spectrum_color is None:
            # Spectra read best NEUTRAL grey (not the accent) — the EQ8/Pro-Q look.
            self.spectrum_color = [0.66, 0.70, 0.74, 0.85]
        if self.grid_color is None:
            self.grid_color = alpha(self.text_dim, 0.45)

    def meter_kwargs(self) -> dict:
        """Return meter color kwargs for this theme."""
        return {
            'coldcolor': self.meter_cold,
            'warmcolor': self.meter_warm,
            'hotcolor': self.meter_hot,
            'overloadcolor': self.meter_over,
        }

    def accent_str(self) -> str:
        """Primary accent as a ``"r, g, b"`` string (custom-control accent kwarg)."""
        return js_color(self.accent[:3])

    def accent2_str(self) -> str:
        """Selection accent as a ``"r, g, b"`` string (two-accent devices)."""
        return js_color((self.accent2 or self.accent)[:3])

    def panel_bg_kwargs(self) -> dict:
        """Kwargs for ``ui_kit.panel_bg_js`` — a premium top-lit panel in this palette."""
        return {
            'lo': js_color(self.panel_lo),
            'hi': js_color(self.panel_hi),
            'border': js_color(self.panel_border),
        }

    def knob_bg_args(self, device_height, inset: float = 4.0) -> dict:
        """Kwargs for ``Device.add_custom_knob`` so a knob's self-painted
        background matches this palette's panel gradient (seamless, no object box)."""
        hi = self.panel_hi or self.surface
        lo = self.panel_lo or self.bg
        return {
            'bg_hi': [hi[0], hi[1], hi[2]],
            'bg_lo': [lo[0], lo[1], lo[2]],
            'device_height': device_height,
            'inset': inset,
        }

    def scope_kwargs(self) -> dict:
        """Attrs for a raw compiled ``scope~`` (waveform / X-Y goniometer).

        scope~ needs an OPAQUE bg to composite its trace, so ``scope_bgcolor`` is
        forced opaque here.
        """
        bg = list(self.scope_bgcolor or self.bg)
        if len(bg) == 4:
            bg[3] = 1.0
        return {'bgcolor': bg, 'fgcolor': list(self.scope_color or self.accent)}

    def spectrum_kwargs(self, *, transparent_bg: bool = False) -> dict:
        """Attrs for a compiled ``spectroscope~`` spectrum/sonogram display.

        Pass ``transparent_bg=True`` when layering it behind a jsui overlay (the
        EQ pattern); otherwise it carries the theme's opaque scope background.
        """
        return {
            'bgcolor': [0.0, 0.0, 0.0, 0.0] if transparent_bg else list(self.scope_bgcolor or self.bg),
            'fgcolor': list(self.spectrum_color or self.accent),
            'logfreq': 1,
            'logamp': 1,
        }

    def filtergraph_kwargs(self) -> dict:
        """Attrs for a compiled ``filtergraph~`` filter-response editor."""
        return {
            'bgcolor': list(self.scope_bgcolor or self.bg),
            'gridcolor': list(self.grid_color or self.text_dim),
        }

    @classmethod
    def from_accent(cls, accent, bg=None, surface=None):
        """Build a dark theme around a given accent color.

        accent: RGBA list [r, g, b, a] with values 0.0-1.0.
        bg/surface: optional overrides; derived from accent if omitted.
        """
        r, g, b = accent[0], accent[1], accent[2]

        if bg is None:
            # Desaturate and darken significantly
            gray = 0.299 * r + 0.587 * g + 0.114 * b
            bg = [
                gray * 0.08 + r * 0.04,
                gray * 0.08 + g * 0.04,
                gray * 0.08 + b * 0.04,
                1.0,
            ]

        if surface is None:
            surface = [
                bg[0] * 0.6 + 0.1 * 0.4,
                bg[1] * 0.6 + 0.1 * 0.4,
                bg[2] * 0.6 + 0.1 * 0.4,
                1.0,
            ]

        section = [
            min(surface[0] + 0.04, 1.0),
            min(surface[1] + 0.04, 1.0),
            min(surface[2] + 0.04, 1.0),
            1.0,
        ]

        return cls(
            bg=list(bg),
            surface=list(surface),
            section=section,
            text=[0.88, 0.88, 0.88, 1.0],
            text_dim=[0.50, 0.50, 0.52, 1.0],
            accent=list(accent),
        )

    @classmethod
    def custom(cls, **overrides):
        """Start from MIDNIGHT defaults and override individual fields.

        Example: Theme.custom(accent=[0.8, 0.3, 0.1, 1.0])
        """
        defaults = dict(
            bg=[0.07, 0.07, 0.08, 1.0],
            surface=[0.10, 0.10, 0.11, 1.0],
            section=[0.14, 0.14, 0.15, 1.0],
            text=[0.88, 0.88, 0.88, 1.0],
            text_dim=[0.50, 0.50, 0.52, 1.0],
            accent=[0.45, 0.75, 0.65, 1.0],
            meter_cold=[0.25, 0.72, 0.55, 1.0],
            meter_warm=[0.70, 0.72, 0.20, 1.0],
            meter_hot=[0.85, 0.48, 0.10, 1.0],
            meter_over=[0.85, 0.20, 0.15, 1.0],
        )
        defaults.update(overrides)
        return cls(**defaults)


# Hue rotations (fraction of the wheel) for the standard accent-pair schemes.
_SCHEME_ROTATION = {
    "complementary": 0.5,        # 180° — max contrast (the premium default)
    "split": 150.0 / 360.0,      # 150° — softer than complementary
    "triadic": 120.0 / 360.0,    # 120°
    "analogous": 30.0 / 360.0,   # 30°  — harmonious, low contrast
}


def derive_palette(accent, *, scheme="complementary", bg=None, surface=None):
    """Derive a premium TWO-accent dark :class:`Theme` from a single accent (B2).

    ``accent2`` is the accent hue-rotated by the ``scheme`` amount (complementary =
    180°, split = 150°, triadic = 120°, analogous = 30°) in HLS space, preserving
    the accent's lightness and saturation so the pair reads balanced. Two-accent
    devices look far more premium than one-accent ones. ``bg`` / ``surface`` pass
    through to :meth:`Theme.from_accent` (derived from the accent if omitted).
    """
    r, g, b = accent[0], accent[1], accent[2]
    a = accent[3] if len(accent) > 3 else 1.0
    h, light, s = colorsys.rgb_to_hls(r, g, b)
    rot = _SCHEME_ROTATION.get(scheme, 0.5)
    r2, g2, b2 = colorsys.hls_to_rgb((h + rot) % 1.0, light, s)
    theme = Theme.from_accent(list(accent), bg=bg, surface=surface)
    theme.accent2 = [r2, g2, b2, a]
    return theme


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

FOREST = Theme(
    bg=[0.06, 0.09, 0.07, 1.0],
    surface=[0.09, 0.13, 0.10, 1.0],
    section=[0.12, 0.17, 0.13, 1.0],
    text=[0.88, 0.92, 0.88, 1.0],
    text_dim=[0.48, 0.55, 0.50, 1.0],
    accent=[0.30, 0.80, 0.40, 1.0],
    meter_cold=[0.25, 0.75, 0.35, 1.0],
    meter_warm=[0.65, 0.75, 0.20, 1.0],
    meter_hot=[0.80, 0.48, 0.10, 1.0],
    meter_over=[0.85, 0.20, 0.15, 1.0],
)

VIOLET = Theme(
    bg=[0.07, 0.06, 0.10, 1.0],
    surface=[0.11, 0.09, 0.15, 1.0],
    section=[0.15, 0.12, 0.20, 1.0],
    text=[0.90, 0.88, 0.95, 1.0],
    text_dim=[0.52, 0.48, 0.58, 1.0],
    accent=[0.60, 0.30, 0.90, 1.0],
    meter_cold=[0.30, 0.65, 0.80, 1.0],
    meter_warm=[0.55, 0.30, 0.85, 1.0],
    meter_hot=[0.80, 0.20, 0.70, 1.0],
    meter_over=[0.85, 0.20, 0.15, 1.0],
)

SOLAR = Theme(
    bg=[0.10, 0.09, 0.05, 1.0],
    surface=[0.14, 0.12, 0.07, 1.0],
    section=[0.18, 0.16, 0.09, 1.0],
    text=[0.95, 0.93, 0.85, 1.0],
    text_dim=[0.55, 0.52, 0.42, 1.0],
    accent=[0.90, 0.75, 0.20, 1.0],
    meter_cold=[0.35, 0.72, 0.30, 1.0],
    meter_warm=[0.88, 0.75, 0.15, 1.0],
    meter_hot=[0.92, 0.45, 0.08, 1.0],
    meter_over=[0.88, 0.18, 0.12, 1.0],
)

LOFI = Theme(
    bg=[0.12, 0.10, 0.09, 1.0],
    surface=[0.16, 0.14, 0.12, 1.0],
    section=[0.20, 0.18, 0.16, 1.0],
    text=[0.90, 0.87, 0.82, 1.0],
    text_dim=[0.50, 0.46, 0.40, 1.0],
    accent=[0.75, 0.60, 0.25, 1.0],
    meter_cold=[0.40, 0.58, 0.35, 1.0],
    meter_warm=[0.72, 0.60, 0.22, 1.0],
    meter_hot=[0.78, 0.42, 0.12, 1.0],
    meter_over=[0.75, 0.22, 0.15, 1.0],
)

SYNTHWAVE = Theme(
    bg=[0.06, 0.04, 0.10, 1.0],
    surface=[0.10, 0.07, 0.16, 1.0],
    section=[0.14, 0.10, 0.22, 1.0],
    text=[0.90, 0.92, 0.98, 1.0],
    text_dim=[0.48, 0.45, 0.60, 1.0],
    accent=[0.00, 0.85, 0.90, 1.0],
    meter_cold=[0.20, 0.70, 0.80, 1.0],
    meter_warm=[0.55, 0.30, 0.85, 1.0],
    meter_hot=[0.85, 0.15, 0.65, 1.0],
    meter_over=[0.90, 0.10, 0.30, 1.0],
)

INDUSTRIAL = Theme(
    bg=[0.08, 0.08, 0.08, 1.0],
    surface=[0.14, 0.14, 0.14, 1.0],
    section=[0.20, 0.20, 0.20, 1.0],
    text=[0.82, 0.82, 0.82, 1.0],
    text_dim=[0.48, 0.48, 0.48, 1.0],
    accent=[0.95, 0.45, 0.05, 1.0],
    meter_cold=[0.30, 0.65, 0.30, 1.0],
    meter_warm=[0.80, 0.70, 0.15, 1.0],
    meter_hot=[0.92, 0.42, 0.08, 1.0],
    meter_over=[0.90, 0.15, 0.10, 1.0],
)

# ── Two-accent palettes (the diversity set — each device picks its OWN) ───────
# Primary + selection accent, distinct bg character. Built for the PRO UI kit so
# no two devices share the copy-pasted 5-constant block. accent = primary draw
# color; accent2 = selection/secondary (Rupture's pink-on-cyan idea).

RUPTURE = Theme(  # deep navy, cyan primary + pink selection (the Rupture bar)
    bg=[0.052, 0.062, 0.082, 1.0],
    surface=[0.085, 0.10, 0.13, 1.0],
    section=[0.11, 0.13, 0.17, 1.0],
    text=[0.80, 0.85, 0.92, 1.0],
    text_dim=[0.42, 0.47, 0.56, 1.0],
    accent=[0.30, 0.80, 0.86, 1.0],
    accent2=[0.92, 0.40, 0.62, 1.0],
    meter_cold=[0.28, 0.72, 0.78, 1.0],
    meter_warm=[0.55, 0.62, 0.80, 1.0],
    meter_hot=[0.85, 0.45, 0.62, 1.0],
    meter_over=[0.90, 0.22, 0.30, 1.0],
)

TAPELEAP = Theme(  # near-pure black, hot orange + crimson (the TapeLeap bar)
    bg=[0.014, 0.014, 0.017, 1.0],
    surface=[0.040, 0.040, 0.046, 1.0],
    section=[0.070, 0.070, 0.078, 1.0],
    text=[0.88, 0.86, 0.82, 1.0],
    text_dim=[0.46, 0.45, 0.42, 1.0],
    accent=[0.96, 0.56, 0.16, 1.0],
    accent2=[0.90, 0.22, 0.26, 1.0],
    meter_cold=[0.55, 0.55, 0.30, 1.0],
    meter_warm=[0.85, 0.62, 0.18, 1.0],
    meter_hot=[0.92, 0.40, 0.12, 1.0],
    meter_over=[0.90, 0.18, 0.16, 1.0],
)

AMBER = Theme(  # warm charcoal, amber primary + teal selection
    bg=[0.060, 0.057, 0.050, 1.0],
    surface=[0.105, 0.097, 0.082, 1.0],
    section=[0.140, 0.130, 0.110, 1.0],
    text=[0.92, 0.88, 0.80, 1.0],
    text_dim=[0.54, 0.50, 0.42, 1.0],
    accent=[0.94, 0.70, 0.26, 1.0],
    accent2=[0.28, 0.78, 0.74, 1.0],
    meter_cold=[0.30, 0.72, 0.62, 1.0],
    meter_warm=[0.82, 0.72, 0.22, 1.0],
    meter_hot=[0.90, 0.48, 0.12, 1.0],
    meter_over=[0.88, 0.20, 0.14, 1.0],
)

NEON = Theme(  # black, lime primary + magenta selection
    bg=[0.030, 0.034, 0.030, 1.0],
    surface=[0.060, 0.068, 0.060, 1.0],
    section=[0.090, 0.100, 0.090, 1.0],
    text=[0.86, 0.92, 0.84, 1.0],
    text_dim=[0.46, 0.52, 0.46, 1.0],
    accent=[0.66, 0.94, 0.26, 1.0],
    accent2=[0.94, 0.26, 0.74, 1.0],
    meter_cold=[0.50, 0.85, 0.30, 1.0],
    meter_warm=[0.78, 0.82, 0.20, 1.0],
    meter_hot=[0.90, 0.45, 0.55, 1.0],
    meter_over=[0.92, 0.18, 0.40, 1.0],
)

# Two-accent set on an existing palette (cyan + magenta).
SYNTHWAVE.accent2 = [0.92, 0.18, 0.62, 1.0]

STRANULAR = Theme(  # violet + cyan (+ amber meters) — colors lifted from stranular
    bg=[0.055, 0.050, 0.072, 1.0],
    surface=[0.092, 0.084, 0.118, 1.0],
    section=[0.125, 0.114, 0.158, 1.0],
    text=[0.96, 0.98, 0.89, 1.0],        # stranular's near-white text
    text_dim=[0.52, 0.50, 0.58, 1.0],
    accent=[0.70, 0.42, 0.89, 1.0],      # stranular violet (its primary, 9 uses)
    accent2=[0.43, 0.83, 1.0, 1.0],      # stranular cyan (its secondary, 7 uses)
    meter_cold=[0.43, 0.83, 1.0, 1.0],   # cyan
    meter_warm=[0.96, 0.83, 0.16, 1.0],  # stranular yellow
    meter_hot=[1.0, 0.71, 0.20, 1.0],    # stranular amber (its 3rd accent)
    meter_over=[0.90, 0.22, 0.26, 1.0],
)

# Registry of the distinct two-accent palettes for iteration / pick-by-name.
PALETTES = {
    'rupture': RUPTURE,
    'tapeleap': TAPELEAP,
    'amber': AMBER,
    'neon': NEON,
    'synthwave': SYNTHWAVE,
    'violet': VIOLET,
    'industrial': INDUSTRIAL,
    'stranular': STRANULAR,
}
