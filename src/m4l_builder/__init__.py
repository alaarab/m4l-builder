"""m4l_builder: Programmatically build Max for Live (.amxd) devices.

The root package stays compatibility-oriented, but it now resolves most exports
lazily so importing `m4l_builder` does not eagerly load reverse/corpus tooling.
"""

from __future__ import annotations

from importlib import import_module

from ._exports import ROOT_ALL, ROOT_EXPORT_GROUPS, ROOT_NAMESPACE_MODULES

__all__ = list(ROOT_ALL)


def __getattr__(name: str):
    module_name = ROOT_NAMESPACE_MODULES.get(name)
    if module_name is not None:
        module = import_module(module_name)
        globals()[name] = module
        return module

    for module_name, exports in ROOT_EXPORT_GROUPS:
        if name in exports:
            value = getattr(import_module(module_name), name)
            globals()[name] = value
            return value

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
