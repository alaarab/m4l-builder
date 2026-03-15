"""Reusable module abstraction for graph blocks and DSP helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Mapping

from .assets import Asset
from .graph import BoxRef, InletRef, OutletRef
from .stages import StageResult, stage_result


@dataclass
class ModuleSpec:
    """Pre-mount description of a reusable graph module."""

    boxes: list
    lines: list
    name: str = "module"
    mapping: dict = field(default_factory=dict)
    ports: dict = field(default_factory=dict)
    params: dict = field(default_factory=dict)
    assets: list = field(default_factory=list)
    validators: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


def _resolve_port(graph, port):
    if isinstance(port, BoxRef):
        return graph.box(port.id)
    if isinstance(port, OutletRef):
        return graph.box(port.box_id).outlet(port.outlet)
    if isinstance(port, InletRef):
        return graph.box(port.box_id).inlet(port.inlet)
    if isinstance(port, str):
        return graph.box(port)
    return port


def mount_module(graph, spec: ModuleSpec) -> StageResult:
    """Mount a module onto a graph and return a stage-style result."""
    graph.add_dsp(spec.boxes, spec.lines)
    for asset in spec.assets:
        if isinstance(asset, Asset):
            graph.register_asset(
                asset.filename,
                asset.content,
                asset_type=asset.asset_type,
                category=asset.category,
                encoding=asset.encoding,
            )
        elif isinstance(asset, Mapping):
            graph.register_asset(
                asset["filename"],
                asset["content"],
                asset_type=asset.get("asset_type", asset.get("type", "TEXT")),
                category=asset.get("category", "support"),
                encoding=asset.get("encoding", "utf-8"),
            )
        else:
            raise TypeError(f"Unsupported asset spec: {asset!r}")
    resolved_mapping = {
        key: _resolve_port(graph, value) if isinstance(value, (BoxRef, InletRef, OutletRef)) else value
        for key, value in dict(spec.mapping).items()
    }
    resolved_ports = {key: _resolve_port(graph, value) for key, value in dict(spec.ports).items()}
    resolved_params = {
        key: (graph.parameter(value) if not hasattr(value, "name") else value)
        for key, value in dict(spec.params).items()
    }
    return stage_result(
        resolved_mapping,
        name=spec.name,
        params=resolved_params,
        ports=resolved_ports,
        assets=[asset.filename if isinstance(asset, Asset) else asset["filename"] for asset in spec.assets],
        validators=spec.validators,
        metadata=spec.metadata,
    )


def module_from_block(
    block_fn: Callable[..., tuple],
    *,
    name: str = None,
    mapping_factory: Callable[..., Mapping[str, Any]] = None,
    port_factory: Callable[..., Mapping[str, Any]] = None,
    param_factory: Callable[..., Mapping[str, Any]] = None,
    asset_factory: Callable[..., Iterable[Any]] = None,
    validator_factory: Callable[..., Iterable[Any]] = None,
    metadata_factory: Callable[..., Mapping[str, Any]] = None,
) -> Callable[..., ModuleSpec]:
    """Lift a legacy `(boxes, lines)` helper into the module abstraction."""

    def factory(*args, **kwargs) -> ModuleSpec:
        boxes, lines = block_fn(*args, **kwargs)
        return ModuleSpec(
            boxes=boxes,
            lines=lines,
            name=name or getattr(block_fn, "__name__", "module"),
            mapping=dict(mapping_factory(*args, **kwargs) if mapping_factory else {}),
            ports=dict(port_factory(*args, **kwargs) if port_factory else {}),
            params=dict(param_factory(*args, **kwargs) if param_factory else {}),
            assets=list(asset_factory(*args, **kwargs) if asset_factory else []),
            validators=list(validator_factory(*args, **kwargs) if validator_factory else []),
            metadata=dict(metadata_factory(*args, **kwargs) if metadata_factory else {}),
        )

    factory.__name__ = getattr(block_fn, "__name__", "module")
    return factory
