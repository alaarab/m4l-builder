"""Reusable stage and module abstractions for builder recipes."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, Iterable, Mapping, Optional


class StageResult(dict):
    """Mapping-compatible stage result with semantic metadata."""

    def __init__(
        self,
        mapping: Mapping[str, Any] = None,
        *,
        name: str = None,
        params: Mapping[str, Any] = None,
        ports: Mapping[str, Any] = None,
        assets: Iterable[str] = None,
        validators: Iterable[Callable[..., Any]] = None,
        metadata: Mapping[str, Any] = None,
    ):
        super().__init__(mapping or {})
        self.name = name or "stage"
        self.params = dict(params or {})
        self.ports = dict(ports or {})
        self.assets = list(assets or [])
        self.validators = list(validators or [])
        self.metadata = dict(metadata or {})

    def port(self, name: str) -> Any:
        """Return a named port reference."""
        return self.ports[name]

    def param(self, name: str) -> Any:
        """Return a named parameter reference."""
        return self.params[name]


class Stage(ABC):
    """Base class for reusable graph stages."""

    name = "stage"

    @abstractmethod
    def build(self, graph, *args, **kwargs) -> StageResult:
        """Mount the stage on a graph and return its result."""


def stage_result(
    mapping: Mapping[str, Any] = None,
    *,
    name: str = None,
    params: Mapping[str, Any] = None,
    ports: Mapping[str, Any] = None,
    assets: Iterable[str] = None,
    validators: Iterable[Callable[..., Any]] = None,
    metadata: Mapping[str, Any] = None,
) -> StageResult:
    """Convenience constructor for StageResult."""
    return StageResult(
        mapping,
        name=name,
        params=params,
        ports=ports,
        assets=assets,
        validators=validators,
        metadata=metadata,
    )


def coerce_stage_result(result: Any, *, name: str = None) -> StageResult:
    """Normalize mapping-like stage results."""
    if isinstance(result, StageResult):
        if name and not result.name:
            result.name = name
        return result
    if isinstance(result, Mapping):
        return StageResult(result, name=name)
    raise TypeError(f"Stage results must be mappings, got {type(result)!r}")
