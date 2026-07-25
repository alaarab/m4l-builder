"""Touch overlays — custom-UI surfaces that SELECT their parameter in Live.

THE GAP: a native ``live.dial`` tells Live "this parameter was touched" the
moment you click it, so Live focuses its automation lane. A CUSTOM drag
surface (v8ui packet / jar / band row) that routes values into a parked
param host does NOT — the lane never focuses.

WHY NOT THE LOM: in Live 12.4 the exposed ``DeviceParameter`` has no
``begin_gesture``/``end_gesture`` (only ``re_enable_automation`` /
``str_for_value``; empirically verified — the calls error), and
``Song.View.selected_parameter`` is read-only. There is no message-level way
to fake a native touch.

THE FIX (the corpus mechanism): put an INVISIBLE native control on top of
the drawn art and let it own the gesture. This is exactly how the premium
M4L corpus builds drawn controls ("jsui-drawn controls over hidden live.*
params" — Particle-Reverb teardown): the native object hosts the param,
handles the drag, reports the touch, and Live selects the lane. The art
below stays a pure display, driven by the control's value echo.

* :func:`add_touch_dial` — a fully transparent ``live.dial`` covering a
  rect. Vertical drag anywhere in the rect edits the value (live.dial's
  native drag), click selects the parameter in Live. The device's drawn
  art renders through from BELOW (add the overlay AFTER the art box —
  z-order is add-order).
* :func:`add_touch_menu` — a fully transparent ``live.menu`` covering a
  rect: click opens the native option picker AND selects the parameter.

Both return the box id; wire ``id -> prepend <param> -> gen`` and
``id -> prepend set_<x> -> display`` exactly as with any control.
"""

from __future__ import annotations

_CLEAR = [0.0, 0.0, 0.0, 0.0]


def _clear_dial_kwargs() -> dict:
    return dict(
        showname=0, shownumber=0, triangle=0,
        activedialcolor=list(_CLEAR), dialcolor=list(_CLEAR),
        activefgdialcolor=list(_CLEAR), fgdialcolor=list(_CLEAR),
        activeneedlecolor=list(_CLEAR), needlecolor=list(_CLEAR),
        bordercolor=list(_CLEAR), focusbordercolor=list(_CLEAR),
        textcolor=list(_CLEAR),
    )


def add_touch_dial(device, id: str, param_name: str, rect: list,
                   *, min_val: float = 0.0, max_val: float = 100.0,
                   initial: float = 0.0, unitstyle: int = 5,
                   **dial_kwargs) -> str:
    """An invisible ``live.dial`` hit-zone over ``rect``.

    The dial hosts the REAL parameter (automation / MIDI-map / undo / lane
    selection all native). Vertical drag anywhere in the rect edits it —
    live.dial's own drag behaviour, which is exactly the fader gesture a
    drawn packet/jar/row wants. All colours are alpha-0 so the art below
    shows through; pass explicit kwargs to override any of that.
    """
    kw = _clear_dial_kwargs()
    kw.update(dial_kwargs)
    device.add_dial(id, param_name, list(rect), min_val=min_val,
                    max_val=max_val, initial=initial, unitstyle=unitstyle,
                    **kw)
    return id


def add_touch_slider(device, id: str, param_name: str, rect: list,
                     *, min_val: float = 0.0, max_val: float = 100.0,
                     initial: float = 0.0, unitstyle: int = 5,
                     **slider_kwargs) -> str:
    """An invisible vertical ``live.slider`` hit-zone over ``rect``.

    THE control for tall drag surfaces (packets / jars / band rows):
    unlike ``live.dial`` — whose hit-zone is only its KNOB CIRCLE, not its
    rect (empirically probed; a transparent dial over a tall zone is dead
    everywhere but the knob) — a slider drags ANYWHERE in its rect, and a
    click sets the value at that height (which matches a drawn fill
    metaphor exactly). live.slider has no active-twin colours: the fill is
    the bare ``slidercolor`` (doc-verified in the kit registry); clearing
    it + ``textcolor`` + name/number flags makes it fully invisible.
    """
    kw = dict(
        showname=0, shownumber=0,
        slidercolor=list(_CLEAR), textcolor=list(_CLEAR),
    )
    kw.update(slider_kwargs)
    device.add_slider(id, param_name, list(rect), min_val=min_val,
                      max_val=max_val, initial=initial, unitstyle=unitstyle,
                      **kw)
    return id


def add_touch_menu(device, id: str, param_name: str, rect: list,
                   *, options: list, initial: int = 0,
                   **menu_kwargs) -> str:
    """An invisible ``live.menu`` hit-zone over ``rect``.

    Click opens the NATIVE option picker for ``options`` and selects the
    parameter in Live — the selectable replacement for a drawn tap-to-cycle
    surface (and a direct picker is better UX than cycling anyway).
    """
    kw = dict(
        bgcolor=list(_CLEAR), bgeditingcolor=list(_CLEAR),
        bordercolor=list(_CLEAR), focusbordercolor=list(_CLEAR),
        textcolor=list(_CLEAR), textjustification=1,
        arrow=0,
    )
    kw.update(menu_kwargs)
    device.add_menu(id, param_name, list(rect), options=list(options),
                    initial=initial, **kw)
    return id
