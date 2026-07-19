"""Core graph, device, and serialization primitives."""

from collections import ChainMap as _ChainMap

from .. import assets as _assets
from .. import constants as _constants
from .. import container as _container
from .. import device as _device
from .. import freeze as _freeze
from .. import gen_lint as _gen_lint
from .. import gen_patcher as _gen_patcher
from .. import gen_sim as _gen_sim
from .. import gen_snippets as _gen_snippets
from .. import graph as _graph
from .. import jsui_contract as _jsui_contract
from .. import layout as _layout
from .. import modules as _modules
from .. import notes as _notes
from .. import objects as _objects
from .. import parameters as _parameters
from .. import paths as _paths
from .. import profiles as _profiles
from .. import stages as _stages
from .. import subpatcher as _subpatcher
from .. import validation as _validation
from .._exports import CORE_EXPORTS as _CORE_EXPORTS

_SOURCE_MODULES = (
    _assets,
    _constants,
    _container,
    _device,
    _freeze,
    _gen_lint,
    _gen_patcher,
    _gen_sim,
    _gen_snippets,
    _graph,
    _jsui_contract,
    _layout,
    _modules,
    _notes,
    _objects,
    _parameters,
    _paths,
    _profiles,
    _stages,
    _subpatcher,
    _validation,
)

__all__ = list(_CORE_EXPORTS)

_namespace = _ChainMap(*(vars(module) for module in _SOURCE_MODULES))
globals().update({name: _namespace[name] for name in __all__})
