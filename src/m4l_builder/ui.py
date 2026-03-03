"""UI/presentation element creators with presentation mode support.

All UI helpers create objects positioned off-screen in patching view (so they
don't interfere with the DSP wiring) and placed at the specified rect in
presentation view.
"""

from .constants import DEFAULT_TEXT_COLOR


def _presentation_box(id: str, maxclass: str, rect: list, *,
                      numinlets: int = 1, numoutlets: int = 0,
                      patching_rect: list = None, **kwargs) -> dict:
    """Internal helper for creating a presentation-mode box."""
    box = {
        "id": id,
        "maxclass": maxclass,
        "numinlets": numinlets,
        "numoutlets": numoutlets,
        "patching_rect": patching_rect or [700, 0, rect[2], rect[3]],
        "presentation": 1,
        "presentation_rect": rect,
    }
    box.update(kwargs)
    return {"box": box}


def panel(id: str, rect: list, *, bgcolor: list, border: int = 0,
          bordercolor: list = None, rounded: int = 0,
          bgfillcolor: dict = None, shadow: int = 0, shape: int = 0,
          **kwargs) -> dict:
    """Create a panel background element.

    CRITICAL: Always sets background:1 to prevent the panel from rendering
    on top of other objects in presentation view.

    Args:
        id: Unique object ID.
        rect: [x, y, width, height] in presentation view.
        bgcolor: RGBA color list [r, g, b, a].
        border: Border width in pixels.
        bordercolor: RGBA border color.
        rounded: Corner radius.
        bgfillcolor: Gradient fill dict with keys: type, color1, color2, angle, proportion.
        shadow: Positive=raised, negative=recessed.
        shape: 0=rect, 1=circle, 2=triangle, 3=arrow.
    """
    extra = {
        "mode": 0,
        "bgcolor": bgcolor,
        "border": border,
        "rounded": rounded,
        "background": 1,
    }
    if bordercolor:
        extra["bordercolor"] = bordercolor
    if bgfillcolor:
        extra["bgfillcolor"] = bgfillcolor
    if shadow != 0:
        extra["shadow"] = shadow
    if shape != 0:
        extra["shape"] = shape
    extra.update(kwargs)
    return _presentation_box(id, "panel", rect, numinlets=1, numoutlets=0, **extra)


def dial(id: str, varname: str, rect: list, *,
         min_val: float = 0.0, max_val: float = 100.0,
         initial: float = 50.0, shortname: str = None,
         unitstyle: int = 5, patching_rect: list = None,
         appearance: int = 0, activedialcolor: list = None,
         activeneedlecolor: list = None, showname: int = 1,
         shownumber: int = 1, parameter_exponent: float = 1.0,
         triangle: int = 1, focusbordercolor: list = None,
         **kwargs) -> dict:
    """Create a live.dial with parameter storage.

    Args:
        id: Unique object ID.
        varname: Parameter variable name (stored in the Live preset).
        rect: [x, y, width, height] in presentation view.
        min_val: Minimum parameter value.
        max_val: Maximum parameter value.
        initial: Default/initial value.
        shortname: Short display name (defaults to varname).
        unitstyle: Unit display style (see constants.py UNITSTYLE_*).
        patching_rect: Override patching view position.
        appearance: 0=Vertical, 1=Tiny, 2=Panel, 3=Large.
        activedialcolor: RGBA color of the dial arc.
        activeneedlecolor: RGBA needle/indicator color.
        showname: 0=hide name label, 1=show.
        shownumber: 0=hide value, 1=show.
        parameter_exponent: Log scaling for frequency knobs (e.g., 3.0).
        triangle: Show reset-to-default triangle (0=hide).
        focusbordercolor: RGBA highlight color when selected.
    """
    box = {
        "id": id,
        "maxclass": "live.dial",
        "varname": varname,
        "numinlets": 1,
        "numoutlets": 2,
        "outlettype": ["", "float"],
        "parameter_enable": 1,
        "patching_rect": patching_rect or [700, 100, rect[2], rect[3]],
        "presentation": 1,
        "presentation_rect": rect,
        "appearance": appearance,
        "showname": showname,
        "shownumber": shownumber,
        "triangle": triangle,
        "saved_attribute_attributes": {
            "valueof": {
                "parameter_longname": varname,
                "parameter_shortname": shortname or varname,
                "parameter_type": 0,
                "parameter_mmin": min_val,
                "parameter_mmax": max_val,
                "parameter_initial_enable": 1,
                "parameter_initial": [initial],
                "parameter_unitstyle": unitstyle,
                "parameter_exponent": parameter_exponent,
            }
        },
    }
    if activedialcolor:
        box["activedialcolor"] = activedialcolor
    if activeneedlecolor:
        box["activeneedlecolor"] = activeneedlecolor
    if focusbordercolor:
        box["focusbordercolor"] = focusbordercolor
    box.update(kwargs)
    return {"box": box}


def tab(id: str, varname: str, rect: list, *,
        options: list, bgcolor: list = None, bgoncolor: list = None,
        textcolor: list = None, textoncolor: list = None,
        patching_rect: list = None, rounded: float = 0.0,
        spacing_x: float = 0.0, appearance: int = 0,
        **kwargs) -> dict:
    """Create a live.tab selector.

    Args:
        id: Unique object ID.
        varname: Parameter variable name.
        rect: [x, y, width, height] in presentation view.
        options: List of tab label strings.
        bgcolor: Background color for unselected tabs.
        bgoncolor: Background color for selected tab.
        textcolor: Text color for unselected tabs.
        textoncolor: Text color for selected tab.
        patching_rect: Override patching view position.
        rounded: Corner radius for pill-shaped buttons.
        spacing_x: Gaps between tabs.
        appearance: 0=Default, 1=LCD.
    """
    box = {
        "id": id,
        "maxclass": "live.tab",
        "varname": varname,
        "numinlets": 1,
        "numoutlets": 3,
        "outlettype": ["", "", "float"],
        "parameter_enable": 1,
        "num_lines_patching": 1,
        "num_lines_presentation": 1,
        "patching_rect": patching_rect or [700, 200, rect[2], rect[3]],
        "presentation": 1,
        "presentation_rect": rect,
        "saved_attribute_attributes": {
            "valueof": {
                "parameter_longname": varname,
                "parameter_shortname": varname,
                "parameter_type": 2,
                "parameter_enum": " ".join(options),
            }
        },
    }
    if rounded != 0.0:
        box["rounded"] = rounded
    if spacing_x != 0.0:
        box["spacing_x"] = spacing_x
    if appearance != 0:
        box["appearance"] = appearance
    if bgcolor:
        box["bgcolor"] = bgcolor
    if bgoncolor:
        box["bgoncolor"] = bgoncolor
    if textcolor:
        box["textcolor"] = textcolor
    if textoncolor:
        box["textoncolor"] = textoncolor
    box.update(kwargs)
    return {"box": box}


def toggle(id: str, varname: str, rect: list, *, shortname: str = None,
           patching_rect: list = None, activebgcolor: list = None,
           activebgoncolor: list = None, rounded: float = 0.0,
           labels: tuple = ("off", "on"),
           **kwargs) -> dict:
    """Create a live.toggle with parameter storage.

    Args:
        id: Unique object ID.
        varname: Parameter variable name.
        rect: [x, y, width, height] in presentation view.
        shortname: Short display name (defaults to varname).
        patching_rect: Override patching view position.
        activebgcolor: RGBA background when OFF.
        activebgoncolor: RGBA background when ON.
        rounded: Corner radius.
        labels: Tuple of (off_label, on_label) for automation display.
                Examples: ("off", "on"), ("Normal", "Inverted"), ("Stereo", "Mono").
    """
    box = {
        "id": id,
        "maxclass": "live.toggle",
        "varname": varname,
        "numinlets": 1,
        "numoutlets": 1,
        "outlettype": [""],
        "parameter_enable": 1,
        "patching_rect": patching_rect or [700, 300, rect[2], rect[3]],
        "presentation": 1,
        "presentation_rect": rect,
        "saved_attribute_attributes": {
            "valueof": {
                "parameter_longname": varname,
                "parameter_shortname": shortname or varname,
                "parameter_type": 2,
                "parameter_enum": f"{labels[0]} {labels[1]}",
            }
        },
    }
    if activebgcolor:
        box["activebgcolor"] = activebgcolor
    if activebgoncolor:
        box["activebgoncolor"] = activebgoncolor
    if rounded != 0.0:
        box["rounded"] = rounded
    box.update(kwargs)
    return {"box": box}


def comment(id: str, rect: list, text: str, *, textcolor: list = None,
            fontsize: float = 10.0, fontname: str = "Ableton Sans Medium",
            justification: int = 0, patching_rect: list = None,
            **kwargs) -> dict:
    """Create a live.comment label.

    Args:
        id: Unique object ID.
        rect: [x, y, width, height] in presentation view.
        text: Label text.
        textcolor: RGBA text color.
        fontsize: Font size in points.
        fontname: Font family name.
        justification: Text alignment (0=left, 1=center, 2=right).
        patching_rect: Override patching view position.
    """
    box = {
        "id": id,
        "maxclass": "live.comment",
        "numinlets": 1,
        "numoutlets": 0,
        "fontname": fontname,
        "fontsize": fontsize,
        "textcolor": textcolor or list(DEFAULT_TEXT_COLOR),
        "text": text,
        "textjustification": justification,
        "patching_rect": patching_rect or [700, 400, rect[2], rect[3]],
        "presentation": 1,
        "presentation_rect": rect,
    }
    box.update(kwargs)
    return {"box": box}


def meter(id: str, rect: list, *, orientation: int = 0,
          patching_rect: list = None, coldcolor: list = None,
          warmcolor: list = None, hotcolor: list = None,
          overloadcolor: list = None, **kwargs) -> dict:
    """Create a live.meter~ level meter.

    Args:
        id: Unique object ID.
        rect: [x, y, width, height] in presentation view.
        orientation: 0 = vertical, 1 = horizontal.
        patching_rect: Override patching view position.
        coldcolor: RGBA color for low levels.
        warmcolor: RGBA color for medium levels.
        hotcolor: RGBA color for high levels.
        overloadcolor: RGBA color for overload.
    """
    extra = {
        "outlettype": [""],
        "orientation": orientation,
        "patching_rect": patching_rect or [700, 600, rect[2], rect[3]],
    }
    if coldcolor:
        extra["coldcolor"] = coldcolor
    if warmcolor:
        extra["warmcolor"] = warmcolor
    if hotcolor:
        extra["hotcolor"] = hotcolor
    if overloadcolor:
        extra["overloadcolor"] = overloadcolor
    extra.update(kwargs)
    return _presentation_box(
        id, "live.meter~", rect,
        numinlets=1, numoutlets=1,
        **extra,
    )


def menu(id: str, varname: str, rect: list, *, options: list,
         shortname: str = None, patching_rect: list = None,
         **kwargs) -> dict:
    """Create a live.menu dropdown selector.

    Args:
        id: Unique object ID.
        varname: Parameter variable name.
        rect: [x, y, width, height] in presentation view.
        options: List of menu item strings.
        shortname: Short display name (defaults to varname).
        patching_rect: Override patching view position.
    """
    box = {
        "id": id,
        "maxclass": "live.menu",
        "varname": varname,
        "numinlets": 1,
        "numoutlets": 3,
        "outlettype": ["", "", "float"],
        "parameter_enable": 1,
        "patching_rect": patching_rect or [700, 700, rect[2], rect[3]],
        "presentation": 1,
        "presentation_rect": rect,
        "saved_attribute_attributes": {
            "valueof": {
                "parameter_longname": varname,
                "parameter_shortname": shortname or varname,
                "parameter_type": 2,
                "parameter_enum": " ".join(options),
            }
        },
    }
    box.update(kwargs)
    return {"box": box}


def number_box(id: str, varname: str, rect: list, *,
               min_val: float = 0.0, max_val: float = 127.0,
               initial: float = 0.0, shortname: str = None,
               unitstyle: int = 1, patching_rect: list = None,
               **kwargs) -> dict:
    """Create a live.numbox numeric display with parameter storage.

    Args:
        id: Unique object ID.
        varname: Parameter variable name.
        rect: [x, y, width, height] in presentation view.
        min_val: Minimum parameter value.
        max_val: Maximum parameter value.
        initial: Default/initial value.
        shortname: Short display name (defaults to varname).
        unitstyle: Unit display style (see constants.py UNITSTYLE_*).
        patching_rect: Override patching view position.
    """
    box = {
        "id": id,
        "maxclass": "live.numbox",
        "varname": varname,
        "numinlets": 1,
        "numoutlets": 2,
        "outlettype": ["", "float"],
        "parameter_enable": 1,
        "patching_rect": patching_rect or [700, 800, rect[2], rect[3]],
        "presentation": 1,
        "presentation_rect": rect,
        "saved_attribute_attributes": {
            "valueof": {
                "parameter_longname": varname,
                "parameter_shortname": shortname or varname,
                "parameter_type": 0,
                "parameter_mmin": min_val,
                "parameter_mmax": max_val,
                "parameter_initial_enable": 1,
                "parameter_initial": [initial],
                "parameter_unitstyle": unitstyle,
            }
        },
    }
    box.update(kwargs)
    return {"box": box}


def slider(id: str, varname: str, rect: list, *,
           min_val: float = 0.0, max_val: float = 1.0,
           initial: float = 0.5, shortname: str = None,
           unitstyle: int = 1, orientation: int = 0,
           patching_rect: list = None, **kwargs) -> dict:
    """Create a live.slider with parameter storage.

    Args:
        id: Unique object ID.
        varname: Parameter variable name.
        rect: [x, y, width, height] in presentation view.
        min_val: Minimum parameter value.
        max_val: Maximum parameter value.
        initial: Default/initial value.
        shortname: Short display name (defaults to varname).
        unitstyle: Unit display style (see constants.py UNITSTYLE_*).
        orientation: 0 = vertical, 1 = horizontal.
        patching_rect: Override patching view position.
    """
    box = {
        "id": id,
        "maxclass": "live.slider",
        "varname": varname,
        "numinlets": 1,
        "numoutlets": 2,
        "outlettype": ["", "float"],
        "parameter_enable": 1,
        "orientation": orientation,
        "patching_rect": patching_rect or [700, 900, rect[2], rect[3]],
        "presentation": 1,
        "presentation_rect": rect,
        "saved_attribute_attributes": {
            "valueof": {
                "parameter_longname": varname,
                "parameter_shortname": shortname or varname,
                "parameter_type": 0,
                "parameter_mmin": min_val,
                "parameter_mmax": max_val,
                "parameter_initial_enable": 1,
                "parameter_initial": [initial],
                "parameter_unitstyle": unitstyle,
            }
        },
    }
    box.update(kwargs)
    return {"box": box}


def button(id: str, varname: str, rect: list, *, shortname: str = None,
           patching_rect: list = None, **kwargs) -> dict:
    """Create a live.button (momentary trigger).

    Outputs a bang when clicked. Parameter-enabled for automation.

    Args:
        id: Unique object ID.
        varname: Parameter variable name.
        rect: [x, y, width, height] in presentation view.
        shortname: Short display name (defaults to varname).
        patching_rect: Override patching view position.
    """
    box = {
        "id": id,
        "maxclass": "live.button",
        "varname": varname,
        "numinlets": 1,
        "numoutlets": 1,
        "outlettype": [""],
        "parameter_enable": 1,
        "patching_rect": patching_rect or [700, 1000, rect[2], rect[3]],
        "presentation": 1,
        "presentation_rect": rect,
        "saved_attribute_attributes": {
            "valueof": {
                "parameter_longname": varname,
                "parameter_shortname": shortname or varname,
                "parameter_type": 2,
                "parameter_enum": "off on",
            }
        },
    }
    box.update(kwargs)
    return {"box": box}


def scope(id: str, rect: list, *, bgcolor: list = None, linecolor: list = None,
          gridcolor: list = None, range_vals: list = None,
          calccount: int = 64, patching_rect: list = None,
          smooth: int = 0, line_width: float = 1.0,
          mode: str = None, activelinecolor: list = None,
          decay_time: int = 0, **kwargs) -> dict:
    """Create a live.scope~ display.

    Args:
        id: Unique object ID.
        rect: [x, y, width, height] in presentation view.
        bgcolor: Background color.
        linecolor: Waveform line color.
        gridcolor: Grid line color.
        range_vals: [min, max] display range.
        calccount: Number of samples per pixel.
        patching_rect: Override patching view position.
        smooth: 0=off, 1=accurate, 2=pretty.
        line_width: Waveform trace thickness.
        mode: Display mode string.
        activelinecolor: Visible trace color in Live.
        decay_time: Fade-out duration in ms.
    """
    box = {
        "id": id,
        "maxclass": "live.scope~",
        "numinlets": 2,
        "numoutlets": 0,
        "calccount": calccount,
        "patching_rect": patching_rect or [700, 500, rect[2], rect[3]],
        "presentation": 1,
        "presentation_rect": rect,
    }
    if bgcolor:
        box["bgcolor"] = bgcolor
    if linecolor:
        box["linecolor"] = linecolor
    if gridcolor:
        box["gridcolor"] = gridcolor
    if range_vals:
        box["range"] = range_vals
    if smooth != 0:
        box["smooth"] = smooth
    if line_width != 1.0:
        box["line_width"] = line_width
    if mode is not None:
        box["mode"] = mode
    if activelinecolor:
        box["activelinecolor"] = activelinecolor
    if decay_time != 0:
        box["decay_time"] = decay_time
    box.update(kwargs)
    return {"box": box}


# --- Phase 4: New UI Objects ---


def live_text(id: str, varname: str, rect: list, *, text_on: str = "ON",
              text_off: str = "OFF", bgcolor: list = None,
              bgoncolor: list = None, textcolor: list = None,
              textoncolor: list = None, fontname: str = "Ableton Sans Medium",
              fontsize: float = 10.0, rounded: float = 0.0, mode: int = 0,
              shortname: str = None, patching_rect: list = None,
              **kwargs) -> dict:
    """Create a live.text styled button/toggle.

    Args:
        id: Unique object ID.
        varname: Parameter variable name.
        rect: [x, y, width, height] in presentation view.
        text_on: Text displayed when ON.
        text_off: Text displayed when OFF.
        bgcolor: RGBA background color (off state).
        bgoncolor: RGBA background color (on state).
        textcolor: RGBA text color (off state).
        textoncolor: RGBA text color (on state).
        fontname: Font family name.
        fontsize: Font size in points.
        rounded: Corner radius.
        mode: 0=toggle, 1=button (momentary).
        shortname: Short display name (defaults to varname).
        patching_rect: Override patching view position.
    """
    box = {
        "id": id,
        "maxclass": "live.text",
        "varname": varname,
        "numinlets": 1,
        "numoutlets": 2,
        "outlettype": ["", ""],
        "parameter_enable": 1,
        "text": text_off,
        "texton": text_on,
        "fontname": fontname,
        "fontsize": fontsize,
        "mode": mode,
        "patching_rect": patching_rect or [700, 1100, rect[2], rect[3]],
        "presentation": 1,
        "presentation_rect": rect,
        "saved_attribute_attributes": {
            "valueof": {
                "parameter_longname": varname,
                "parameter_shortname": shortname or varname,
                "parameter_type": 2,
                "parameter_enum": text_off + " " + text_on,
            }
        },
    }
    if bgcolor:
        box["bgcolor"] = bgcolor
    if bgoncolor:
        box["bgoncolor"] = bgoncolor
    if textcolor:
        box["textcolor"] = textcolor
    if textoncolor:
        box["textoncolor"] = textoncolor
    if rounded != 0.0:
        box["rounded"] = rounded
    box.update(kwargs)
    return {"box": box}


def fpic(id: str, rect: list, *, pic: str = "", autofit: int = 1,
         patching_rect: list = None, **kwargs) -> dict:
    """Create an fpic image display.

    Args:
        id: Unique object ID.
        rect: [x, y, width, height] in presentation view.
        pic: Filename of image (must be in Max search path or absolute).
        autofit: 1=scale image to fit rect.
        patching_rect: Override patching view position.
    """
    return _presentation_box(
        id, "fpic", rect,
        numinlets=1, numoutlets=1,
        outlettype=["jit_matrix"],
        pic=pic,
        autofit=autofit,
        patching_rect=patching_rect or [700, 1200, rect[2], rect[3]],
        **kwargs,
    )


def live_gain(id: str, varname: str, rect: list, *, min_val: float = -70.0,
              max_val: float = 6.0, initial: float = 0.0,
              shortname: str = None, orientation: int = 0,
              patching_rect: list = None, **kwargs) -> dict:
    """Create a live.gain~ gain fader with built-in meter.

    Args:
        id: Unique object ID.
        varname: Parameter variable name.
        rect: [x, y, width, height] in presentation view.
        min_val: Minimum gain in dB.
        max_val: Maximum gain in dB.
        initial: Default gain in dB.
        shortname: Short display name (defaults to varname).
        orientation: 0=vertical, 1=horizontal.
        patching_rect: Override patching view position.
    """
    box = {
        "id": id,
        "maxclass": "live.gain~",
        "varname": varname,
        "numinlets": 2,
        "numoutlets": 5,
        "outlettype": ["signal", "signal", "", "float", "list"],
        "parameter_enable": 1,
        "orientation": orientation,
        "patching_rect": patching_rect or [700, 1300, rect[2], rect[3]],
        "presentation": 1,
        "presentation_rect": rect,
        "saved_attribute_attributes": {
            "valueof": {
                "parameter_longname": varname,
                "parameter_shortname": shortname or varname,
                "parameter_type": 0,
                "parameter_mmin": min_val,
                "parameter_mmax": max_val,
                "parameter_initial_enable": 1,
                "parameter_initial": [initial],
                "parameter_unitstyle": 4,
            }
        },
    }
    box.update(kwargs)
    return {"box": box}


def multislider(id: str, rect: list, *, size: int = 16, min_val: float = 0.0,
                max_val: float = 1.0, setminmax: list = None,
                slidercolor: list = None, candicane2: list = None,
                orientation: int = 0, setstyle: int = 0,
                patching_rect: list = None, **kwargs) -> dict:
    """Create a multislider bar/step display.

    Args:
        id: Unique object ID.
        rect: [x, y, width, height] in presentation view.
        size: Number of sliders.
        min_val: Minimum slider value.
        max_val: Maximum slider value.
        setminmax: [min, max] override.
        slidercolor: RGBA bar color.
        candicane2: RGBA alternate bar color.
        orientation: 0=vertical bars, 1=horizontal.
        setstyle: 0=bar, 1=line, 2=point.
        patching_rect: Override patching view position.
    """
    box = {
        "id": id,
        "maxclass": "multislider",
        "numinlets": 2,
        "numoutlets": 2,
        "outlettype": ["", ""],
        "size": size,
        "setminmax": setminmax or [min_val, max_val],
        "orientation": orientation,
        "setstyle": setstyle,
        "patching_rect": patching_rect or [700, 1400, rect[2], rect[3]],
        "presentation": 1,
        "presentation_rect": rect,
    }
    if slidercolor:
        box["slidercolor"] = slidercolor
    if candicane2:
        box["candicane2"] = candicane2
    box.update(kwargs)
    return {"box": box}


def jsui(id: str, rect: list, *, js_filename: str, numinlets: int = 1,
         numoutlets: int = 0, outlettype: list = None,
         patching_rect: list = None, **kwargs) -> dict:
    """Create a jsui JavaScript UI display.

    jsui renders custom vector graphics via Max's mgraphics (Cairo) API.
    The JS file is written alongside the .amxd by device.build().

    Args:
        id: Unique object ID.
        rect: [x, y, width, height] in presentation view.
        js_filename: Name of the JavaScript file to load.
        numinlets: Number of inlets for receiving parameter data.
        numoutlets: Number of outlets for sending data back.
        outlettype: List of outlet type strings.
        patching_rect: Override patching view position.
    """
    box = {
        "id": id,
        "maxclass": "jsui",
        "numinlets": numinlets,
        "numoutlets": numoutlets,
        "outlettype": outlettype or ([""] * numoutlets if numoutlets > 0 else []),
        "filename": js_filename,
        "patching_rect": patching_rect or [700, 1500, rect[2], rect[3]],
        "presentation": 1,
        "presentation_rect": rect,
    }
    box.update(kwargs)
    return {"box": box}
