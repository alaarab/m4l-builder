"""Live API helpers, controller shells, presets, and bridge tooling."""

from collections import ChainMap as _ChainMap

from .. import controller_shells as _controller_shells
from .. import live_api as _live_api
from .. import livemcp_bridge as _livemcp_bridge
from .. import paths as _paths
from .. import presets as _presets
from .._exports import LIVE_EXPORTS as _LIVE_EXPORTS

_SOURCE_MODULES = (
    _controller_shells,
    _live_api,
    _livemcp_bridge,
    _paths,
    _presets,
)

__all__ = list(_LIVE_EXPORTS)

_namespace = _ChainMap(*(vars(module) for module in _SOURCE_MODULES))
globals().update({name: _namespace[name] for name in __all__})
