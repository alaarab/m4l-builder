"""The registry-driven `add_*` widget methods carry static signatures.

`Device.add_<name>` and the layout-container proxies are declared in class
bodies from their ui.py factory, so type checkers see real arguments. These
tests keep those declarations in sync with `DEVICE_WIDGET_SPECS` and check
that mypy actually rejects a bad call.
"""

import inspect
import textwrap

import pytest

from m4l_builder import ui
from m4l_builder.device import Device
from m4l_builder.layout import _VARNAME_PROXY_WIDGETS, _LayoutContainer
from m4l_builder.ui_registry import (
    DEVICE_WIDGET_SPECS,
    POSITIONAL_SIGNATURE_SHIMS,
    DeviceWidgetMethods,
)


def _declared_widget_methods():
    return {
        name[len("add_"):]
        for name, value in vars(DeviceWidgetMethods).items()
        if name.startswith("add_") and callable(value)
    }


def test_every_registry_widget_is_declared():
    assert _declared_widget_methods() == set(DEVICE_WIDGET_SPECS)


@pytest.mark.parametrize("name", sorted(DEVICE_WIDGET_SPECS))
def test_declared_method_is_the_registry_wrapper(name):
    method = getattr(Device, f"add_{name}")
    assert method.__qualname__ == f"Device.add_{name}"
    assert DEVICE_WIDGET_SPECS[name].factory is getattr(ui, name)


@pytest.mark.parametrize("name", sorted(POSITIONAL_SIGNATURE_SHIMS))
def test_positional_shim_matches_factory(name):
    """Shims differ from the factory only in letting `keyword_only_args` be positional."""
    spec = DEVICE_WIDGET_SPECS[name]
    factory_params = list(inspect.signature(spec.factory).parameters.values())
    shim_params = list(inspect.signature(POSITIONAL_SIGNATURE_SHIMS[name]).parameters.values())
    positional = set(spec.keyword_only_args.values())

    def annotation(param):
        if param.kind == param.VAR_KEYWORD:
            return None
        return getattr(param.annotation, "__name__", param.annotation)

    def normalized(params):
        return sorted(
            (p.name, p.default, annotation(p), p.kind == p.VAR_KEYWORD) for p in params
        )

    assert normalized(shim_params) == normalized(factory_params)
    shim_positional = [p.name for p in shim_params if p.kind == p.POSITIONAL_OR_KEYWORD]
    factory_positional = [p.name for p in factory_params if p.kind == p.POSITIONAL_OR_KEYWORD]
    assert shim_positional[: len(factory_positional)] == factory_positional
    assert set(shim_positional[len(factory_positional):]) == positional


def test_every_widget_with_keyword_only_args_has_a_shim():
    needs_shim = {name for name, spec in DEVICE_WIDGET_SPECS.items() if spec.keyword_only_args}
    assert needs_shim == set(POSITIONAL_SIGNATURE_SHIMS)


def test_layout_proxies_are_declared_for_registry_widgets():
    for name in _VARNAME_PROXY_WIDGETS:
        assert name in DEVICE_WIDGET_SPECS
        assert "varname" in inspect.signature(DEVICE_WIDGET_SPECS[name].factory).parameters
        assert getattr(_LayoutContainer, f"add_{name}").__qualname__ == (
            f"_LayoutContainer.add_{name}")


_SNIPPET = textwrap.dedent('''
    from m4l_builder.device import AudioEffect
    from m4l_builder.graph import BoxRef

    d = AudioEffect("T", width=100, height=100)
    ok: BoxRef = d.add_dial("g", "Gain", [0, 0, 40, 40], min_val=-70.0)
    d.add_tab("t", "Mode", [0, 0, 40, 20], ["A", "B"])
    d.add_menu("m", "Pick", [0, 0, 40, 20], options=["A", "B"])
    d.add_dial("g2", "Gain", [0, 0, 40, 40], min_val="loud")
    d.add_meter("m2")
    with d.row(0, 0) as row:
        row.add_dial("g3", "Gain", width=40, min_val=0.0)
        row.add_panel("p", bgcolor=[0, 0, 0, 1], width=10)
        row.add_dial("g4", "Gain", initial="x")
''')


def test_mypy_sees_widget_signatures(tmp_path):
    api = pytest.importorskip("mypy.api")
    snippet = tmp_path / "snippet.py"
    snippet.write_text(_SNIPPET)
    stdout, _stderr, status = api.run([
        str(snippet), "--python-version", "3.9", "--no-incremental",
        "--config-file", "/dev/null", "--no-error-summary", "--hide-error-context",
    ])
    errors = [line for line in stdout.splitlines() if ": error:" in line]
    error_lines = sorted(int(line.split(":")[1]) for line in errors)
    # min_val="loud", add_meter without rect, layout initial="x".
    assert error_lines == [9, 10, 14], stdout
    assert status == 1
