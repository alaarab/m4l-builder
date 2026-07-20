"""UI widgets, themes, and display engines."""

from collections import ChainMap as _ChainMap

from .. import theme as _theme
from .. import ui as _ui
from .._exports import UI_EXPORTS as _UI_EXPORTS
from ..engines import sidechain_display as _sidechain_display
from ..engines import spectral_display as _spectral_display
from ..engines import wavetable_display as _wavetable_display
from ..engines import xy_pad as _xy_pad

_SOURCE_MODULES = (
    _sidechain_display,
    _spectral_display,
    _wavetable_display,
    _xy_pad,
    _theme,
    _ui,
)

__all__ = list(_UI_EXPORTS)

_namespace = _ChainMap(*(vars(module) for module in _SOURCE_MODULES))
globals().update({name: _namespace[name] for name in __all__})
