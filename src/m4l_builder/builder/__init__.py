"""Structured builder namespace for authoring Max for Live devices."""

from __future__ import annotations

from importlib import import_module

from .._exports import BUILDER_ALL, BUILDER_EXPORT_GROUPS, BUILDER_NAMESPACE_MODULES

__all__ = list(BUILDER_ALL)


def __getattr__(name: str):
    module_name = BUILDER_NAMESPACE_MODULES.get(name)
    if module_name is not None:
        module = import_module(module_name)
        globals()[name] = module
        return module

    for module_name, exports in BUILDER_EXPORT_GROUPS:
        if name in exports:
            value = getattr(import_module(module_name), name)
            globals()[name] = value
            return value

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
