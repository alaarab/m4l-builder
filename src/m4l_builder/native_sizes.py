"""Native control sizes (px) — MEASURED from 81 official Ableton/C74 .amxd devices.

Ground truth (parsed presentation_rect from the unencrypted official devices; the
flagship ones like LFO/Shaper are DRM-encrypted and were not touched). Use these as the
DEFAULT sizes for native ``live.*`` controls so devices read native-grade + dense
(Ableton/Rupture style) instead of oversized. See ``docs/ui_inputs_reference.md``.

    from m4l_builder import native_sizes as ns
    device.add_dial("amt", "Amount", [x, y, *ns.DIAL], ...)
    for r in ns.knob_row(16, 24, 3): device.add_dial(..., r, ...)
"""

# (width, height) of each control's presentation rect — the COMMON value in the data.
DIAL = (44, 47)          # ⚠️ un-grounded guess — prefer DIAL_COMPACT (premium default)
DIAL_HERO = (48, 50)     # slightly bigger feature knob (also seen: 56x56)
DIAL_BIG = (56, 56)
MENU = (48, 15)          # NARROW dropdown — height is ALWAYS 15, never wide
NUMBOX = (39, 15)        # mode of 170 official numboxes (39x15, x75); H always 15
TOGGLE = (12, 13)        # tiny
TEXT = (32, 15)          # textbutton / live.text
TEXT_MINI = (16, 15)
BUTTON = (15, 15)        # live.button trigger (can shrink to ~6)
TAB_H = 16               # live.tab row height (16-18)
TAB_SEG_W = 28           # approx per-segment width → 3 segs ≈ 84
VSLIDER = (18, 110)      # vertical fader (18 x ~101-120)
HSLIDER = (64, 15)       # horizontal level slider

# Layout grid (measured).
KNOB_PITCH = 48          # x-spacing between adjacent knobs in a row (44 + ~4 gap)
ROW_PITCH = 22           # y-spacing between stacked single-row controls (menu/numbox)
ROW_H = 15               # standard single-row control height
LABEL_FONTSIZE = 7.0     # a live.comment label above a control (renders small)
VALUE_FONTSIZE = 9.0
FONTSIZE = 10            # the live.* default fontsize

# Premium tiers — MEASURED across the 15-device commercial corpus (own count of
# presentation_rect sizes; counts in parens). The standard DIAL above (44,47) was a
# guess and is NOT how premium devices size knobs; prefer DIAL_COMPACT going forward.
DIAL_COMPACT = (41, 35)   # THE workhorse — 38 of 82 corpus dials. Premium default.
DIAL_RAIL = (41, 48)      # taller labelled rail dial (7)
DIAL_TINY = (54, 36)      # wide-short tiny dial, appearance=1 (5)
DIAL_LCD = (51, 63)       # tall LCD-stacked dial, appearance=3 (5)
NUMBOX_WIDE = (50, 15)    # wider numeric readout (18)
NUMBOX_MINI = (17, 15)    # tiny inline number (5)
VSLIDER_NATIVE = (22, 113)  # measured vertical fader (12) — wider than VSLIDER=(18,110)
TAB_BAR_H = 20            # full-width mode-bar height (the ~175x20 selector, 14x) — taller than TAB_H=16
TEXT_ICON = (15, 15)      # square glyph/icon live.text (17) — the LED/icon-toggle cell
TEXT_SPLIT = (24, 15)     # short/split label live.text (10)
LED_DOT = (10, 10)        # tiny status dot
ROW_PITCH_TIGHT = 17      # measured tight row spacing (AS-suite dense grids)
LABEL_FONTSIZE_PRIMARY = 9.5  # the premium label size (corpus); LABEL_FONTSIZE 7.0 = _TINY

# Device shell.
DEVICE_H = 168           # the device-view ceiling (taller clips in Live)
FRAME_MARGIN = 6         # keep control cells this far inside the panel border


def knob_row(x0, y, n, *, pitch=KNOB_PITCH, size=DIAL_COMPACT):
    """``n`` knob rects in a row starting at ``x0``, spaced by ``pitch``.

    Defaults to ``DIAL_COMPACT`` (41x35) — THE premium corpus workhorse — to match
    ``knob_row_fit`` and the documented preference. (The old ``DIAL`` (44,47) default
    was an un-grounded guess; ``KNOB_PITCH`` 48 gives a corpus-reasonable ~7px gap on
    a 41-wide knob — AS Console's 41-wide dials sit at pitch ~51.)
    """
    w, h = size
    return [[x0 + i * pitch, y, w, h] for i in range(n)]


def col(x, y0, n, *, pitch=ROW_PITCH, size=MENU):
    """``n`` single-row control rects stacked down from ``y0``."""
    w, h = size
    return [[x, y0 + i * pitch, w, h] for i in range(n)]


def knob_row_fit(x0, y, n, width, *, size=DIAL_COMPACT, margin=FRAME_MARGIN):
    """``n`` knob rects spread evenly to fill ``width`` (margin both ends).

    Width-derived pitch — the premium way to lay a knob aisle into a panel of a
    known width instead of a fixed ``KNOB_PITCH``. Uses ``DIAL_COMPACT`` by default.
    """
    w, h = size
    if n <= 1:
        return [[x0 + margin, y, w, h]]
    avail = width - 2 * margin - w
    pitch = avail / (n - 1)
    return [[round(x0 + margin + i * pitch), y, w, h] for i in range(n)]


DENSE_COL_H = 156    # usable vertical band for a knob column inside a 168px device
KNOB_LABEL_H = 8     # the caption rect above each compact knob


def knob_column(x, y0, n, *, height=DENSE_COL_H, knob_w=40, label_h=KNOB_LABEL_H):
    """``n`` dense knob CELLS stacked vertically to fill ``height`` (Rainbow/Pressure
    look). Returns a list of ``(label_rect, dial_rect)`` tuples — caption rect above,
    knob rect below — evenly spaced.

    ⚠️ **In a 168px device a knob COLUMN fits 4 ONLY without a persistent value.** Each
    cell is ``label(8) + knob(~21) + value(~10) ≈ 40px``; at n=4 that is 160px and the
    ``live.dial`` value text OVERFLOWS the short cell into the label below it (verified on
    Pressure). So set ``shownumber=0`` + ``valuepopup=1`` on each dial (value on hover);
    each cell is then just label + knob and 4 fit cleanly. With an always-on
    ``shownumber`` value a column caps at ~3 (taller cells). Pitch = ``height/n``.
    """
    pitch = height / n
    cells = []
    for i in range(n):
        cy = y0 + round(i * pitch)
        dial_h = max(round(pitch) - label_h - 2, 18)
        cells.append((
            [x, cy, knob_w, label_h],
            [x, cy + label_h + 1, knob_w, dial_h],
        ))
    return cells


def toggle_column(x, y0, n, *, height=DENSE_COL_H, w=48, label_h=KNOB_LABEL_H):
    """``n`` toggle CELLS stacked to fill ``height`` — the labelled-button column that
    sits beside the knob columns in a dense control card (Pressure / Snap). Returns
    ``(label_rect, button_rect)`` tuples. Buttons default to 48 wide (room for text
    like ``ACTIVE``/``BYPASSED``) and 14–18 tall. Pairs with :func:`knob_column` to
    build the flagship dense card: displays on the left, then 2–3 ``knob_column`` knob
    columns + one ``toggle_column`` (mode/auto/look/bypass) inside a SURFACE card."""
    pitch = height / n
    cells = []
    for i in range(n):
        cy = y0 + round(i * pitch)
        btn_h = min(max(round(pitch) - label_h - 2, 14), 18)
        cells.append((
            [x, cy, w, label_h],
            [x, cy + label_h + 1, w, btn_h],
        ))
    return cells
