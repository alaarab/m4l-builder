"""Internal widget registry for device-level UI wrappers."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Generic

from .graph import GraphContainer
from .parameters import ParameterSpec
from .ui import (
    adsrui,
    bpatcher,
    button,
    comment,
    dial,
    filtergraph,
    fpic,
    function,
    kslider,
    live_arrows,
    live_drop,
    live_gain,
    live_grid,
    live_line,
    live_step,
    live_text,
    matrixctrl,
    menu,
    meter,
    multislider,
    nodes,
    nslider,
    number_box,
    panel,
    pictctrl,
    plot,
    radiogroup,
    rslider,
    scope,
    slider,
    spectrumdraw,
    swatch,
    tab,
    textbutton,
    textedit,
    toggle,
    ubutton,
    umenu,
    waveform,
)


@dataclass(frozen=True)
class DeviceWidgetSpec:
    """Metadata describing a `Device.add_*` wrapper."""

    factory: Callable[..., dict]
    theme_mapping: dict[str, str] = field(default_factory=dict)
    parameter_arg_index: int | None = None
    keyword_only_args: dict[int, str] = field(default_factory=dict)


def make_device_widget_method(widget_name: str, spec: DeviceWidgetSpec):
    """Build a `Device.add_*` wrapper from registry metadata."""

    def method(self, id: str, *args, **kwargs):
        if spec.theme_mapping:
            self._inject_theme(kwargs, spec.theme_mapping)
        if spec.keyword_only_args:
            positional_args = list(args)
            for arg_index, kwarg_name in sorted(spec.keyword_only_args.items(), reverse=True):
                if len(positional_args) > arg_index and kwarg_name not in kwargs:
                    kwargs[kwarg_name] = positional_args.pop(arg_index)
            args = tuple(positional_args)
        ref = self.add_box(spec.factory(id, *args, **kwargs))
        if spec.parameter_arg_index is not None:
            parameter_arg = (
                args[spec.parameter_arg_index]
                if len(args) > spec.parameter_arg_index
                else None
            )
            self._register_parameter_arg(ref, parameter_arg, kwargs)
        return ref

    method.__name__ = f"add_{widget_name}"
    method.__qualname__ = f"Device.add_{widget_name}"
    method.__doc__ = f"Add a `{widget_name}` widget to the device."
    return method


DEVICE_WIDGET_SPECS = {
    "panel": DeviceWidgetSpec(panel, theme_mapping={"bgcolor": "bg"}),
    "dial": DeviceWidgetSpec(
        dial,
        theme_mapping={
            "activedialcolor": "dial_color",
            "activeneedlecolor": "needle_color",
            # the reset-triangle marker (shown by default, triangle=1) was Live-
            # default; theme it to the needle color so it isn't an off-theme dot.
            "tricolor": "needle_color",
        },
        parameter_arg_index=0,
    ),
    "tab": DeviceWidgetSpec(
        tab,
        theme_mapping={
            "bgcolor": "tab_bg",
            "bgoncolor": "tab_bg_on",
            "textcolor": "tab_text",
            "textoncolor": "tab_text_on",
        },
        parameter_arg_index=0,
        keyword_only_args={2: "options"},
    ),
    "toggle": DeviceWidgetSpec(
        toggle,
        theme_mapping={"activebgoncolor": "accent"},
        parameter_arg_index=0,
    ),
    "comment": DeviceWidgetSpec(
        comment,
        theme_mapping={"textcolor": "text", "fontname": "fontname"},
    ),
    "scope": DeviceWidgetSpec(
        scope,
        # live.scope~ is a display: its trace color is the BARE linecolor (the
        # color you always see), like the meter — NOT activelinecolor. Verified
        # across the whole real-device corpus: only linecolor,
        # gridcolor, bgcolor are ever used; activelinecolor appears nowhere, so
        # the old mapping left themed scope traces Live-default.
        theme_mapping={
            "bgcolor": "scope_bgcolor",
            "linecolor": "scope_color",
            "gridcolor": "grid_color",
        },
    ),
    "plot": DeviceWidgetSpec(
        plot,
        theme_mapping={"bgcolor": "scope_bgcolor"},
    ),
    # filtergraph~ (corpus-measured): the freq grid is markercolor (NOT gridcolor —
    # that was dead); response curve = accent, highlighted curve = accent2.
    "filtergraph": DeviceWidgetSpec(
        filtergraph,
        theme_mapping={"bgcolor": "scope_bgcolor", "markercolor": "grid_color",
                       "curvecolor": "accent", "hcurvecolor": "accent2"},
    ),
    # function: native breakpoint/curve editor; corpus uses it as a patching-layer
    # curve-DATA store (no presentation, no colors) so it carries no theme_mapping.
    "function": DeviceWidgetSpec(function),
    # waveform~ (corpus-measured): buffer~ display + drag-select. Trace = accent,
    # selection highlight = accent2, display bg/grid from the scope tokens.
    "waveform": DeviceWidgetSpec(
        waveform,
        theme_mapping={"waveformcolor": "accent", "selectioncolor": "accent2",
                       "bgcolor": "scope_bgcolor", "gridcolor": "grid_color"},
    ),
    # spectrumdraw~ (corpus-measured): multi-trace FFT display. Primary trace =
    # accent, the comparison trace = accent2, display bg = scope bg.
    "spectrumdraw": DeviceWidgetSpec(
        spectrumdraw,
        theme_mapping={"color": "accent", "color2": "accent2",
                       "bgcolor": "scope_bgcolor"},
    ),
    "meter": DeviceWidgetSpec(
        meter,
        theme_mapping={
            "coldcolor": "meter_cold",
            "warmcolor": "meter_warm",
            "hotcolor": "meter_hot",
            "overloadcolor": "meter_over",
            # The UNLIT segments. live.gain~/meter~ have inactive twins ONLY for cold &
            # warm (no inactivehotcolor — hot/overload only show when triggered). Corpus
            # sets these to a mid-grey ~0.5 = the text_dim token, so the
            # meter track reads as a consistent dim rail instead of Live-default grey.
            "inactivecoldcolor": "text_dim",
            "inactivewarmcolor": "text_dim",
            # slidercolor = the meter's recessed BACKGROUND rail (live.gain~ maxref:
            # "the slider background color"). Corpus live.meter~ sets it dark ~0.098 (≈
            # the surface token, NOT the accent), so the channel behind the segments
            # matches the panel instead of Live-default grey. live_gain themes this too.
            "slidercolor": "surface",
        },
    ),
    "menu": DeviceWidgetSpec(
        menu,
        # live.menu has its OWN colour model (corpus-grounded, NOT live.tab's): the
        # factory routes bgoncolor -> hltcolor (highlighted item bg) and textoncolor ->
        # hlttextcolor (highlighted item TEXT). We feed the tab accent tokens so the
        # highlighted item matches the selected tab: bg = tab_bg_on (accent2), and its
        # TEXT = tab_text_on. Without the textoncolor mapping the highlighted item's text
        # stayed Live-default over the accent highlight (often illegible) — the corpus
        # themes hlttextcolor (6/25 menus), and the tab already maps all four colours;
        # this brings live.menu to parity.
        theme_mapping={"bgcolor": "tab_bg", "bgoncolor": "tab_bg_on",
                       "textcolor": "tab_text", "textoncolor": "tab_text_on"},
        parameter_arg_index=0,
        keyword_only_args={2: "options"},
    ),
    "number_box": DeviceWidgetSpec(
        number_box,
        # live.numbox colours are MODE-specific and each renders only in its appearance:
        # lcd* only at appearance=4 (the dominant premium look), activeslidercolor only at
        # appearance=2 (Slider), activebgcolor is the BODY bg for the non-LCD modes (0/1/3).
        # Setting an off-mode colour is harmless (not rendered), so theme them all
        # unconditionally — corpus-grounded: numboxes use activebgcolor (30) + bare textcolor
        # (41), never bare bgcolor (0); 17 corpus numboxes set activebgcolor AND lcd together.
        theme_mapping={
            "activebgcolor": "surface",
            "activeslidercolor": "dial_color",
            "textcolor": "text",
            "lcdcolor": "lcd_on",
            "lcdbgcolor": "lcd_bg",
            "inactivelcdcolor": "lcd_off",
        },
        parameter_arg_index=0,
    ),
    "slider": DeviceWidgetSpec(
        slider,
        # live.slider has NO activeslidercolor (doc-verified) — its fill is the
        # BARE slidercolor (no active twin, unlike live.numbox which DOES have
        # activeslidercolor). Mapping the non-existent active attr left themed
        # sliders Live-grey; slidercolor is the real fill. textcolor = the value
        # readout (doc-confirmed, set by 14/14 reference channel-strip sliders) — theme it
        # too or the digits render Live-default. The mod/automation triangle trio
        # (tricolor/trioncolor/tribordercolor) is left to Live's modulation colour.
        theme_mapping={"slidercolor": "dial_color", "textcolor": "text"},
        parameter_arg_index=0,
    ),
    "button": DeviceWidgetSpec(
        button,
        theme_mapping={"bgcolor": "surface", "bgoncolor": "accent"},
        parameter_arg_index=0,
    ),
    "live_text": DeviceWidgetSpec(
        live_text,
        # live.text is a full active-twin object; the factory mirrors each bare
        # color to its active* twin, so mapping the bare attrs themes the visible
        # (active=1) state. Was previously unthemed (Live-default).
        theme_mapping={"bgcolor": "surface", "bgoncolor": "accent", "textcolor": "text"},
        parameter_arg_index=0,
    ),
    "fpic": DeviceWidgetSpec(fpic),
    # pictctrl: image-filmstrip control (sprite frames -> int). No themeable colors
    # (the look IS the sprite art), so no theme_mapping — like fpic.
    "pictctrl": DeviceWidgetSpec(pictctrl),
    "live_gain": DeviceWidgetSpec(
        live_gain,
        theme_mapping={
            # Meter segments are the BARE attrs (inverted rule): these are the
            # LIT colors you see at active=1. Verified from the live.gain~ doc:
            # coldcolor=Cold, warmcolor=Warm, hotcolor=Warning, overloadcolor=Overload.
            "coldcolor": "meter_cold",
            "warmcolor": "meter_warm",
            "hotcolor": "meter_hot",
            "overloadcolor": "meter_over",
            # UNLIT cold/warm segments → dim rail (only cold & warm have inactive twins).
            "inactivecoldcolor": "text_dim",
            "inactivewarmcolor": "text_dim",
            "slidercolor": "dial_color",
            "textcolor": "text",
            # tricolor/trioncolor = the drag-triangle handle (unfocused/focused);
            # theme it to the accent so it isn't a stray Live-grey on dark devices.
            "tricolor": "dial_color",
            "trioncolor": "dial_color",
        },
        parameter_arg_index=0,
    ),
    # Verified corpus multislider colors: slidercolor=the bars (accent), bgcolor=backdrop.
    "multislider": DeviceWidgetSpec(
        multislider,
        theme_mapping={"slidercolor": "accent", "bgcolor": "bg"},
    ),
    # live.adsrui (corpus-measured): the active* colors are what render; the line +
    # handles take accent, the display bg the scope bg.
    "adsrui": DeviceWidgetSpec(
        adsrui,
        theme_mapping={"activebgcolor": "scope_bgcolor", "activelinecolor": "accent",
                       "activehandlecolor": "accent"},
    ),
    # live.drop colors (doc-verified): color=box outline, textcolor=display text,
    # bordercolor/focusbordercolor=border; NO bgcolor. Focus ring goes accent.
    "live_drop": DeviceWidgetSpec(
        live_drop,
        theme_mapping={"color": "panel_border", "textcolor": "text",
                       "bordercolor": "panel_border", "focusbordercolor": "accent"},
    ),
    "bpatcher": DeviceWidgetSpec(bpatcher),
    "swatch": DeviceWidgetSpec(swatch),
    # textedit (corpus-measured): editable text/numeric field; transparent bg +
    # colored text in the corpus. Theme the text + field bg.
    "textedit": DeviceWidgetSpec(
        textedit,
        theme_mapping={"textcolor": "text", "bgcolor": "section"},
    ),
    # Corpus-measured Blob-param sequencers (not in synced docs). step bars / lit
    # cell = accent; backdrop = bg/section; border = panel_border; grid direction
    # strip = accent2.
    # live.step / live.grid (sequencer lanes, no synced doc — grounded on measured
    # Max device conventions). Map only the SOLID (alpha=1.0) attrs to tokens:
    # the lit step (stepcolor=accent) + second step (stepcolor2=accent2), the grid
    # direction arrow (directioncolor=accent2) and the two borders. ⚠️ The PREMIUM look
    # also uses ALPHA-FADED washes a solid token CANNOT express — the zebra (bgstepcolor
    # white@0.05 / bgstepcolor2 white@0.10), the hover (hbgcolor accent@0.35) and the
    # amount overlay (amountcolor dim-accent@0.64). Do NOT token-map those (a solid accent
    # hover would paint the whole cell); set them per-device with explicit RGBA instead.
    "live_step": DeviceWidgetSpec(
        live_step,
        theme_mapping={"stepcolor": "accent", "stepcolor2": "accent2",
                       "bgcolor": "bg", "bordercolor": "panel_border"},
    ),
    "live_grid": DeviceWidgetSpec(
        live_grid,
        theme_mapping={"stepcolor": "accent", "bgstepcolor": "section",
                       "bordercolor": "panel_border", "bordercolor2": "panel_border",
                       "directioncolor": "accent2"},
    ),
    "live_line": DeviceWidgetSpec(
        live_line,
        # live.line is a divider; its ONLY style attr is linecolor (verified across
        # the corpus: 40 uses, no thickness/orientation attrs — orientation is
        # implicit from the rect aspect). Theme it to the subtle panel border so
        # dividers aren't a stray Live-default line. Was unthemed.
        theme_mapping={"linecolor": "panel_border"},
    ),
    # live.arrows (doc-verified): arrows pop in accent, press-flash in accent2,
    # text + border follow theme. No active* twins.
    "live_arrows": DeviceWidgetSpec(
        live_arrows,
        theme_mapping={"arrowcolor": "accent", "blinkcolor": "accent2",
                       "textcolor": "text", "bordercolor": "panel_border"},
    ),
    "rslider": DeviceWidgetSpec(rslider),
    "kslider": DeviceWidgetSpec(kslider),
    "textbutton": DeviceWidgetSpec(
        textbutton,
        theme_mapping={"bgcolor": "surface", "bgoncolor": "accent", "textcolor": "text"},
    ),
    # umenu is non-parameter; in the corpus it's a styled read-only display, so it
    # only needs bg + text colors (no on-state). Verified attrs from 25/26 corpus umenus.
    "umenu": DeviceWidgetSpec(
        umenu,
        theme_mapping={"bgcolor": "tab_bg", "textcolor": "tab_text"},
    ),
    "radiogroup": DeviceWidgetSpec(radiogroup),
    "nodes": DeviceWidgetSpec(nodes),
    # Verified cell-color attrs from corpus matrixctrl: color=ON cell (accent),
    # elementcolor=OFF cell, bgcolor=backdrop.
    "matrixctrl": DeviceWidgetSpec(
        matrixctrl,
        theme_mapping={"color": "accent", "elementcolor": "section", "bgcolor": "bg"},
    ),
    # ubutton: invisible click zone; its only color is hltcolor (the click flash).
    "ubutton": DeviceWidgetSpec(
        ubutton,
        theme_mapping={"hltcolor": "accent"},
    ),
    "nslider": DeviceWidgetSpec(nslider),
}


# --- Statically typed widget methods ---------------------------------------
#
# Each `add_*` wrapper is declared in a class body as ``add_dial =
# device_widget(dial)``. At runtime that is exactly the function built by
# `make_device_widget_method`; for type checkers it is a descriptor whose
# bound signature is the factory's minus the returned dict, e.g.
# ``(id: str, varname: str, rect: list, *, min_val: float = 0.0, ...) -> BoxRef``.
# ParamSpec/Concatenate are only needed by the checker, so the package keeps
# zero runtime dependencies on Python 3.10.

if TYPE_CHECKING:
    from typing import Concatenate

    from typing_extensions import ParamSpec

    from .graph import BoxRef

    _P = ParamSpec("_P")

    class WidgetMethod(Generic[_P]):
        """Checker-only view of a generated `add_*` method."""

        def __get__(self, obj: Any, owner: Any) -> Callable[Concatenate[str, _P], BoxRef]: ...

    class VarnameWidgetMethod(Generic[_P]):
        """Checker-only view of a layout proxy that keeps ``varname``."""

        def __get__(self, obj: Any, owner: Any) -> Callable[Concatenate[str, str, _P], BoxRef]: ...


# `tab`/`menu` declare `options` keyword-only, but their device wrappers also
# accept it positionally (`keyword_only_args`). These shims carry the wrapper's
# real call signature for type checkers; tests keep them in sync with ui.py.
def _tab_call(id: str, varname: str, rect: list, options: list, *,
              bgcolor: list | None = None, bgoncolor: list | None = None,
              textcolor: list | None = None, textoncolor: list | None = None,
              patching_rect: list | None = None, rounded: float = 0.0,
              spacing_x: float = 0.0, multiline: int = 0, appearance: int = 0,
              parameter: ParameterSpec | None = None,
              **kwargs: Any) -> dict:
    raise NotImplementedError  # signature shim only


def _menu_call(id: str, varname: str, rect: list, options: list, *,
               shortname: str | None = None, patching_rect: list | None = None,
               bgcolor: list | None = None, bgoncolor: list | None = None,
               textcolor: list | None = None, textoncolor: list | None = None,
               parameter: ParameterSpec | None = None,
               **kwargs: Any) -> dict:
    raise NotImplementedError  # signature shim only


POSITIONAL_SIGNATURE_SHIMS: dict[str, Callable[..., dict]] = {
    "tab": _tab_call,
    "menu": _menu_call,
}

_WIDGET_NAMES: dict[Callable[..., dict], str] = {
    **{spec.factory: name for name, spec in DEVICE_WIDGET_SPECS.items()},
    **{shim: name for name, shim in POSITIONAL_SIGNATURE_SHIMS.items()},
}


def widget_name(factory: Callable[..., dict]) -> str:
    """Registry name of a ui.py factory (or signature shim)."""
    return _WIDGET_NAMES[factory]


def device_widget(factory: Callable[Concatenate[str, _P], dict]) -> WidgetMethod[_P]:
    """Declare `Device.add_<factory>`, typed after its ui.py factory."""
    name = widget_name(factory)
    return make_device_widget_method(name, DEVICE_WIDGET_SPECS[name])  # type: ignore[return-value]


class DeviceWidgetMethods(GraphContainer):
    """The registry-driven `add_*` widget wrappers, mixed into Device."""

    add_panel = device_widget(panel)
    add_dial = device_widget(dial)
    add_tab = device_widget(_tab_call)
    add_toggle = device_widget(toggle)
    add_comment = device_widget(comment)
    add_scope = device_widget(scope)
    add_plot = device_widget(plot)
    add_filtergraph = device_widget(filtergraph)
    add_function = device_widget(function)
    add_waveform = device_widget(waveform)
    add_spectrumdraw = device_widget(spectrumdraw)
    add_meter = device_widget(meter)
    add_menu = device_widget(_menu_call)
    add_number_box = device_widget(number_box)
    add_slider = device_widget(slider)
    add_button = device_widget(button)
    add_live_text = device_widget(live_text)
    add_fpic = device_widget(fpic)
    add_pictctrl = device_widget(pictctrl)
    add_live_gain = device_widget(live_gain)
    add_multislider = device_widget(multislider)
    add_adsrui = device_widget(adsrui)
    add_live_drop = device_widget(live_drop)
    add_bpatcher = device_widget(bpatcher)
    add_swatch = device_widget(swatch)
    add_textedit = device_widget(textedit)
    add_live_step = device_widget(live_step)
    add_live_grid = device_widget(live_grid)
    add_live_line = device_widget(live_line)
    add_live_arrows = device_widget(live_arrows)
    add_rslider = device_widget(rslider)
    add_kslider = device_widget(kslider)
    add_textbutton = device_widget(textbutton)
    add_umenu = device_widget(umenu)
    add_radiogroup = device_widget(radiogroup)
    add_nodes = device_widget(nodes)
    add_matrixctrl = device_widget(matrixctrl)
    add_ubutton = device_widget(ubutton)
    add_nslider = device_widget(nslider)
