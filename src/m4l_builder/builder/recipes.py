"""Reusable stages, modules, and higher-level recipes."""

from collections import ChainMap as _ChainMap

from .. import modules as _modules
from .. import recipes as _recipes
from .. import stages as _stages
from .._exports import BUILDER_RECIPE_EXPORTS as _BUILDER_RECIPE_EXPORTS

_SOURCE_MODULES = (_recipes, _modules, _stages)

# Stage/ModuleSpec primitives re-exported here for convenience alongside the
# recipes built on them; already part of CORE_EXPORTS but not of the
# recipes-specific export group.
_SUPPLEMENTAL_EXPORTS = [
    "Stage",
    "StageResult",
    "stage_result",
    "ModuleSpec",
    "module_from_block",
    "mount_module",
]

__all__ = list(_BUILDER_RECIPE_EXPORTS) + _SUPPLEMENTAL_EXPORTS

_namespace = _ChainMap(*(vars(module) for module in _SOURCE_MODULES))
globals().update({name: _namespace[name] for name in __all__})
