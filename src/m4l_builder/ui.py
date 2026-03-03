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

    Always sets background:1 so the panel renders behind other objects in presentation view.
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

    appearance: 0=Vertical, 1=Tiny, 2=Panel, 3=Large.
    parameter_exponent: log scaling — use 3.0 for frequency knobs.
    unitstyle: see constants.py UNITSTYLE_* values.
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
    """Create a live.tab selector."""
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

    labels: (off_label, on_label) for automation display, e.g. ("Normal", "Inverted").
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
    """Create a live.comment label."""
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
    """Create a live.meter~ level meter."""
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
    """Create a live.menu dropdown selector."""
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
    """Create a live.numbox numeric display with parameter storage."""
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
    """Create a live.slider with parameter storage."""
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
    """Create a live.button (momentary trigger, parameter-enabled for automation)."""
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

    smooth: 0=off, 1=accurate, 2=pretty.
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

    mode: 0=toggle, 1=button (momentary).
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
    """Create an fpic image display."""
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
    """Create a live.gain~ fader with built-in meter."""
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

    setstyle: 0=bar, 1=line, 2=point.
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
    """Create a jsui display for custom vector graphics via Max's mgraphics (Cairo) API."""
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


def adsrui(id: str, rect: list, *, bgcolor: list = None,
           bordercolor: list = None, focusbordercolor: list = None,
           patching_rect: list = None, **kwargs) -> dict:
    """Create a live.adsrui ADSR envelope editor.

    Has 4 outlets for attack, decay, sustain, and release values.
    Users drag handles to shape the envelope.
    """
    box = {
        "id": id,
        "maxclass": "live.adsrui",
        "numinlets": 1,
        "numoutlets": 4,
        "outlettype": ["float", "float", "float", "float"],
        "patching_rect": patching_rect or [700, 1600, rect[2], rect[3]],
        "presentation": 1,
        "presentation_rect": rect,
    }
    if bgcolor:
        box["bgcolor"] = bgcolor
    if bordercolor:
        box["bordercolor"] = bordercolor
    if focusbordercolor:
        box["focusbordercolor"] = focusbordercolor
    box.update(kwargs)
    return {"box": box}


def live_drop(id: str, rect: list, *, textcolor: list = None,
              bgcolor: list = None, bordercolor: list = None,
              patching_rect: list = None, **kwargs) -> dict:
    """Create a live.drop drag-and-drop file target.

    Users drop audio files onto it; outputs the file path.
    """
    box = {
        "id": id,
        "maxclass": "live.drop",
        "numinlets": 1,
        "numoutlets": 1,
        "outlettype": [""],
        "patching_rect": patching_rect or [700, 1700, rect[2], rect[3]],
        "presentation": 1,
        "presentation_rect": rect,
    }
    if textcolor:
        box["textcolor"] = textcolor
    if bgcolor:
        box["bgcolor"] = bgcolor
    if bordercolor:
        box["bordercolor"] = bordercolor
    box.update(kwargs)
    return {"box": box}


def bpatcher(id: str, rect: list, patcher_name: str, *, args: str = None,
             embed: int = 1, patching_rect: list = None, **kwargs) -> dict:
    """Create a bpatcher embeddable sub-patcher.

    embed: 1 stores the sub-patch inside the device file.
    """
    box = {
        "id": id,
        "maxclass": "bpatcher",
        "numinlets": 0,
        "numoutlets": 0,
        "name": patcher_name,
        "embed": embed,
        "patching_rect": patching_rect or [700, 1800, rect[2], rect[3]],
        "presentation": 1,
        "presentation_rect": rect,
    }
    if args is not None:
        box["args"] = args
    box.update(kwargs)
    return {"box": box}


def swatch(id: str, rect: list, *, patching_rect: list = None,
           **kwargs) -> dict:
    """Create a swatch color picker/display.

    Shows a color swatch that can be clicked to open a color chooser.
    """
    box = {
        "id": id,
        "maxclass": "swatch",
        "numinlets": 1,
        "numoutlets": 4,
        "outlettype": ["", "", "", ""],
        "patching_rect": patching_rect or [700, 1900, rect[2], rect[3]],
        "presentation": 1,
        "presentation_rect": rect,
    }
    box.update(kwargs)
    return {"box": box}


def textedit(id: str, rect: list, *, fontname: str = "Ableton Sans Medium",
             fontsize: float = 10.0, textcolor: list = None,
             bgcolor: list = None, patching_rect: list = None,
             **kwargs) -> dict:
    """Create a textedit editable text field for user text input."""
    box = {
        "id": id,
        "maxclass": "textedit",
        "numinlets": 1,
        "numoutlets": 4,
        "outlettype": ["", "", "", "int"],
        "fontname": fontname,
        "fontsize": fontsize,
        "patching_rect": patching_rect or [700, 2000, rect[2], rect[3]],
        "presentation": 1,
        "presentation_rect": rect,
    }
    if textcolor:
        box["textcolor"] = textcolor
    if bgcolor:
        box["bgcolor"] = bgcolor
    box.update(kwargs)
    return {"box": box}


# --- Phase 5: Additional UI Objects ---


def live_step(id: str, rect: list, *, nstep: int = 16, nseq: int = 1,
              loop_start: int = None, loop_end: int = None, mode: int = None,
              patching_rect: list = None, **kwargs) -> dict:
    """Create a live.step step sequencer UI."""
    box = {
        "id": id,
        "maxclass": "live.step",
        "numinlets": 1,
        "numoutlets": 5,
        "outlettype": ["", "", "", "", ""],
        "nstep": nstep,
        "nseq": nseq,
        "patching_rect": patching_rect or [700, 2100, rect[2], rect[3]],
        "presentation": 1,
        "presentation_rect": rect,
    }
    if loop_start is not None:
        box["loop_start"] = loop_start
    if loop_end is not None:
        box["loop_end"] = loop_end
    if mode is not None:
        box["mode"] = mode
    box.update(kwargs)
    return {"box": box}


def live_grid(id: str, rect: list, *, columns: int = 16, rows: int = 8,
              direction: int = None, patching_rect: list = None,
              **kwargs) -> dict:
    """Create a live.grid toggleable cell grid."""
    box = {
        "id": id,
        "maxclass": "live.grid",
        "numinlets": 1,
        "numoutlets": 4,
        "outlettype": ["", "", "", ""],
        "columns": columns,
        "rows": rows,
        "patching_rect": patching_rect or [700, 2200, rect[2], rect[3]],
        "presentation": 1,
        "presentation_rect": rect,
    }
    if direction is not None:
        box["direction"] = direction
    box.update(kwargs)
    return {"box": box}


def live_line(id: str, rect: list, *, linecolor: list = None,
              justification: int = 0, patching_rect: list = None,
              **kwargs) -> dict:
    """Create a live.line visual divider."""
    box = {
        "id": id,
        "maxclass": "live.line",
        "numinlets": 1,
        "numoutlets": 0,
        "outlettype": [],
        "justification": justification,
        "patching_rect": patching_rect or [700, 2300, rect[2], rect[3]],
        "presentation": 1,
        "presentation_rect": rect,
    }
    if linecolor:
        box["linecolor"] = linecolor
    box.update(kwargs)
    return {"box": box}


def live_arrows(id: str, rect: list, *, arrowcolor: list = None,
                arrowbgcolor: list = None, patching_rect: list = None,
                **kwargs) -> dict:
    """Create a live.arrows direction arrow buttons."""
    box = {
        "id": id,
        "maxclass": "live.arrows",
        "numinlets": 1,
        "numoutlets": 1,
        "outlettype": [""],
        "patching_rect": patching_rect or [700, 2400, rect[2], rect[3]],
        "presentation": 1,
        "presentation_rect": rect,
    }
    if arrowcolor:
        box["arrowcolor"] = arrowcolor
    if arrowbgcolor:
        box["arrowbgcolor"] = arrowbgcolor
    box.update(kwargs)
    return {"box": box}


def rslider(id: str, rect: list, *, min_val: int = 0, max_val: int = 127,
            bgcolor: list = None, fgcolor: list = None,
            patching_rect: list = None, **kwargs) -> dict:
    """Create an rslider range slider with two handles."""
    box = {
        "id": id,
        "maxclass": "rslider",
        "numinlets": 2,
        "numoutlets": 2,
        "outlettype": ["", ""],
        "min": min_val,
        "max": max_val,
        "patching_rect": patching_rect or [0, 0, 20, 140],
        "presentation": 1,
        "presentation_rect": rect,
    }
    if bgcolor:
        box["bgcolor"] = bgcolor
    if fgcolor:
        box["fgcolor"] = fgcolor
    box.update(kwargs)
    return {"box": box}


def kslider(id: str, rect: list, *, range: int = 61, offset: int = 36,
            patching_rect: list = None, **kwargs) -> dict:
    """Create a kslider piano keyboard display."""
    box = {
        "id": id,
        "maxclass": "kslider",
        "numinlets": 2,
        "numoutlets": 2,
        "outlettype": ["", ""],
        "range": range,
        "offset": offset,
        "patching_rect": patching_rect or [700, 2500, rect[2], rect[3]],
        "presentation": 1,
        "presentation_rect": rect,
    }
    box.update(kwargs)
    return {"box": box}


def textbutton(id: str, rect: list, text: str = "Button", *,
               texton: str = None, textoff: str = None, mode: int = 0,
               fontsize: float = None, fontname: str = None,
               bgcolor: list = None, bgoncolor: list = None,
               textcolor: list = None, textoncolor: list = None,
               patching_rect: list = None, **kwargs) -> dict:
    """Create a textbutton text button (no parameter storage)."""
    box = {
        "id": id,
        "maxclass": "textbutton",
        "numinlets": 1,
        "numoutlets": 3,
        "outlettype": ["", "", "int"],
        "text": text,
        "mode": mode,
        "patching_rect": patching_rect or [700, 2600, rect[2], rect[3]],
        "presentation": 1,
        "presentation_rect": rect,
    }
    if texton is not None:
        box["texton"] = texton
    if textoff is not None:
        box["textoff"] = textoff
    if fontsize is not None:
        box["fontsize"] = fontsize
    if fontname is not None:
        box["fontname"] = fontname
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


def umenu(id: str, rect: list, *, items: list = None,
          patching_rect: list = None, **kwargs) -> dict:
    """Create a umenu dropdown menu (no parameter storage)."""
    box = {
        "id": id,
        "maxclass": "umenu",
        "numinlets": 1,
        "numoutlets": 3,
        "outlettype": ["int", "", ""],
        "patching_rect": patching_rect or [700, 2700, rect[2], rect[3]],
        "presentation": 1,
        "presentation_rect": rect,
    }
    if items is not None:
        box["items"] = items
    box.update(kwargs)
    return {"box": box}


def radiogroup(id: str, rect: list, *, itemcount: int = 4,
               value: int = None, patching_rect: list = None,
               **kwargs) -> dict:
    """Create a radiogroup vertical radio buttons."""
    box = {
        "id": id,
        "maxclass": "radiogroup",
        "numinlets": 1,
        "numoutlets": 1,
        "outlettype": [""],
        "itemcount": itemcount,
        "patching_rect": patching_rect or [700, 2800, rect[2], rect[3]],
        "presentation": 1,
        "presentation_rect": rect,
    }
    if value is not None:
        box["value"] = value
    box.update(kwargs)
    return {"box": box}


def nodes(id: str, rect: list, *, numnodes: int = 4, xmin: float = None,
          xmax: float = None, ymin: float = None, ymax: float = None,
          patching_rect: list = None, **kwargs) -> dict:
    """Create a nodes XY node editor with draggable points."""
    box = {
        "id": id,
        "maxclass": "nodes",
        "numinlets": 1,
        "numoutlets": 3,
        "outlettype": ["", "", ""],
        "numnodes": numnodes,
        "patching_rect": patching_rect or [700, 2900, rect[2], rect[3]],
        "presentation": 1,
        "presentation_rect": rect,
    }
    if xmin is not None:
        box["xmin"] = xmin
    if xmax is not None:
        box["xmax"] = xmax
    if ymin is not None:
        box["ymin"] = ymin
    if ymax is not None:
        box["ymax"] = ymax
    box.update(kwargs)
    return {"box": box}


def matrixctrl(id: str, rect: list, *, rows: int = 8, columns: int = 8,
               patching_rect: list = None, **kwargs) -> dict:
    """Create a matrixctrl grid matrix control."""
    box = {
        "id": id,
        "maxclass": "matrixctrl",
        "numinlets": 1,
        "numoutlets": 2,
        "outlettype": ["", ""],
        "rows": rows,
        "columns": columns,
        "patching_rect": patching_rect or [700, 3000, rect[2], rect[3]],
        "presentation": 1,
        "presentation_rect": rect,
    }
    box.update(kwargs)
    return {"box": box}


def ubutton(id: str, rect: list, *, patching_rect: list = None,
            **kwargs) -> dict:
    """Create a ubutton invisible click zone."""
    box = {
        "id": id,
        "maxclass": "ubutton",
        "numinlets": 1,
        "numoutlets": 4,
        "outlettype": ["bang", "", "", "int"],
        "patching_rect": patching_rect or [700, 3100, rect[2], rect[3]],
        "presentation": 1,
        "presentation_rect": rect,
    }
    box.update(kwargs)
    return {"box": box}


def nslider(id: str, rect: list, *, staffs: int = None,
            bgcolor: list = None, patching_rect: list = None,
            **kwargs) -> dict:
    """Create an nslider staff notation display."""
    box = {
        "id": id,
        "maxclass": "nslider",
        "numinlets": 2,
        "numoutlets": 2,
        "outlettype": ["", ""],
        "patching_rect": patching_rect or [700, 3200, rect[2], rect[3]],
        "presentation": 1,
        "presentation_rect": rect,
    }
    if staffs is not None:
        box["staffs"] = staffs
    if bgcolor:
        box["bgcolor"] = bgcolor
    box.update(kwargs)
    return {"box": box}
