"""UI/presentation element creators with presentation mode support.

All UI helpers create objects positioned off-screen in patching view (so they
don't interfere with the DSP wiring) and placed at the specified rect in
presentation view.
"""

from typing import Any

from .constants import (
    DEFAULT_TEXT_COLOR,
    UNITSTYLE_DB,
    UNITSTYLE_FLOAT,
    UNITSTYLE_PERCENT,
)
from .parameters import ParameterSpec

_PARAM_UNSET = object()


def _resolve_parameter_spec(
    varname_or_spec,
    *,
    parameter: ParameterSpec = None,
    shortname: str = None,
    parameter_type: int = 0,
    minimum=None,
    maximum=None,
    initial=_PARAM_UNSET,
    initial_enable=None,
    unitstyle=None,
    exponent=None,
    enum=None,
    invisible=None,
    annotation_name=None,
    info=None,
    units=None,
    steps=None,
):
    """Build a ParameterSpec from legacy UI args or a first-class spec."""
    base = parameter or varname_or_spec
    provided_spec = isinstance(base, ParameterSpec)
    if provided_spec:
        spec = base.copy()
    else:
        spec = ParameterSpec(name=str(base))

    updates: dict[str, Any] = {}
    # parameter_type: a first-class spec is authoritative — do NOT clobber an
    # enum/toggle spec's type with the dial/slider default 0 (the legacy arg only
    # applies when building from a bare name), matching every other field below.
    if not provided_spec:
        updates["parameter_type"] = parameter_type
    if shortname is not None and (not provided_spec or spec.shortname is None):
        updates["shortname"] = shortname
    if minimum is not None and (not provided_spec or spec.minimum is None):
        updates["minimum"] = minimum
    if maximum is not None and (not provided_spec or spec.maximum is None):
        updates["maximum"] = maximum
    if initial is not _PARAM_UNSET and (not provided_spec or spec.initial is _PARAM_UNSET):
        updates["initial"] = initial
    if initial_enable is not None and (not provided_spec or spec.initial_enable is None):
        updates["initial_enable"] = initial_enable
    if unitstyle is not None and (not provided_spec or spec.unitstyle is None):
        updates["unitstyle"] = unitstyle
    if exponent is not None and (not provided_spec or spec.exponent is None):
        updates["exponent"] = exponent
    if enum is not None and (not provided_spec or spec.enum is None):
        updates["enum"] = list(enum)
    if invisible is not None and (not provided_spec or spec.invisible is None):
        updates["invisible"] = invisible
    if annotation_name is not None and (not provided_spec or spec.annotation_name is None):
        updates["annotation_name"] = annotation_name
    if info is not None and (not provided_spec or spec.info is None):
        updates["info"] = info
    if units is not None and (not provided_spec or spec.units is None):
        updates["units"] = units
    if steps is not None and (not provided_spec or spec.steps is None):
        updates["steps"] = steps
    return spec.copy(**updates)




def _apply_info_view_annotations(box: dict, spec) -> None:
    """Official-adopt 2 (Ableton Final Checklist): every UI parameter carries
    BOX-level ``annotation_name`` (Live Info View title) + ``annotation``
    (body) so hovering the control in Live shows real help text instead of a
    blank pane. Derives from the richer ``parameter_annotation_name`` when the
    widget provided one, else the param longname; explicit attrs always win
    (setdefault) and raw box dicts (reverse-engineered builds) are untouched.
    """
    title = getattr(spec, "annotation_name", None) or getattr(spec, "name", None)
    if title:
        # alphabetical insertion order — the reverse codegen normalises box
        # keys alphabetically, so this keeps reversed rebuilds byte-identical
        box.setdefault("annotation", str(title))
        box.setdefault("annotation_name", str(title))

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

    Defaults ``background:1`` so the panel renders BEHIND other objects (z-order safe — a
    section/card backdrop; add it before the controls it sits under). Pass ``background=0``
    (via kwargs) to make a FOREGROUND panel that renders in normal box order — added LAST it
    overlays ON TOP of the controls (Max "Send to Back" off). With ``ignoreclick=1`` + a low
    alpha ``bgcolor`` this is the lightweight **bypass-dim / glass overlay** (approach B): a
    transparent film that tints everything below and passes clicks through; drive its
    ``bgcolor`` from ``live.thisdevice`` outlet 1 to darken on bypass. (The ``background=0`` +
    ``ignoreclick=1`` foreground-overlay pattern is PROVEN in the kit — ``tilt``'s
    ``band_display`` v8ui uses exactly it as a working transparent overlay on top of the
    panel below; a panel does the same, filling its ``bgcolor`` instead of painting.)
    """
    extra: dict[str, Any] = {
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
         unitstyle: int = UNITSTYLE_PERCENT, patching_rect: list = None,
         appearance: int = 0, needlemode: int = None,
         activedialcolor: list = None, activefgdialcolor: list = None,
         fgdialcolor: list = None, tricolor: list = None,
         panelcolor: list = None,
         activeneedlecolor: list = None, showname: int = 1,
         shownumber: int = 1, parameter_exponent: float = 1.0,
         triangle: int = 0, focusbordercolor: list = None,
         parameter: ParameterSpec = None, invisible: int = None,
         annotation_name: str = None, info: str = None, units: str = None,
         steps: int = None,
         valuepopup: int = None, valuepopuplabel: int = None,
         **kwargs) -> dict:
    """Create a live.dial with parameter storage.

    appearance: 0=Vertical, 1=Tiny, 2=Panel, 3=Large. This is the knob-SIZE lever and
        the sizes are NEAR-FIXED (Live-measured): 0=small (~21px) stays small even in a
        big rect (extra rect = padding); 3=large (~30px, ≈ EQ Eight's native dial) stays
        large even in a small rect. No medium between them — for an in-between size draw
        a custom v8ui knob. Size the rect only to fit label+knob+value, not to tune ⌀.
    parameter_exponent: log scaling, use 3.0 for frequency knobs.
    unitstyle: see constants.py UNITSTYLE_* values.

    Value display: a ``parameter_enable=0`` dial renders the knob + arc but its
    value text stays BLANK even with ``shownumber=1`` (Live-confirmed) — only a
    REAL parameter shows the value. Accent goes on ``activedialcolor`` — the FILLED value
    arc (min→value unipolar, center→value bipolar), the bright indicator — with a dim
    ``activefgdialcolor`` for the UNFILLED remainder track. This is the kit default and the
    premium bright-fill / dark-track knob (AS Console + EQ Eight use the SAME mapping).
    Verified by the Dial Color Lab A/B at appearance 0 AND 3 (2026-06): there is NO needlemode
    "flip" — ``activedialcolor`` is the filled arc for BOTH polarities. Do NOT accent
    ``activefgdialcolor`` (the remainder): it dims the fill and brightens the empty track.
    Label that MATCHES the value font/size: use this dial's own ``showname=1`` (the
    name renders in the dial's single object-font, identical to the value) with a
    rect tall enough to stack name/knob/value (~50px for appearance=0) — a separate
    ``live.comment`` at the same nominal fontsize renders visibly SMALLER. Trade-off:
    name + value then share one ``textcolor`` (can't grey the label, brighten the value).
    invisible: Max "Parameter Visibility" (PARAM_VIS_* in parameters.py). Pass
        PARAM_VIS_HIDDEN (2) for DSP-probe / diagnostic dials read only via the
        Live API — keeps them out of automation and Live's undo history (a
        metro-fed probe at the default 0 floods undo per Ableton's guidelines).
    """
    spec = _resolve_parameter_spec(
        varname,
        parameter=parameter,
        shortname=shortname,
        parameter_type=0,
        minimum=min_val,
        maximum=max_val,
        initial=initial,
        initial_enable=True,
        unitstyle=unitstyle,
        exponent=parameter_exponent,
        invisible=invisible,
        annotation_name=annotation_name,
        info=info,
        units=units,
        steps=steps,
    )
    box = {
        "id": id,
        "maxclass": "live.dial",
        "varname": spec.name,
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
        "saved_attribute_attributes": spec.to_saved_attributes(),
    }
    # Needle fill ORIGIN (live.dial needlemode, Max 8.6+: 0=Automatic, 1=Unipolar,
    # 2=Bipolar). 'Automatic' fills from CENTER — wrong for a 0..100 dry/wet. Auto-
    # pick: a range straddling zero is bipolar (fill from center), otherwise
    # unipolar (fill from the minimum / 0). Pass `needlemode` to override.
    box["needlemode"] = (
        needlemode if needlemode is not None
        else (2 if (min_val < 0 < max_val) else 1)
    )
    if activedialcolor:
        box["activedialcolor"] = activedialcolor          # FILLED value arc at active=1 (accent)
    if activefgdialcolor:
        box["activefgdialcolor"] = activefgdialcolor      # unfilled REMAINDER track at active=1 (dim)
    if fgdialcolor:
        box["fgdialcolor"] = fgdialcolor                  # unfilled REMAINDER track at active=0
    if activeneedlecolor:
        box["activeneedlecolor"] = activeneedlecolor
    if tricolor:
        box["tricolor"] = tricolor                        # reset-triangle marker (triangle=1)
    if panelcolor:
        box["panelcolor"] = panelcolor                    # only rendered when appearance=2 (Panel)
    if focusbordercolor:
        box["focusbordercolor"] = focusbordercolor
    # valuepopup (default off): 1 = float the value in a popup caption on hover/drag —
    # the premium feedback for a COMPACT dial that has no room for a persistent
    # shownumber. valuepopuplabel sources the caption's label: 0 None / 1 Hint /
    # 2 Scripting Name / 3 Long Name.
    if valuepopup is not None:
        box["valuepopup"] = valuepopup
    if valuepopuplabel is not None:
        box["valuepopuplabel"] = valuepopuplabel
    box.update(kwargs)
    _apply_info_view_annotations(box, spec)
    return {"box": box}


def tab(id: str, varname: str, rect: list, *,
        options: list, bgcolor: list = None, bgoncolor: list = None,
        textcolor: list = None, textoncolor: list = None,
        patching_rect: list = None, rounded: float = 0.0,
        spacing_x: float = 0.0, multiline: int = 0, appearance: int = 0,
        parameter: ParameterSpec = None,
        **kwargs) -> dict:
    """Create a live.tab selector.

    multiline: Max defaults this to 1, which lets live.tab wrap its segments into
    a multi-row / multi-column grid when the rect is short — so a 2-option tab in a
    compact ~64x16 cell stacks VERTICALLY (verified on echotide's FREE/SYNC). A
    premium segmented selector is a single horizontal row ("width grows with
    segments"), so the kit defaults multiline=0. Pass multiline=1 only for a
    deliberate multi-row tab.
    """
    enum_max = max(len(options) - 1, 0)
    spec = _resolve_parameter_spec(
        varname,
        parameter=parameter,
        parameter_type=2,
        minimum=0,
        maximum=enum_max,
        initial=0,
        initial_enable=True,
        enum=options,
    )
    box = {
        "id": id,
        "maxclass": "live.tab",
        "varname": spec.name,
        "numinlets": 1,
        "numoutlets": 3,
        "outlettype": ["", "", "float"],
        "parameter_enable": 1,
        "num_lines_patching": 1,
        "num_lines_presentation": 1,
        "patching_rect": patching_rect or [700, 200, rect[2], rect[3]],
        "presentation": 1,
        "presentation_rect": rect,
        "tabs": len(options),
        "saved_attribute_attributes": spec.to_saved_attributes(),
    }
    if rounded != 0.0:
        box["rounded"] = rounded
    if spacing_x != 0.0:
        box["spacing_x"] = spacing_x
    # Single horizontal segment row by default (premium); see the docstring.
    box["multiline"] = multiline
    if appearance != 0:
        box["appearance"] = appearance
    # live.tab color state matrix (corpus-grounded across 28 corpus tabs): the
    # BACKGROUND attrs have active* twins — bgcolor/activebgcolor and
    # bgoncolor/activebgoncolor — and premium devices set BOTH (17/28 each) so the fill
    # themes whether the device is active or bypassed. The TEXT attrs pair with
    # INACTIVE* twins instead: textoncolor + inactivetextoncolor (20/28) and
    # textcolor + inactivetextoffcolor (9/28) — the bare attr is the enabled colour,
    # the inactive* one holds it when the device is BYPASSED. NB the corpus NEVER sets
    # activetextoncolor (0/28); mirroring textoncolor there (an earlier guess) set a
    # non-corpus attr and left the bypassed selected-tab text un-themed. Mirror each
    # given colour to the twin the corpus uses. Explicit kwargs win last.
    if bgcolor:
        box["bgcolor"] = bgcolor
        box["activebgcolor"] = bgcolor
    if bgoncolor:
        box["bgoncolor"] = bgoncolor
        box["activebgoncolor"] = bgoncolor
    if textcolor:
        box["textcolor"] = textcolor
        box["inactivetextoffcolor"] = textcolor
    if textoncolor:
        box["textoncolor"] = textoncolor
        box["inactivetextoncolor"] = textoncolor
    box.update(kwargs)
    _apply_info_view_annotations(box, spec)
    return {"box": box}


def toggle(id: str, varname: str, rect: list, *, shortname: str = None,
           patching_rect: list = None, activebgcolor: list = None,
           activebgoncolor: list = None, rounded: float = 0.0,
           labels: tuple = ("off", "on"),
           parameter: ParameterSpec = None,
           **kwargs) -> dict:
    """Create a live.toggle with parameter storage.

    labels: (off_label, on_label) for automation display, e.g. ("Normal", "Inverted").
    """
    spec = _resolve_parameter_spec(
        varname,
        parameter=parameter,
        shortname=shortname,
        parameter_type=2,
        enum=labels,
    )
    box = {
        "id": id,
        "maxclass": "live.toggle",
        "varname": spec.name,
        "numinlets": 1,
        "numoutlets": 1,
        "outlettype": [""],
        "parameter_enable": 1,
        "patching_rect": patching_rect or [700, 300, rect[2], rect[3]],
        "presentation": 1,
        "presentation_rect": rect,
        "saved_attribute_attributes": spec.to_saved_attributes(),
    }
    if activebgcolor:
        box["activebgcolor"] = activebgcolor
    if activebgoncolor:
        box["activebgoncolor"] = activebgoncolor
    if rounded != 0.0:
        box["rounded"] = rounded
    box.update(kwargs)
    _apply_info_view_annotations(box, spec)
    return {"box": box}


def comment(id: str, rect: list, text: str, *, textcolor: list = None,
            fontsize: float = 10.0, fontname: str = "Ableton Sans Medium",
            justification: int = 0, linecount: int = None, fontface: int = None,
            patching_rect: list = None, **kwargs) -> dict:
    """Create a live.comment label.

    A live.comment is SINGLE-LINE by default and TRUNCATES text wider than its rect
    (it does not auto-wrap). For a multi-line info/description/credit block set
    ``linecount`` = the number of lines (corpus uses 3 and 5) and give the rect enough
    height. ``fontface``: 0 regular / 1 bold / 2 italic / 3 bold-italic (combines with
    ``fontname``). ``justification`` = ``textjustification`` (0 left / 1 center / 2 right).
    NB a live.comment renders VISIBLY SMALLER than a live.dial's text at the same
    ``fontsize`` — to label a dial so they match, use the dial's ``showname`` instead.
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
    if linecount is not None:
        box["linecount"] = linecount
    if fontface is not None:
        box["fontface"] = fontface
    box.update(kwargs)
    return {"box": box}


def meter(id: str, rect: list, *, orientation: int = 0,
          patching_rect: list = None, coldcolor: list = None,
          warmcolor: list = None, hotcolor: list = None,
          overloadcolor: list = None, **kwargs) -> dict:
    """Create a live.meter~ level meter."""
    extra: dict[str, Any] = {
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
        numinlets=1, numoutlets=2,
        outlettype=["float", "int"],
        **extra,
    )


def menu(id: str, varname: str, rect: list, *, options: list,
         shortname: str = None, patching_rect: list = None,
         bgcolor: list = None, bgoncolor: list = None,
         textcolor: list = None, textoncolor: list = None,
         parameter: ParameterSpec = None,
         **kwargs) -> dict:
    """Create a live.menu dropdown enum selector (automatable Enum param).

    live.menu has its OWN colour model — it does NOT share live.tab's (no synced doc
    exists; 25 corpus menus are the ground truth, e.g. Roulette). The kit maps its
    uniform colour args to live.menu's REAL attrs:
      * ``bgcolor``    -> ``bgcolor`` + ``activebgcolor`` (the menu BODY; active=1 = visible)
      * ``textcolor``  -> bare ``textcolor`` (live.menu shows the BARE attr; NO active twin)
      * ``bgoncolor``  -> ``hltcolor`` (the HIGHLIGHTED item's bg in the open list)
      * ``textoncolor``-> ``hlttextcolor`` (the highlighted item's text)
    live.menu has NO ``bgoncolor``/``textoncolor``/``activetext*`` — the highlight is
    ``hlt*``. Pass ``tricolor`` (dropdown triangle) / ``bordercolor`` via kwargs.
    """
    enum_max = max(len(options) - 1, 0)
    spec = _resolve_parameter_spec(
        varname,
        parameter=parameter,
        shortname=shortname,
        parameter_type=2,
        minimum=0,
        maximum=enum_max,
        initial=0,
        initial_enable=True,
        enum=options,
    )
    box = {
        "id": id,
        "maxclass": "live.menu",
        "varname": spec.name,
        "numinlets": 1,
        "numoutlets": 3,
        "outlettype": ["", "", "float"],
        "parameter_enable": 1,
        "patching_rect": patching_rect or [700, 700, rect[2], rect[3]],
        "presentation": 1,
        "presentation_rect": rect,
        "saved_attribute_attributes": spec.to_saved_attributes(),
    }
    if bgcolor:
        box["bgcolor"] = bgcolor
        box["activebgcolor"] = bgcolor          # the body bg you see when active=1
    if textcolor:
        box["textcolor"] = textcolor            # live.menu shows the BARE attr (no active twin)
    if bgoncolor:
        box["hltcolor"] = bgoncolor             # highlighted-item bg (live.menu has no bgoncolor)
    if textoncolor:
        box["hlttextcolor"] = textoncolor       # highlighted-item text (live.menu has no textoncolor)
    box.update(kwargs)
    _apply_info_view_annotations(box, spec)
    return {"box": box}


def number_box(id: str, varname: str, rect: list, *,
               min_val: float = 0.0, max_val: float = 127.0,
               initial: float = 0.0, shortname: str = None,
               unitstyle: int = UNITSTYLE_FLOAT, patching_rect: list = None,
               allow_wide_int_range: bool = False, appearance: int = 4,
               lcdcolor: list = None, lcdbgcolor: list = None,
               inactivelcdcolor: list = None,
               parameter: ParameterSpec = None,
               **kwargs) -> dict:
    """Create a live.numbox numeric display with parameter storage.

    appearance (doc/corpus-verified): the numbox enum is its OWN — 0=Default,
    1=Triangle, 2=Slider, 3=Bipolar, 4=LCD — NOT the dial's (0=Vertical/1=Tiny/
    2=Panel/3=Large), so don't copy a dial appearance value here. **The kit DEFAULTS
    to ``appearance=4`` (LCD)** — the DOMINANT premium numbox look (98 of 142 corpus
    numboxes) and the one the registry's ``lcdcolor``/``lcdbgcolor``/
    ``inactivelcdcolor`` theme tokens actually RENDER in: a borderless glowing digit
    on an ``lcdbgcolor`` field; ``lcdcolor`` = lit digit, ``inactivelcdcolor`` = the
    dim/unlit segments. (Previously the default was unset → Max's plain mode, so the
    themed LCD colours were DEAD — they only paint at appearance 4.) Pass
    ``appearance=0`` for a plain box, or ``=2`` (Slider) to draw ``activeslidercolor``
    as a value-fill bar behind the digits.
    """
    spec = _resolve_parameter_spec(
        varname,
        parameter=parameter,
        shortname=shortname,
        parameter_type=0,
        minimum=min_val,
        maximum=max_val,
        initial=initial,
        initial_enable=True,
        unitstyle=unitstyle,
    )
    if parameter is not None and isinstance(parameter, ParameterSpec):
        spec = parameter.copy(
            shortname=spec.shortname,
            minimum=spec.minimum,
            maximum=spec.maximum,
            initial=spec.initial,
            initial_enable=spec.initial_enable,
            unitstyle=spec.unitstyle,
        )
    box = {
        "id": id,
        "maxclass": "live.numbox",
        "varname": spec.name,
        "numinlets": 1,
        "numoutlets": 2,
        "outlettype": ["", "float"],
        "parameter_enable": 1,
        "patching_rect": patching_rect or [700, 800, rect[2], rect[3]],
        "presentation": 1,
        "presentation_rect": rect,
        "saved_attribute_attributes": spec.to_saved_attributes(),
    }
    if appearance is not None:
        box["appearance"] = appearance
    if lcdcolor:
        box["lcdcolor"] = lcdcolor
    if lcdbgcolor:
        box["lcdbgcolor"] = lcdbgcolor
    if inactivelcdcolor:
        box["inactivelcdcolor"] = inactivelcdcolor
    if (
        parameter is not None
        and isinstance(parameter, ParameterSpec)
        and parameter.integer_like
        and not (allow_wide_int_range or parameter.allow_wide_range)
        and parameter.minimum is not None
        and parameter.maximum is not None
        and (parameter.minimum < 0 or parameter.maximum > 255)
    ):
        raise ValueError(
            "wide integer-like live.numbox ranges are fragile in Live; "
            "use ParameterSpec.integer(..., allow_wide_range=True) or set allow_wide_int_range=True"
        )
    box.update(kwargs)
    _apply_info_view_annotations(box, spec)
    return {"box": box}


def slider(id: str, varname: str, rect: list, *,
           min_val: float = 0.0, max_val: float = 1.0,
           initial: float = 0.5, shortname: str = None,
           unitstyle: int = UNITSTYLE_FLOAT, orientation: int = 0,
           patching_rect: list = None, parameter: ParameterSpec = None,
           **kwargs) -> dict:
    """Create a live.slider with parameter storage."""
    spec = _resolve_parameter_spec(
        varname,
        parameter=parameter,
        shortname=shortname,
        parameter_type=0,
        minimum=min_val,
        maximum=max_val,
        initial=initial,
        initial_enable=True,
        unitstyle=unitstyle,
    )
    box = {
        "id": id,
        "maxclass": "live.slider",
        "varname": spec.name,
        "numinlets": 1,
        "numoutlets": 2,
        "outlettype": ["", "float"],
        "parameter_enable": 1,
        "orientation": orientation,
        "patching_rect": patching_rect or [700, 900, rect[2], rect[3]],
        "presentation": 1,
        "presentation_rect": rect,
        "saved_attribute_attributes": spec.to_saved_attributes(),
    }
    box.update(kwargs)
    _apply_info_view_annotations(box, spec)
    return {"box": box}


def button(id: str, varname: str, rect: list, *, shortname: str = None,
           bgcolor: list = None, bgoncolor: list = None, bordercolor: list = None,
           patching_rect: list = None, parameter: ParameterSpec = None,
           **kwargs) -> dict:
    """Create a live.button (momentary trigger, parameter-enabled for automation).

    Colors (doc-verified live.button has the active twins): ``bgcolor`` (idle),
    ``bgoncolor`` (the flash on trigger), ``bordercolor``; bg colors are mirrored to
    their ``active*`` twins so the live (active=1) state is themed, not just bypassed.
    """
    spec = _resolve_parameter_spec(
        varname,
        parameter=parameter,
        shortname=shortname,
        parameter_type=2,
        enum=["off", "on"],
    )
    box = {
        "id": id,
        "maxclass": "live.button",
        "varname": spec.name,
        "numinlets": 1,
        "numoutlets": 1,
        "outlettype": [""],
        "parameter_enable": 1,
        "patching_rect": patching_rect or [700, 1000, rect[2], rect[3]],
        "presentation": 1,
        "presentation_rect": rect,
        "saved_attribute_attributes": spec.to_saved_attributes(),
    }
    if bgcolor:
        box["bgcolor"] = bgcolor
        box["activebgcolor"] = bgcolor
    if bgoncolor:
        box["bgoncolor"] = bgoncolor
        box["activebgoncolor"] = bgoncolor
    if bordercolor:
        box["bordercolor"] = bordercolor
    box.update(kwargs)
    _apply_info_view_annotations(box, spec)
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
        "numoutlets": 1,
        "outlettype": ["bang"],
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
              fontsize: float = 10.0, rounded: float = 0.0, mode: int = 1,
              outputmode: int = None, appearance: int = None,
              shortname: str = None,
              patching_rect: list = None, parameter: ParameterSpec = None,
              **kwargs) -> dict:
    """Create a live.text styled button/toggle.

    appearance (doc-verified): 0 = Default (text within box), 1 = Label (a
    square button with the text to the right — the glyph/icon-toggle look), 2 =
    LCD. Corpus uses appearance=2 on live.text 12 sites (LCD readout labels).

    mode: 0 = Button (MOMENTARY — fires on press, un-latches on release,
    rejects Live-API sets), 1 = Toggle (latching). **DEFAULTS to 1 (Toggle)** —
    the live.text MAXREF default is ``mode 1``, the corpus is dominantly toggles
    (113 live.text: 72 default-toggle + 0 explicit mode=1 + 41 explicit Button),
    and EVERY kit/device use is a latching control (bypass / freeze / M-S / on-off).
    The factory previously FORCED ``mode 0`` on every live.text, overriding Max's
    Toggle default, so all 48 fleet toggles shipped MOMENTARY: they un-latched on
    release, rejected Live-API ``set`` (``bad arguments for message set``) and broke
    loadbang defaults (the outlet fires 1 while the param snaps back to 0 — proven
    live in Ableton 12.4). Pass ``mode=0`` explicitly for a genuine momentary button.

    outputmode (toggle mode only, doc-verified): 0 = Mouse down (default),
    1 = Mouse up. Colors (synced-doc state model): a device is active=1, so the
    VISIBLE colours are the ``active*`` variants and the bare attrs only show when
    bypassed. BG + general text have both twins (``bgcolor``/``activebgcolor``,
    ``bgoncolor``/``activebgoncolor``, ``textcolor``/``activetextcolor``) so the
    factory mirrors each. The ON-state text is the EXCEPTION: live.text has only
    ``activetextoncolor`` (no bare ``textoncolor``), so ``textoncolor`` sets just that.
    """
    spec = _resolve_parameter_spec(
        varname,
        parameter=parameter,
        shortname=shortname,
        parameter_type=2,
        # min/max 0..1 are REQUIRED so parameter_mmax is emitted — without it Live
        # cannot map the 2-value enum and shows the placeholder "val1"/"val2" in the
        # automation/MIDI-map display instead of the OFF/ON labels (Live-confirmed on
        # Mono Maker). menu()/tab() already set these; live.text was the gap.
        minimum=0,
        maximum=1,
        enum=[text_off, text_on],
    )
    # Live's automation / MIDI-map DISPLAY labels for live.text come from the
    # BOX-level ``automation`` (off state) / ``automationon`` (on state) attrs —
    # ``parameter_enum`` + ``parameter_mmax`` alone still leave live.text's
    # built-in "val1"/"val2" defaults showing in Live (LOM display_value,
    # automation lanes, MIDI map). Corpus-verified: Rainbow / AS Console /
    # stranular mirror their enum labels into these two attrs on every
    # custom-labelled live.text.
    auto_labels = (list(spec.enum) if getattr(spec, "enum", None)
                   and len(spec.enum) == 2 else [text_off, text_on])
    box = {
        "id": id,
        "maxclass": "live.text",
        "varname": spec.name,
        "numinlets": 1,
        "numoutlets": 2,
        "outlettype": ["", ""],
        "parameter_enable": 1,
        "text": text_off,
        "texton": text_on,
        "automation": str(auto_labels[0]),
        "automationon": str(auto_labels[1]),
        "fontname": fontname,
        "fontsize": fontsize,
        "mode": mode,
        "patching_rect": patching_rect or [700, 1100, rect[2], rect[3]],
        "presentation": 1,
        "presentation_rect": rect,
        "saved_attribute_attributes": spec.to_saved_attributes(),
    }
    # Mirror each bare color to its active* twin (active=1 is the visible state).
    if bgcolor:
        box["bgcolor"] = bgcolor
        box["activebgcolor"] = bgcolor
    if bgoncolor:
        box["bgoncolor"] = bgoncolor
        box["activebgoncolor"] = bgoncolor
    if textcolor:
        box["textcolor"] = textcolor          # off/general text, active=0 (bypassed)
        box["activetextcolor"] = textcolor     # …and active=1 (the visible state)
    if textoncolor:
        # live.text has NO bare `textoncolor` (synced doc): the on-state text colour is
        # `activetextoncolor` (shown when active=1, the visible state), and there is no
        # bypassed on-text twin to mirror. Setting bare `textoncolor` was a no-op guess.
        box["activetextoncolor"] = textoncolor
    if outputmode is not None:
        box["outputmode"] = outputmode
    if appearance is not None:
        box["appearance"] = appearance
    if rounded != 0.0:
        box["rounded"] = rounded
    box.update(kwargs)
    _apply_info_view_annotations(box, spec)
    return {"box": box}


def fpic(id: str, rect: list, *, pic: str = "", autofit: int = 1,
         forceaspect: int = None, embed: int = None, hidden: int = None,
         background: int = None, patching_rect: list = None, **kwargs) -> dict:
    """Create an ``fpic`` picture display (logo / background / SVG state graphic).

    NOT in the synced Max docs — every attr is MEASURED from the corpus (35
    instances; 1 inlet / 1 outlet ``jit_matrix``). ``pic`` is the image file
    (corpus is almost all ``.svg`` — crisp at any size). The high-value attrs the
    prior stub omitted:
    - ``embed`` [int] (corpus 17/35): bundle the image DATA inside the patcher so
      the device is self-contained (no external file to ship). Pair with the kit's
      asset/freeze bundling so the ``pic`` is actually present.
    - ``forceaspect`` [int] (corpus 33/35): preserve the image's aspect ratio
      (with ``autofit`` 1, scales to the box without distorting).
    - ``hidden`` [int] (corpus 23/35): the premium STATE-GRAPHIC pattern — stack N
      fpics (e.g. ``algo1.svg``…``algo8.svg`` + ``*Off.svg``), all ``hidden 1``, and
      let the patch reveal the one matching the current state (AS Console's
      switchable algorithm diagrams). ``background`` 1 puts it on the bg layer.
    fpic has no color attrs (it's an image) — so it is NOT themed. **Use for** a
    logo, a textured/material backdrop, or switchable diagram graphics; for a drawn
    gradient/panel use ``panel`` / a ``v8ui`` painter instead.
    """
    for key, val in (("forceaspect", forceaspect), ("embed", embed),
                     ("hidden", hidden), ("background", background)):
        if val is not None:
            kwargs[key] = val
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
              patching_rect: list = None, parameter: ParameterSpec = None,
              **kwargs) -> dict:
    """Create a live.gain~ fader with built-in meter."""
    spec = _resolve_parameter_spec(
        varname,
        parameter=parameter,
        shortname=shortname,
        parameter_type=0,
        minimum=min_val,
        maximum=max_val,
        initial=initial,
        initial_enable=True,
        unitstyle=UNITSTYLE_DB,
    )
    box = {
        "id": id,
        "maxclass": "live.gain~",
        "varname": spec.name,
        "numinlets": 2,
        "numoutlets": 5,
        "outlettype": ["signal", "signal", "", "float", "list"],
        "parameter_enable": 1,
        "orientation": orientation,
        "patching_rect": patching_rect or [700, 1300, rect[2], rect[3]],
        "presentation": 1,
        "presentation_rect": rect,
        "saved_attribute_attributes": spec.to_saved_attributes(),
    }
    box.update(kwargs)
    _apply_info_view_annotations(box, spec)
    return {"box": box}


def multislider(id: str, rect: list, *, size: int = 16, min_val: float = 0.0,
                max_val: float = 1.0, setminmax: list = None,
                slidercolor: list = None, candicane2: list = None,
                orientation: int = 0, setstyle: int = 0,
                patching_rect: list = None, display: bool = False,
                ghostbar: int = None, ignoreclick: int = None,
                thickness: float = None, signed: int = None,
                bgcolor: list = None, **kwargs) -> dict:
    """Create a ``multislider`` — a strip of N bars (a multi-band meter / GR display
    / step editor).

    ``setstyle`` (default 0): the bar/line/point draw style. ⚠️ The exact enum is
    UNVERIFIED — `multislider` is absent from the synced Max docs, all 5 corpus
    multisliders use the default (0), and the Factory Packs set no explicit `setstyle`;
    a phren finding disputes the old "0=bar/1=line/2=point" labels (claiming 0=thin-line,
    1=bars, …). So keep the default for the standard bar look and Live-VERIFY before
    relying on any non-default style. PREMIUM USAGE (measured: 4/5 corpus
    instances): multislider is used mostly as a NON-interactive multi-bar DISPLAY —
    ``ignoreclick=1`` + ``ghostbar=1`` (a faint full-range outline behind each bar)
    + ``thickness`` + a ``setminmax`` dB range (``[-70,0]`` level, ``[-24,24]``
    gain-reduction), ``signed=1`` for bipolar bars — driven by a list into the right
    inlet. Pass ``display=True`` for that meter preset. The interactive case (1/5)
    is a Blob PARAMETER (``parameter_enable=1`` + ``settype`` stores all bars as one
    saved/automatable list, like ``matrixctrl``). Colors: ``slidercolor`` (the bars)
    + ``bgcolor`` (backdrop) — themed.
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
    if display:
        # the verified multi-bar meter/display preset (overridable below / via kwargs)
        box["ghostbar"] = 1
        box["ignoreclick"] = 1
    for key, val in (("ghostbar", ghostbar), ("ignoreclick", ignoreclick),
                     ("thickness", thickness), ("signed", signed),
                     ("slidercolor", slidercolor), ("candicane2", candicane2),
                     ("bgcolor", bgcolor)):
        if val is not None:
            box[key] = val
    box.update(kwargs)
    return {"box": box}


def jsui(id: str, rect: list, *, js_filename: str, numinlets: int = 1,
         numoutlets: int = 0, outlettype: list = None,
         patching_rect: list = None, **kwargs) -> dict:
    """Create a jsui display for custom vector graphics via Max's mgraphics (Cairo) API.

    A bare ``jsui`` defaults to ``border 1`` — a 1px box OUTLINE Max draws at the
    box edge ON TOP of whatever the JS paints. For a TRANSPARENT overlay (one that
    paints no opaque background) that renders as a stray empty rectangle around the
    control (Live-verified: the Parametric EQ "black box around the knobs"). ``v8ui``
    does not draw this, and ``add_custom_knob`` already uses v8ui to dodge it.
    So we default ``border=0`` here (Chiral ships ``"border":0`` on its jsui); a
    device that wants a visible frame passes ``border=1`` explicitly (kwargs win).
    """
    box = {
        "id": id,
        "maxclass": "jsui",
        "numinlets": numinlets,
        "numoutlets": numoutlets,
        "outlettype": outlettype or ([""] * numoutlets if numoutlets > 0 else []),
        "filename": js_filename,
        "border": 0,
        "patching_rect": patching_rect or [700, 1500, rect[2], rect[3]],
        "presentation": 1,
        "presentation_rect": rect,
    }
    box.update(kwargs)
    return {"box": box}


def v8ui(id: str, rect: list, *, js_filename: str, numinlets: int = 1,
         numoutlets: int = 0, outlettype: list = None,
         patching_rect: list = None, **kwargs) -> dict:
    """Create a v8ui display for modern pointer-aware custom UI rendering.

    Like :func:`jsui`, a bare v8ui draws Max's default black 1px BORDER frame at
    the box edge ON TOP of whatever the JS paints — the "black box around the big
    UI" (Live-verified on the beta: the hero displays + the settings bar). So we
    default ``border=0`` + a transparent ``bordercolor`` here; a device that wants
    a visible frame passes ``border=1`` and a ``bordercolor`` explicitly (kwargs
    win).
    """
    box = {
        "id": id,
        "maxclass": "v8ui",
        "numinlets": numinlets,
        "numoutlets": numoutlets,
        "outlettype": outlettype or ([""] * numoutlets if numoutlets > 0 else []),
        "filename": js_filename,
        "textfile": {
            "filename": js_filename,
            "flags": 0,
            "embed": 0,
            "autowatch": 1,
        },
        "border": 0,
        "bordercolor": [0.0, 0.0, 0.0, 0.0],
        "parameter_enable": 0,
        "patching_rect": patching_rect or [700, 1500, rect[2], rect[3]],
        "presentation": 1,
        "presentation_rect": rect,
    }
    box.update(kwargs)
    return {"box": box}


def adsrui(id: str, rect: list, *, attack_domain: list = None,
           decay_domain: list = None, release_domain: list = None,
           attack_time: float = None, decay_time: float = None,
           release_time: float = None, enable_initial: int = None,
           enable_peak: int = None, enable_final: int = None,
           outputmode: int = None, show_slopehandles: int = None,
           tethering: int = None, activebgcolor: list = None,
           activelinecolor: list = None, activehandlecolor: list = None,
           patching_rect: list = None, **kwargs) -> dict:
    """Create a ``live.adsrui`` ADSR envelope editor.

    MEASURED from the official M4L corpus (2 instances, identical structure). Drag the
    handles to shape an A / D / (S) / R envelope. **10 inlets / 10 outlets, all UNTYPED**
    (``[""]*10``) — the prior stub's 1-in / 4-out 'float' outlets were guessed and WRONG.
    Per-stage TIME AXES (ms): ``attack_domain`` / ``decay_domain`` / ``release_domain``
    [lo, hi] (corpus attack ``[0, 60000]``, decay ``[10, 60000]``, release ``[10, 30000]``);
    the live values are ``attack_time`` / ``decay_time`` / ``release_time`` (ms). Extra
    handles: ``enable_initial`` / ``enable_peak`` / ``enable_final`` (corpus all 0).
    Behaviour: ``outputmode``, ``show_slopehandles`` (curve handles), ``tethering``. Colors
    are the ``active*`` set (the bare twins are the runtime skin): ``activebgcolor`` (display
    bg, corpus alpha-0), ``activelinecolor`` (the envelope line), ``activehandlecolor`` (drag
    handles). Themed ``activebgcolor → scope_bgcolor``, ``activelinecolor → accent``,
    ``activehandlecolor → accent``. **Use for** a built-in ADSR shaper; for an arbitrary
    multi-breakpoint curve use ``function``.
    """
    box = {
        "id": id,
        "maxclass": "live.adsrui",
        "numinlets": 10,
        "numoutlets": 10,
        "outlettype": [""] * 10,
        "patching_rect": patching_rect or [700, 1600, rect[2], rect[3]],
        "presentation": 1,
        "presentation_rect": rect,
    }
    for key, val in (("attack_domain", attack_domain), ("decay_domain", decay_domain),
                     ("release_domain", release_domain), ("attack_time", attack_time),
                     ("decay_time", decay_time), ("release_time", release_time),
                     ("enable_initial", enable_initial), ("enable_peak", enable_peak),
                     ("enable_final", enable_final), ("outputmode", outputmode),
                     ("show_slopehandles", show_slopehandles), ("tethering", tethering),
                     ("activebgcolor", activebgcolor),
                     ("activelinecolor", activelinecolor),
                     ("activehandlecolor", activehandlecolor)):
        if val is not None:
            box[key] = val
    box.update(kwargs)
    return {"box": box}


def live_drop(id: str, rect: list, *, param_name: str = None,
              invisible: int = 1, shortname: str = None,
              decodemode: int = None, color: list = None,
              textcolor: list = None, bordercolor: list = None,
              focusbordercolor: list = None, legend: str = None,
              textjustification: int = None, fontname: str = None,
              fontsize: float = None, ignoreclick: int = None,
              patching_rect: list = None, **kwargs) -> dict:
    """Create a ``live.drop`` file/sample drop target.

    DOC-GROUNDED (live.drop maxref; 0 corpus instances, so the synced doc is the
    sole ground truth — the prior 'ScratchBacker/Mosaique 2-outlet' grounding was
    fabricated and is removed). Drag a file from Live's browser / Finder / Max
    file browser onto it; the absolute pathname is sent out its **single** outlet
    as one quoted symbol (route through ``prepend read`` to feed a ``buffer~`` /
    ``sfplay~``). Doc-verified attributes:
    - ``decodemode`` [int] (default ENABLED): decode non-PCM drops (.mp3/.mp4/
      .mov/.flac…) to extracted audio reported on the outlet; set ``0`` to pass the
      ORIGINAL file path (e.g. a movie for ``jit.movie``, or raw data).
    - ``legend`` [symbol] (default 'Drop Something Here!'): the display-area text.
    - ``color`` = the box OUTLINE color; ``textcolor`` = display text;
      ``bordercolor`` / ``focusbordercolor`` = border (unfocused / focused).
      live.drop has **no bgcolor / fill** attribute. ``textjustification`` aligns
      the text. Supports a ``jspainterfile`` painter (pass via ``**kwargs``).
    Messages: ``set <path>`` stores an initial filepath (persists / reported on
    init), ``clear`` clears it, ``bang`` outputs the current path. **Use when** you
    need a sample / IR / file intake (granular source, convolution loader); for a
    numeric/enum value use the matching ``live.*`` control instead.

    ``param_name`` (widget-hardening spec): registers the drop as a REAL stored
    Live parameter — ``parameter_type=4`` (Blob), no min/max/unit/enum — so the
    dropped path SURVIVES set save/reload and device duplication and is
    re-reported on init. Default ``invisible=1`` (Stored-Only: persisted, no
    automation lane — what a path wants). Caveat: files dragged from encrypted
    Live-pack browsers can hand a decoded TEMP path that may not exist next
    session; files from disk/User Library persist cleanly.
    """
    saved_attrs = None
    if param_name is not None:
        spec = _resolve_parameter_spec(
            param_name, shortname=shortname or "live.drop",
            parameter_type=4, invisible=invisible,
        )
        saved_attrs = {"valueof": spec.to_saved_attributes()["valueof"]}
    box = {
        "id": id,
        "maxclass": "live.drop",
        "numinlets": 1,
        "numoutlets": 2,
        "outlettype": ["", ""],
        "patching_rect": patching_rect or [700, 1700, rect[2], rect[3]],
        "presentation": 1,
        "presentation_rect": rect,
    }
    if saved_attrs is not None:
        box["parameter_enable"] = 1
        box["saved_attribute_attributes"] = saved_attrs
        box["varname"] = param_name
    for key, val in (("decodemode", decodemode), ("color", color),
                     ("textcolor", textcolor), ("bordercolor", bordercolor),
                     ("focusbordercolor", focusbordercolor), ("legend", legend),
                     ("textjustification", textjustification),
                     ("fontname", fontname), ("fontsize", fontsize),
                     ("ignoreclick", ignoreclick)):
        if val is not None:
            box[key] = val
    box.update(kwargs)
    return {"box": box}


def bpatcher(id: str, rect: list, patcher_name: str, *, args: str = None,
             embed: int = 1, numinlets: int = 0, numoutlets: int = 0,
             patching_rect: list = None, **kwargs) -> dict:
    """Create a bpatcher embeddable sub-patcher.

    embed: 1 stores the sub-patch inside the device file.
    """
    box = {
        "id": id,
        "maxclass": "bpatcher",
        "numinlets": numinlets,
        "numoutlets": numoutlets,
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


def swatch(id: str, rect: list, *, compatibility: int = None,
           parameter_enable: int = None, patching_rect: list = None,
           **kwargs) -> dict:
    """Create a ``swatch`` colour picker / display.

    MEASURED from the official M4L corpus (1 instance). A clickable colour field that
    outputs the chosen colour. **3 inlets / 2 outlets** ``["", "float"]`` (the prior
    stub's 1-in / 4-out was guessed and WRONG) — outlet 0 emits the colour (list),
    outlet 1 a float. It has no styling box attrs (its displayed colour IS its runtime
    VALUE, set by a message); the only measured attrs are ``compatibility`` (a Max
    compatibility-mode flag) and ``parameter_enable`` (corpus 0). NICHE for audio —
    use it for a colour-pick utility / a user-themeable accent control; for a normal
    value use a ``live.*`` control.
    """
    box = {
        "id": id,
        "maxclass": "swatch",
        "numinlets": 3,
        "numoutlets": 2,
        "outlettype": ["", "float"],
        "patching_rect": patching_rect or [700, 1900, rect[2], rect[3]],
        "presentation": 1,
        "presentation_rect": rect,
    }
    if compatibility is not None:
        box["compatibility"] = compatibility
    if parameter_enable is not None:
        box["parameter_enable"] = parameter_enable
    box.update(kwargs)
    return {"box": box}


def textedit(id: str, rect: list, *, fontname: str = "Ableton Sans Medium",
             fontsize: float = 10.0, text: str = None, textcolor: list = None,
             bgcolor: list = None, textjustification: int = None,
             keymode: int = None, tabmode: int = None, border: float = None,
             rounded: float = None, parameter_enable: int = None,
             patching_rect: list = None, **kwargs) -> dict:
    """Create a ``textedit`` editable text / numeric entry field.

    NOT in the synced Max docs — MEASURED from the corpus (4 instances, Roulette /
    SliceShuffler, used as small numeric entry fields). 1 inlet / 4 outlets;
    **outlettype ``['', 'int', '', '']``** (the int is on outlet **1** — the prior
    stub's int-on-outlet-3 was WRONG). On Enter the typed text/number is reported.
    Measured attrs: ``text`` (initial / stored string, e.g. '0' / '127'), ``keymode``
    (1 = key handling on), ``tabmode`` (0), ``textjustification`` (1 = center),
    ``border`` / ``rounded`` (corpus 0 — flat borderless), ``bgcolor`` (corpus alpha-0
    transparent, themed at runtime), ``textcolor``. ``parameter_enable=1`` makes it a
    **Blob parameter** (``parameter_type 3``) that SAVES the text with the device —
    pass it only when you also wire the saved-attr blob. Themed:
    ``textcolor → text``, ``bgcolor → section``. **Use for** a small editable
    value/name field; for a plain numeric parameter prefer ``live.numbox``.
    """
    box = {
        "id": id,
        "maxclass": "textedit",
        "numinlets": 1,
        "numoutlets": 4,
        "outlettype": ["", "int", "", ""],
        "fontname": fontname,
        "fontsize": fontsize,
        "patching_rect": patching_rect or [700, 2000, rect[2], rect[3]],
        "presentation": 1,
        "presentation_rect": rect,
    }
    for key, val in (("text", text), ("textcolor", textcolor), ("bgcolor", bgcolor),
                     ("textjustification", textjustification), ("keymode", keymode),
                     ("tabmode", tabmode), ("border", border), ("rounded", rounded),
                     ("parameter_enable", parameter_enable)):
        if val is not None:
            box[key] = val
    box.update(kwargs)
    return {"box": box}


# --- Phase 5: Additional UI Objects ---


def live_step(id: str, rect: list, *, mode: int = None,
              parameter_enable: int = None, stepcolor: list = None,
              stepcolor2: list = None, bgcolor: list = None,
              bgcolor2: list = None, blackkeycolor: list = None,
              bordercolor: list = None, loopbordercolor: list = None,
              loopruler: int = None, unitruler: int = None,
              pitch_active: int = None, velocity_active: int = None,
              duration_active: int = None, extra2_active: int = None,
              patching_rect: list = None, **kwargs) -> dict:
    """Create a ``live.step`` multi-lane step sequencer.

    NOT in the synced Max docs — every attribute here is MEASURED from the real
    corpus (4 instances, SliceShuffler's Mod/Pan/Direction/Slice lanes), not guessed.
    Structure: **1 inlet / 5 outlets** (pitch, velocity, duration, extra1, extra2 lane
    data). It is a **Blob parameter** (``parameter_enable=1`` + ``parameter_type=3``
    stores the WHOLE pattern as one saved/automatable list — same family as
    ``matrixctrl`` / ``multislider`` / ``live.grid``); the step count lives inside that
    Blob, NOT in a ``nstep`` attr. Lanes are toggled by ``pitch_active`` /
    ``velocity_active`` / ``duration_active`` / ``extra2_active`` (corpus disables all
    but one editable lane); ``extra1`` is ranged via ``extra1_min`` / ``extra1_max`` /
    ``extra1_signed`` (pass through ``**kwargs``). ``mode`` selects the shown lane
    (corpus uses 4). Colors (two-shade gradients): ``stepcolor`` / ``stepcolor2`` (the
    step bars), ``bgcolor`` / ``bgcolor2`` (backdrop), ``blackkeycolor`` (pitch-row
    black keys), ``bordercolor`` / ``loopbordercolor``; ``loopruler`` / ``unitruler``
    toggle the rulers. Themed: ``stepcolor→accent``, ``bgcolor→bg``,
    ``bordercolor→panel_border``. Full Blob-param automation (emitting the
    ``parameter_initial`` blob) is a separate step — pass ``parameter_enable`` only
    when you wire that yourself.
    """
    box = {
        "id": id,
        "maxclass": "live.step",
        "numinlets": 1,
        "numoutlets": 5,
        "outlettype": ["", "", "", "", ""],
        "patching_rect": patching_rect or [700, 2100, rect[2], rect[3]],
        "presentation": 1,
        "presentation_rect": rect,
    }
    for key, val in (("mode", mode), ("parameter_enable", parameter_enable),
                     ("stepcolor", stepcolor), ("stepcolor2", stepcolor2),
                     ("bgcolor", bgcolor), ("bgcolor2", bgcolor2),
                     ("blackkeycolor", blackkeycolor), ("bordercolor", bordercolor),
                     ("loopbordercolor", loopbordercolor), ("loopruler", loopruler),
                     ("unitruler", unitruler), ("pitch_active", pitch_active),
                     ("velocity_active", velocity_active),
                     ("duration_active", duration_active),
                     ("extra2_active", extra2_active)):
        if val is not None:
            box[key] = val
    box.update(kwargs)
    return {"box": box}


def live_grid(id: str, rect: list, *, columns: int = 16, rows: int = 8,
              maxcolumns: int = None, maxrows: int = None, direction: int = None,
              parameter_enable: int = None, stepcolor: list = None,
              bgstepcolor: list = None, bgstepcolor2: list = None,
              bordercolor: list = None, bordercolor2: list = None,
              hbgcolor: list = None, directioncolor: list = None,
              marker_horizontal: int = None, marker_vertical: int = None,
              rounded: float = None, patching_rect: list = None,
              **kwargs) -> dict:
    """Create a ``live.grid`` monome-style cell sequencer.

    NOT in the synced Max docs — every attribute is MEASURED from the real corpus
    (2 instances: Roulette's 12×12 PitchMap, SliceShuffler's 32×32 Sequencer), not
    guessed. Structure: **2 inlets / 6 outlets** (the prior stub's 1/4 was wrong). It
    is a **Blob parameter** (``parameter_enable=1`` + ``parameter_type=3`` saves the
    whole grid as one automatable list). ``rows`` / ``columns`` set the visible grid;
    ``maxrows`` / ``maxcolumns`` cap a resizable grid. ``direction`` picks the play
    direction mode; ``marker_horizontal`` / ``marker_vertical`` draw guide lines;
    ``rounded`` rounds cells. Colors: ``stepcolor`` (the lit/active cell — Roulette
    orange, SliceShuffler magenta), ``bgstepcolor`` / ``bgstepcolor2`` (the unlit-cell
    two-shade backdrop), ``bordercolor`` / ``bordercolor2``, ``hbgcolor`` (playhead-
    column highlight), ``directioncolor`` (the direction-arrow strip). Themed:
    ``stepcolor→accent``, ``bgstepcolor→section``, ``bordercolor→panel_border``,
    ``directioncolor→accent2``. Pass ``parameter_enable`` only when you wire the
    ``parameter_initial`` blob yourself.
    """
    box = {
        "id": id,
        "maxclass": "live.grid",
        "numinlets": 2,
        "numoutlets": 6,
        "outlettype": ["", "", "", "", "", ""],
        "columns": columns,
        "rows": rows,
        "patching_rect": patching_rect or [700, 2200, rect[2], rect[3]],
        "presentation": 1,
        "presentation_rect": rect,
    }
    for key, val in (("maxcolumns", maxcolumns), ("maxrows", maxrows),
                     ("direction", direction), ("parameter_enable", parameter_enable),
                     ("stepcolor", stepcolor), ("bgstepcolor", bgstepcolor),
                     ("bgstepcolor2", bgstepcolor2), ("bordercolor", bordercolor),
                     ("bordercolor2", bordercolor2), ("hbgcolor", hbgcolor),
                     ("directioncolor", directioncolor),
                     ("marker_horizontal", marker_horizontal),
                     ("marker_vertical", marker_vertical), ("rounded", rounded)):
        if val is not None:
            box[key] = val
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
                blinkcolor: list = None, bordercolor: list = None,
                textcolor: list = None, color: list = None, blinktime: int = None,
                uparrow: int = None, downarrow: int = None, leftarrow: int = None,
                rightarrow: int = None, textjustification: int = None,
                ignoreclick: int = None, parameter_enable: int = None,
                patching_rect: list = None, **kwargs) -> dict:
    """Create a ``live.arrows`` direction-arrow control.

    DOC-VERIFIED (live.arrows maxref). On click it sends the **symbol** ``left`` /
    ``up`` / ``down`` / ``right`` to its single outlet (NOT a number) — wire those to
    your own increment / rotate / nudge logic. 1 inlet / 1 outlet (``[""]``). Which
    arrows are shown is set by ``uparrow`` / ``downarrow`` / ``leftarrow`` /
    ``rightarrow`` [int, default 1]: a vertical up/down stepper = ``leftarrow 0`` +
    ``rightarrow 0``; a horizontal pair = ``uparrow 0`` + ``downarrow 0``. Colors
    (doc-verified, NO ``active*`` twins): ``arrowcolor`` (the arrows), ``blinkcolor``
    (flash on press) + ``blinktime`` [ms, default 150], ``bordercolor``, ``textcolor``,
    ``color`` (object color); ``textjustification`` aligns text. (The old
    ``arrowbgcolor`` kwarg was a non-existent attr — removed.) Supports a
    ``jspainterfile`` painter; ``parameter_enable`` opt-in. **Use for** a rotate / nudge
    / step control (SliceShuffler uses it to rotate the cell sequence); for a numeric
    value prefer ``live.numbox`` / ``live.dial``.
    """
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
    for key, val in (("arrowcolor", arrowcolor), ("blinkcolor", blinkcolor),
                     ("bordercolor", bordercolor), ("textcolor", textcolor),
                     ("color", color), ("blinktime", blinktime),
                     ("uparrow", uparrow), ("downarrow", downarrow),
                     ("leftarrow", leftarrow), ("rightarrow", rightarrow),
                     ("textjustification", textjustification),
                     ("ignoreclick", ignoreclick),
                     ("parameter_enable", parameter_enable)):
        if val is not None:
            box[key] = val
    box.update(kwargs)
    return {"box": box}


def rslider(id: str, rect: list, *, min_val: int = 0, max_val: int = 127,
            bgcolor: list = None, fgcolor: list = None,
            patching_rect: list = None, **kwargs) -> dict:
    """Create an rslider range slider (two handles selecting a min..max range).

    ⚠️ NOT M4L-idiomatic / UNGROUNDED. ``rslider`` is a stock-Max control with NO
    ``live.*`` theming — it renders unthemed/out-of-place in a premium device — and
    is absent from the synced Max docs, used by ZERO commercial-corpus devices, ZERO
    M4L Factory-Pack devices, and ZERO kit devices (verified 2026-06 across all
    three sources). It is NOT a Live parameter (does not save/automate). The
    ``min``/``max`` box attrs set here are therefore UNVERIFIED (no maxref to ground
    them; never guess). For a level/range control inside a device use ``slider``
    (live.slider — verified, themes to the accent, saves as a parameter) for a
    single value, or a **custom v8ui** (``add_xy_pad`` / a bespoke range bar) when
    you genuinely need a two-ended range. Reserve ``rslider`` for a non-Live Max
    patch where the plain look + unverified attrs are acceptable.
    """
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
    """Create a textbutton text button (classic Max, NO Live parameter storage —
    for an automatable button use ``live_text``/``button`` instead).

    ``mode``: 0 = Button (momentary bang on click), 1 = Toggle (latching). In Toggle
    mode the ``bgoncolor`` on-state background only PERSISTS when ``usebgoncolor=1``
    (Max default is 0), so this factory auto-sets it whenever a toggle has a
    ``bgoncolor`` — otherwise the latched button shows its on-LABEL (``texton``) but
    never its on-COLOUR. Button mode flashes ``bgoncolor`` briefly with no flag needed.
    """
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
        # textbutton's bgoncolor only PERSISTS in Toggle mode when usebgoncolor=1;
        # without it a latched toggle never shows its on-bg (Button mode just flashes
        # it briefly, no flag needed). Auto-enable for toggles; kwargs can override.
        if mode == 1:
            box["usebgoncolor"] = 1
    if textcolor:
        box["textcolor"] = textcolor
    if textoncolor:
        box["textoncolor"] = textoncolor
    box.update(kwargs)
    return {"box": box}


def umenu(id: str, rect: list, *, items: list = None,
          patching_rect: list = None, display: bool = False,
          arrow: int = None, ignoreclick: int = None, allowdrag: int = None,
          bgcolor: list = None, textcolor: list = None,
          fontname: str = None, fontsize: float = None,
          **kwargs) -> dict:
    """Create a ``umenu`` — a NON-parameter dropdown: it outputs the selected int
    index and is NOT automatable/saved. For an automatable enum parameter use
    :func:`menu` (``live.menu``) instead.

    PREMIUM USAGE (measured: 25/26 corpus ``umenu`` instances): ``umenu`` is used
    almost exclusively as a STYLED READ-ONLY DISPLAY — ``ignoreclick=1`` (clicks do
    nothing), ``arrow=0`` (no dropdown triangle), ``allowdrag=0``, a flat
    ``bgfillcolor`` fill + centered text — driven programmatically by a
    ``set <index>`` message (a filled value readout, NOT a picker). Pass
    ``display=True`` for that preset.

    ⚠️ A umenu's RENDERED background is ``bgfillcolor`` (the modern "Color" attr), NOT
    bare ``bgcolor``: corpus-measured, 25/25 umenus set ``bgfillcolor_type "color"``
    with ``bgfillcolor_color == bgcolor`` — a FLAT fill (``bgfillcolor_color1/color2``
    are stored but unused at type ``color``; it is NOT a rendered gradient). So a
    themed ``bgcolor`` is MIRRORED here into a flat ``bgfillcolor`` automatically — set
    only ``bgcolor`` and the readout would otherwise draw Max's default fill and ignore
    the theme. Pass explicit ``bgfillcolor_*`` kwargs to override (e.g. a real gradient).
    """
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
    if display:
        # the verified read-only-readout preset (overridable below / via kwargs)
        box["ignoreclick"] = 1
        box["arrow"] = 0
        box["allowdrag"] = 0
    for key, val in (
        ("arrow", arrow), ("ignoreclick", ignoreclick), ("allowdrag", allowdrag),
        ("bgcolor", bgcolor), ("textcolor", textcolor),
        ("fontname", fontname), ("fontsize", fontsize),
    ):
        if val is not None:
            box[key] = val
    if items is not None:
        box["items"] = items
    # Mirror a themed bg into a FLAT bgfillcolor (the corpus pattern: type "color",
    # bgfillcolor_color == bgcolor) so the readout actually renders the theme colour
    # instead of Max's default fill. Explicit bgfillcolor_* kwargs win (applied below).
    if bgcolor is not None:
        box.setdefault("bgfillcolor_type", "color")
        box.setdefault("bgfillcolor_color", bgcolor)
    box.update(kwargs)
    return {"box": box}


def radiogroup(id: str, rect: list, *, itemcount: int = 4,
               value: int = None, mode: int = None,
               patching_rect: list = None, **kwargs) -> dict:
    """Create a radiogroup (plain-Max radio buttons / checkboxes).

    ⚠️ NOT M4L-idiomatic. ``radiogroup`` is a stock-Max control with NO ``live.*``
    theming — it renders unthemed/out-of-place in a premium device — and is used by
    ZERO M4L Factory Pack devices (verified 2026-06) and absent from the synced
    docs. For an enum / segmented selector inside a device use ``tab`` (live.tab —
    shows ALL options at once, best ≤4 segments, ≈40 px/seg) or ``menu`` (live.menu
    — a dropdown, best for many options); both theme to the device accent and SAVE
    as a Live parameter. Reserve ``radiogroup`` for a non-Live Max patch where the
    plain look is fine.

    The outlet emits the selected button INDEX as an int. ``mode``: 0 = Radio
    Button (exclusive single-select, the default), 1 = Check Box (independent
    per-button toggles, value is a bitmask). Color attrs are NOT in the synced
    docs and no corpus device uses it, so they are left to raw kwargs (unverified)
    rather than a guessed theme_mapping.
    """
    box = {
        "id": id,
        "maxclass": "radiogroup",
        "numinlets": 1,
        "numoutlets": 1,
        "outlettype": ["int"],
        "itemcount": itemcount,
        "patching_rect": patching_rect or [700, 2800, rect[2], rect[3]],
        "presentation": 1,
        "presentation_rect": rect,
    }
    if value is not None:
        box["value"] = value
    if mode is not None:
        box["mode"] = mode
    box.update(kwargs)
    return {"box": box}


def nodes(id: str, rect: list, *, numnodes: int = 4, xmin: float = None,
          xmax: float = None, ymin: float = None, ymax: float = None,
          patching_rect: list = None, **kwargs) -> dict:
    """Create a ``nodes`` XY node editor (draggable circular nodes in a 2D field).

    ⚠️ UNGROUNDED + non-M4L. ``nodes`` is a stock-Max object but is absent from the
    synced Max docs AND used by ZERO devices across the Ableton Factory Packs and the
    downloaded commercial corpus (verified 2026-06) — so the IO and attrs here
    (3 outlets; ``numnodes`` / ``xmin`` / ``xmax`` / ``ymin`` / ``ymax``) are
    UNVERIFIED guesses, and it carries no ``live.*`` theming (renders out-of-place in
    a device). For device UI prefer: ``function`` (breakpoint / transfer curve),
    ``filtergraph~`` (filter response), ``live.adsrui`` (envelope), or a custom
    ``v8ui`` for a true 2D XY pad / multi-point editor (themed, full control).
    Reserve ``nodes`` for a non-Live Max patch."""
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
               patching_rect: list = None, autosize: int = 1,
               ignoreclick: int = None, bgcolor: list = None,
               color: list = None, elementcolor: list = None,
               **kwargs) -> dict:
    """Create a ``matrixctrl`` — a ``rows``×``columns`` grid of toggle cells (routing
    matrix, mod matrix, step row).

    Verified from the corpus (7 instances): ``autosize=1`` (6/7, the Max default —
    cells auto-fit the rect), and most are ``ignoreclick=1`` *displays* driven by the
    patch (showing a step pattern / routing state), not interactive. The interactive
    one is a 1×16 step row that's a **Blob parameter** (``parameter_enable=1`` +
    ``parameter_type=3`` stores the WHOLE grid state, automatable/saved). Cell colors
    (``color`` = ON cell, ``elementcolor`` = OFF cell, ``bgcolor`` = backdrop) are
    themed; when a runtime ``live.colors`` bus drives them the SAVED colors are
    alpha-0. **Use when** you need a compact multi-cell on/off grid; for a single
    multi-value slider strip use ``multislider`` / ``live.step``.
    """
    box = {
        "id": id,
        "maxclass": "matrixctrl",
        "numinlets": 1,
        "numoutlets": 2,
        "outlettype": ["list", "list"],
        "rows": rows,
        "columns": columns,
        "autosize": autosize,
        "patching_rect": patching_rect or [700, 3000, rect[2], rect[3]],
        "presentation": 1,
        "presentation_rect": rect,
    }
    for key, val in (("ignoreclick", ignoreclick), ("bgcolor", bgcolor),
                     ("color", color), ("elementcolor", elementcolor)):
        if val is not None:
            box[key] = val
    box.update(kwargs)
    return {"box": box}


def ubutton(id: str, rect: list, *, hltcolor: list = None, handoff: str = None,
            patching_rect: list = None, **kwargs) -> dict:
    """Create a ``ubutton`` — an invisible click zone over graphics.

    MEASURED from the official M4L corpus (43 instances across 14 devices, 100%
    consistent). 1 inlet / **4 outlets** ``["bang", "bang", "", "int"]`` — outlet 0
    bangs on mouse-UP (release inside), outlet 1 bangs on mouse-DOWN, outlet 3 is the
    ``int`` button state (1 down / 0 up). (The prior stub's outlet 1 was wrongly
    ``""`` — it is a down-bang.) Real attrs: ``hltcolor`` = the highlight flash drawn
    on click (ubutton's ONLY color — it is otherwise transparent), ``handoff`` = a
    name to forward clicks to a partner ``ubutton``. ``annotation`` / ``varname`` are
    common. Themed: ``hltcolor → accent``. **Use to** make an ``fpic`` / drawn region
    clickable (a graphic button, a clickable logo, a hotspot on a jsui hero); for a
    visible automatable trigger use ``live.button``, for a labelled action use
    ``textbutton``.
    """
    box = {
        "id": id,
        "maxclass": "ubutton",
        "numinlets": 1,
        "numoutlets": 4,
        "outlettype": ["bang", "bang", "", "int"],
        "patching_rect": patching_rect or [700, 3100, rect[2], rect[3]],
        "presentation": 1,
        "presentation_rect": rect,
    }
    if hltcolor is not None:
        box["hltcolor"] = hltcolor
    if handoff is not None:
        box["handoff"] = handoff
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


# --- Compiled signal-display objects (native C++, portable) --------------------
# These render in native Max code — smoother/cheaper than hand-drawn jsui — and
# ship WITH Max so devices stay portable. Like scope()/meter() they return a box
# dict (add via device.add_box). To LAYER one behind a transparent jsui (compiled
# fill + custom jsui overlay on top), use GraphContainer.add_compiled_ui instead,
# which also handles the optional signal feed. I/O counts are parameters because
# they vary by config — set them to match your patch.

def plot(id: str, rect: list, *, numinlets: int = 1, numoutlets: int = 1,
         outlettype: list = None, patching_rect: list = None, **attrs) -> dict:
    """Create a ``plot~`` — a compiled curve/data plotter.

    ⚠️ UNGROUNDED. ``plot~`` is absent from the synced Max docs (only the unrelated
    Jitter ``jit.plot`` is documented) AND used by ZERO devices across the Ableton
    Factory Packs and the downloaded commercial corpus (verified 2026-06), so the
    attrs suggested here (``rgba`` / ``bgrgba`` / ``range`` / ``domain`` / ``style``)
    are UNVERIFIED — confirm them in Max before relying on them. For a GROUNDED
    display prefer: ``scope`` (live.scope~, signal time-domain), ``function`` /
    ``multislider`` (breakpoint or bar data), ``filtergraph~`` (filter response),
    ``spectroscope~`` (spectrum), or a custom ``v8ui`` curve — all corpus-verified
    and themed. Reach for ``plot~`` only when you specifically need it and have
    checked its real attribute set.
    """
    box = {
        "id": id,
        "maxclass": "plot~",
        "numinlets": numinlets,
        "numoutlets": numoutlets,
        "patching_rect": patching_rect or [700, 3400, rect[2], rect[3]],
        "presentation": 1,
        "presentation_rect": rect,
    }
    if outlettype is not None:
        box["outlettype"] = outlettype
    box.update(attrs)
    return {"box": box}


def filtergraph(id: str, rect: list, *, numinlets: int = 8, numoutlets: int = 7,
                outlettype: list = None, domain: list = None,
                value_range: list = None, nfilters: int = None,
                setfilter: list = None, logmarkers: list = None,
                dbdisplay: int = None, numdisplay: int = None,
                bgcolor: list = None, curvecolor: list = None,
                hcurvecolor: list = None, markercolor: list = None,
                bwidthcolor: list = None, fgcolor: list = None,
                textcolor: list = None, patching_rect: list = None, **attrs) -> dict:
    """Create a ``filtergraph~`` — the COMPILED interactive filter-response editor.

    MEASURED from the official M4L corpus (11 instances, 100% consistent). Drag the
    curve to design a filter; outlet 0 emits the coefficient **list** to feed
    ``biquad~`` / ``cascade~``, so it is BOTH the UI and the coefficient source.
    **8 inlets / 7 outlets** ``["list","float","float","float","float","list","int"]``
    (the prior stub's 1/1 was wrong). Key attrs:
    - ``domain`` [lo, hi]: the X-axis frequency range (corpus ``[20.0, 22050.0]`` Hz).
    - ``value_range`` → ``range`` [lo, hi]: the Y-axis gain range (LINEAR amplitude,
      e.g. ``[0.0725, 4.0]``); set ``dbdisplay 1`` to label it in dB.
    - ``nfilters`` [int]: filter count. ``setfilter`` [list]: define a filter band
      ``[idx, type, bypass, …, freq, gain, Q, …]`` (corpus ``type`` enum, e.g. 6).
    - ``logmarkers`` [list]: log-spaced freq grid lines (corpus ``[50, 500, 5000]``).
      ``numdisplay`` toggles numeric readouts.
    - Colors: ``bgcolor``, ``markercolor`` (the freq GRID — NOT ``gridcolor``),
      ``curvecolor`` (the response curve), ``hcurvecolor`` (highlighted/active curve),
      ``bwidthcolor`` / ``hbwidthcolor`` (bandwidth fill), ``fgcolor``, ``textcolor``.
    ``parameter_enable`` is 0 in the corpus (a coefficient source, not a Live param).
    Themed ``bgcolor → scope_bgcolor``, ``markercolor → grid_color``,
    ``curvecolor → accent``, ``hcurvecolor → accent2``. **Use for** an EQ / filter
    response editor; for an arbitrary 2-param drawn curve use ``function`` or a v8ui.
    """
    box = {
        "id": id,
        "maxclass": "filtergraph~",
        "numinlets": numinlets,
        "numoutlets": numoutlets,
        "outlettype": outlettype or ["list", "float", "float", "float", "float",
                                     "list", "int"],
        "patching_rect": patching_rect or [700, 3500, rect[2], rect[3]],
        "presentation": 1,
        "presentation_rect": rect,
    }
    for key, val in (("domain", domain), ("range", value_range),
                     ("nfilters", nfilters), ("setfilter", setfilter),
                     ("logmarkers", logmarkers), ("dbdisplay", dbdisplay),
                     ("numdisplay", numdisplay), ("bgcolor", bgcolor),
                     ("curvecolor", curvecolor), ("hcurvecolor", hcurvecolor),
                     ("markercolor", markercolor), ("bwidthcolor", bwidthcolor),
                     ("fgcolor", fgcolor), ("textcolor", textcolor)):
        if val is not None:
            box[key] = val
    box.update(attrs)
    return {"box": box}


def function(id: str, rect: list, *, points: list = None, domain: float = None,
             value_range: list = None, mode: int = 1, classic_curve: int = None,
             parameter_enable: int = None, presentation: int = 1,
             patching_rect: list = None, **kwargs) -> dict:
    """Create a ``function`` — the native breakpoint / envelope / transfer-curve editor.

    NOT in the synced Max docs — MEASURED from the corpus (20 instances: Chiral &
    Superberry transfer curves). 1 inlet / **4 outlets** ``["float", "", "", "bang"]``
    (send an x value in → the y at that x comes out outlet 0; outlet 3 bangs on
    finish). In the corpus it is a **curve-DATA store** in the patching layer (no
    presentation, ``parameter_enable 0``) — you define a shape and the DSP reads it.
    Measured attrs:
    - ``points`` → ``addpoints_with_curve``: the breakpoint list, flat
      ``[x, y, flags, curve, …]`` per node (``curve`` = per-segment tension).
    - ``domain`` [float]: the X-axis max (input range, e.g. 1.0 or 100.0).
    - ``value_range`` → ``range`` [min, max]: the Y-axis output range (e.g. [0, 8]).
    - ``mode`` [int] (corpus 1) + ``classic_curve`` [int] (1 = classic interpolation).
    - ``parameter_enable`` [int]: opt-in (corpus is all 0 — a patch-internal store).
    Defaults to a VISIBLE editor (``presentation=1``, so it places in a layout like any
    UI control); pass ``presentation=0`` for the corpus-style patching-layer curve-DATA
    store. Its display colors are not corpus-grounded here, so set them via ``**kwargs``
    and Live-verify. **Use for** a velocity / transfer / response curve or a drawn
    envelope feeding gen~; for a single value use a dial.
    """
    box = {
        "id": id,
        "maxclass": "function",
        "numinlets": 1,
        "numoutlets": 4,
        "outlettype": ["float", "", "", "bang"],
        "mode": mode,
        "patching_rect": patching_rect or [700, 3600, rect[2], rect[3]],
    }
    if presentation:
        box["presentation"] = 1
        box["presentation_rect"] = rect
    for key, val in (("addpoints_with_curve", points), ("domain", domain),
                     ("range", value_range), ("classic_curve", classic_curve),
                     ("parameter_enable", parameter_enable)):
        if val is not None:
            box[key] = val
    box.update(kwargs)
    return {"box": box}


def waveform(id: str, rect: list, *, buffername: str = None,
             waveformcolor: list = None, selectioncolor: list = None,
             bgcolor: list = None, gridcolor: list = None,
             bordercolor: list = None, linecolor: list = None,
             labelbgcolor: list = None, labeltextcolor: list = None,
             labels: int = None, ruler: int = None, vticks: int = None,
             ignoreclick: int = None, setmode: int = None, allowdrag: int = None,
             patching_rect: list = None, **kwargs) -> dict:
    """Create a ``waveform~`` — a ``buffer~`` audio display with drag-to-select.

    MEASURED from the official M4L corpus (7 instances, 100% consistent). Draws the
    audio in a named ``buffer~`` and (unless ``ignoreclick``) lets the user drag-select
    a region. **5 inlets / 6 outlets** ``["float","float","float","float","list",""]`` —
    doc-verified order: inlets/outlets 0/1 are the DISPLAY window (start ms / length
    ms), 2/3 the SELECTION bounds (start / end ms), outlet 4 the raw mouse list,
    5 the link list. ``setmode`` picks the drag gesture (0 display-only, 1 Select,
    2 Loop, 3 Move/scrub-zoom, 4 Draw); ``outmode`` ("continuous"/"up"/...) sets
    when selection emits. ``buffername`` (required) = the ``buffer~`` to display. Colors:
    ``waveformcolor`` (the trace), ``selectioncolor`` (the drag-selection highlight),
    ``bgcolor``, ``gridcolor``, ``bordercolor``, ``linecolor``,
    ``labelbgcolor`` / ``labeltextcolor``. Display toggles: ``labels``, ``ruler`` (time
    ruler), ``vticks``. ``ignoreclick`` 1 = display-only (no selection);
    ``allowdrag`` / ``setmode`` control drag behaviour. Themed ``waveformcolor → accent``,
    ``selectioncolor → accent2``, ``bgcolor → scope_bgcolor``, ``gridcolor → grid_color``.
    **Use for** a sample / granular / buffer display + region picker (the visual
    front-end of a ``buffer~`` device); for a live signal trace use ``live.scope~``, for
    a spectrum use ``spectroscope~``.
    """
    box = {
        "id": id,
        "maxclass": "waveform~",
        "numinlets": 5,
        "numoutlets": 6,
        "outlettype": ["float", "float", "float", "float", "list", ""],
        "patching_rect": patching_rect or [700, 3700, rect[2], rect[3]],
        "presentation": 1,
        "presentation_rect": rect,
    }
    for key, val in (("buffername", buffername), ("waveformcolor", waveformcolor),
                     ("selectioncolor", selectioncolor), ("bgcolor", bgcolor),
                     ("gridcolor", gridcolor), ("bordercolor", bordercolor),
                     ("linecolor", linecolor), ("labelbgcolor", labelbgcolor),
                     ("labeltextcolor", labeltextcolor), ("labels", labels),
                     ("ruler", ruler), ("vticks", vticks),
                     ("ignoreclick", ignoreclick), ("setmode", setmode),
                     ("allowdrag", allowdrag)):
        if val is not None:
            box[key] = val
    box.update(kwargs)
    return {"box": box}


def pictctrl(id: str, rect: list, *, name: str = None, frames: int = None,
             mode: int = None, trackvertical: int = None,
             clickedimage: int = None, inactiveimage: int = None,
             active: int = None, parameter_enable: int = None,
             patching_rect: list = None, **kwargs) -> dict:
    """Create a ``pictctrl`` — an image-filmstrip control (custom knob / button / slider).

    MEASURED from the official M4L corpus (17 instances, 100% consistent). Displays one
    frame of a sprite image and outputs the frame INDEX as an **int**. 1 inlet / 1 outlet
    (``["int"]``). ``name`` = the sprite file (a filmstrip, e.g. a 68-frame vertical
    strip); ``frames`` = the frame count; ``mode`` = interaction (button / toggle /
    slider-drag); ``trackvertical`` 1 = frames stack VERTICALLY (drag up/down to change).
    ``clickedimage`` / ``inactiveimage`` flag use of the clicked / inactive sub-images in
    the sprite; ``active`` / ``parameter_enable`` opt-in. Requires bundling the sprite
    ``name`` as an asset (embed it like ``fpic``). **PREFER a ``jspainterfile`` painter on
    a native control** (see the premium-control method at the top) for a *themeable* custom
    look; reach for ``pictctrl`` only when you have a READY-MADE sprite filmstrip to drop
    in unchanged.
    """
    box = {
        "id": id,
        "maxclass": "pictctrl",
        "numinlets": 1,
        "numoutlets": 1,
        "outlettype": ["int"],
        "patching_rect": patching_rect or [700, 3800, rect[2], rect[3]],
        "presentation": 1,
        "presentation_rect": rect,
    }
    for key, val in (("name", name), ("frames", frames), ("mode", mode),
                     ("trackvertical", trackvertical), ("clickedimage", clickedimage),
                     ("inactiveimage", inactiveimage), ("active", active),
                     ("parameter_enable", parameter_enable)):
        if val is not None:
            box[key] = val
    box.update(kwargs)
    return {"box": box}


def spectrumdraw(id: str, rect: list, *, amprange: list = None, ampgrid: int = None,
                 amplabels: int = None, freqgrid: int = None, freqlabels: int = None,
                 color: list = None, color2: list = None, color3: list = None,
                 color4: list = None, thickness: float = None,
                 thickness2: float = None, thickness3: float = None,
                 thickness4: float = None, curvestyle: int = None,
                 bgcolor: list = None, bordercolor: list = None,
                 octavesmooth: float = None, timesmooth: list = None,
                 mousemode: int = None, mode: int = None, fftsize: int = None,
                 patching_rect: list = None, **kwargs) -> dict:
    """Create a ``spectrumdraw~`` — a multi-trace spectrum analyzer display.

    MEASURED from the official M4L corpus (4 instances, 100% consistent). **4 signal
    inlets / 1 outlet** (``[""]``) — feed up to 4 signals to OVERLAY 4 spectra (e.g.
    input vs output, or L / R). ``amprange`` [lo, hi] dB (corpus ``[-80, 10]``);
    ``ampgrid`` / ``amplabels`` / ``freqgrid`` / ``freqlabels`` toggle the grids +
    labels. Each of the 4 traces has its own color (``color`` / ``color2`` / ``color3``
    / ``color4``) and ``thickness`` / ``thickness2`` / ``thickness3`` / ``thickness4``.
    ``curvestyle`` = draw style; ``octavesmooth`` = fractional-octave smoothing (corpus
    ~1/6); ``timesmooth`` [attack, release] ms; ``fftsize`` index; ``mode``;
    ``mousemode``. Themed ``color → accent``, ``color2 → accent2``,
    ``bgcolor → scope_bgcolor``. **Use for** a spectrum / analyzer display (the native
    multi-trace FFT graph); for a waveform use ``waveform~`` / ``live.scope~``, for a
    filter response use ``filtergraph~``.
    """
    box = {
        "id": id,
        "maxclass": "spectrumdraw~",
        "numinlets": 4,
        "numoutlets": 1,
        "outlettype": [""],
        "patching_rect": patching_rect or [700, 3900, rect[2], rect[3]],
        "presentation": 1,
        "presentation_rect": rect,
    }
    for key, val in (("amprange", amprange), ("ampgrid", ampgrid),
                     ("amplabels", amplabels), ("freqgrid", freqgrid),
                     ("freqlabels", freqlabels), ("color", color),
                     ("color2", color2), ("color3", color3), ("color4", color4),
                     ("thickness", thickness), ("thickness2", thickness2),
                     ("thickness3", thickness3), ("thickness4", thickness4),
                     ("curvestyle", curvestyle), ("bgcolor", bgcolor),
                     ("bordercolor", bordercolor), ("octavesmooth", octavesmooth),
                     ("timesmooth", timesmooth), ("mousemode", mousemode),
                     ("mode", mode), ("fftsize", fftsize)):
        if val is not None:
            box[key] = val
    box.update(kwargs)
    return {"box": box}
