"""Internal widget registry for device-level UI wrappers."""

from __future__ import annotations

from dataclasses import dataclass, field

from .ui import (
    adsrui,
    bpatcher,
    button,
    comment,
    dial,
    fpic,
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
    radiogroup,
    rslider,
    scope,
    slider,
    swatch,
    tab,
    textbutton,
    textedit,
    toggle,
    ubutton,
    umenu,
)


@dataclass(frozen=True)
class DeviceWidgetSpec:
    """Metadata describing a `Device.add_*` wrapper."""

    factory: callable
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
        theme_mapping={"bgcolor": "scope_bgcolor", "activelinecolor": "scope_color"},
    ),
    "meter": DeviceWidgetSpec(
        meter,
        theme_mapping={
            "coldcolor": "meter_cold",
            "warmcolor": "meter_warm",
            "hotcolor": "meter_hot",
            "overloadcolor": "meter_over",
        },
    ),
    "menu": DeviceWidgetSpec(menu, parameter_arg_index=0, keyword_only_args={2: "options"}),
    "number_box": DeviceWidgetSpec(number_box, parameter_arg_index=0),
    "slider": DeviceWidgetSpec(slider, parameter_arg_index=0),
    "button": DeviceWidgetSpec(button, parameter_arg_index=0),
    "live_text": DeviceWidgetSpec(live_text, parameter_arg_index=0),
    "fpic": DeviceWidgetSpec(fpic),
    "live_gain": DeviceWidgetSpec(live_gain, parameter_arg_index=0),
    "multislider": DeviceWidgetSpec(multislider),
    "adsrui": DeviceWidgetSpec(adsrui),
    "live_drop": DeviceWidgetSpec(live_drop),
    "bpatcher": DeviceWidgetSpec(bpatcher),
    "swatch": DeviceWidgetSpec(swatch),
    "textedit": DeviceWidgetSpec(textedit),
    "live_step": DeviceWidgetSpec(live_step),
    "live_grid": DeviceWidgetSpec(live_grid),
    "live_line": DeviceWidgetSpec(live_line),
    "live_arrows": DeviceWidgetSpec(live_arrows),
    "rslider": DeviceWidgetSpec(rslider),
    "kslider": DeviceWidgetSpec(kslider),
    "textbutton": DeviceWidgetSpec(textbutton),
    "umenu": DeviceWidgetSpec(umenu),
    "radiogroup": DeviceWidgetSpec(radiogroup),
    "nodes": DeviceWidgetSpec(nodes),
    "matrixctrl": DeviceWidgetSpec(matrixctrl),
    "ubutton": DeviceWidgetSpec(ubutton),
    "nslider": DeviceWidgetSpec(nslider),
}
