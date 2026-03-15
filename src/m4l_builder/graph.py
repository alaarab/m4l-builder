"""Shared graph primitives and typed connection handles."""

from __future__ import annotations

from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
import re
from typing import Any, Optional

from .assets import Asset
from .objects import newobj, patchline
from .parameters import ParameterSpec, extract_parameter_spec


class BoxRef(str):
    """Typed object handle that still behaves like a string ID."""

    def __new__(cls, box_id: str, graph=None):
        obj = str.__new__(cls, box_id)
        obj.graph = graph
        return obj

    @property
    def id(self) -> str:
        """Return the raw box ID."""
        return str(self)

    def inlet(self, index: int = 0) -> "InletRef":
        """Return a typed inlet reference."""
        return InletRef(str(self), index, graph=getattr(self, "graph", None))

    def outlet(self, index: int = 0) -> "OutletRef":
        """Return a typed outlet reference."""
        return OutletRef(str(self), index, graph=getattr(self, "graph", None))


@dataclass(frozen=True)
class OutletRef:
    """Typed outlet reference."""

    box_id: str
    outlet: int = 0
    graph: Any = field(default=None, compare=False, repr=False)


@dataclass(frozen=True)
class InletRef:
    """Typed inlet reference."""

    box_id: str
    inlet: int = 0
    graph: Any = field(default=None, compare=False, repr=False)


class GraphContainer:
    """Shared mutable Max graph container."""

    def __init__(self):
        self.boxes = []
        self.lines = []
        self._assets = {}
        self._parameter_specs = {}
        self._box_parameters = {}
        self._id_counters = defaultdict(int)
        self._name_scope_stack = []
        self._reserved_ids = set()

    def _make_box_ref(self, box_id: str) -> BoxRef:
        return BoxRef(box_id, self)

    def scoped_name(self, base: str) -> str:
        """Return a scope-qualified name without reserving it."""
        parts = [self._sanitize_id_part(part) for part in self._name_scope_stack if part]
        if base:
            parts.append(self._sanitize_id_part(base))
        if not parts:
            parts.append("obj")
        return "_".join(part for part in parts if part) or "obj"

    @contextmanager
    def name_scope(self, prefix: str):
        """Temporarily prepend a naming scope for generated IDs."""
        token = self._sanitize_id_part(prefix)
        if token:
            self._name_scope_stack.append(token)
        try:
            yield self
        finally:
            if token:
                self._name_scope_stack.pop()

    def unique_id(self, base: str = "obj") -> str:
        """Return a graph-unique ID using the current naming scope."""
        stem = self.scoped_name(base)
        used = {box["box"]["id"] for box in self.boxes if "box" in box}
        used.update(self._reserved_ids)

        if stem not in used:
            self._reserved_ids.add(stem)
            self._id_counters[stem] = max(self._id_counters[stem], 1)
            return stem

        counter = max(self._id_counters[stem], 1)
        while True:
            counter += 1
            candidate = f"{stem}_{counter}"
            if candidate not in used:
                self._id_counters[stem] = counter
                self._reserved_ids.add(candidate)
                return candidate

    def register_asset(
        self,
        filename: str,
        content,
        *,
        asset_type: str = "TEXT",
        category: str = "support",
        encoding: str = "utf-8",
    ) -> Asset:
        """Register a sidecar asset emitted alongside a device build."""
        stored = Asset(
            filename=filename,
            content=content,
            asset_type=asset_type,
            category=category,
            encoding=encoding,
        )
        self._assets[filename] = stored
        return stored

    def asset(self, filename: str) -> Optional[Asset]:
        """Return a registered asset by filename."""
        return self._assets.get(filename)

    def assets(self) -> tuple[Asset, ...]:
        """Return registered assets."""
        return tuple(self._assets.values())

    def register_parameter(self, spec: ParameterSpec, *, box_id: str = None) -> ParameterSpec:
        """Register a first-class parameter spec on this graph."""
        stored = spec.copy()
        self._parameter_specs[stored.name] = stored
        if box_id is not None:
            self._box_parameters[box_id] = stored.name
        return stored

    def parameter(self, name_or_ref) -> Optional[ParameterSpec]:
        """Return a registered parameter spec by name or box handle."""
        key = self._resolve_parameter_name(name_or_ref)
        if key is None:
            return None
        return self._parameter_specs.get(key)

    def parameters(self) -> tuple:
        """Return registered parameter specs."""
        return tuple(self._parameter_specs.values())

    def box(self, box_id: str) -> BoxRef:
        """Return a typed box reference for an existing ID."""
        return self._make_box_ref(str(box_id))

    def _resolve_parameter_name(self, name_or_ref) -> Optional[str]:
        if isinstance(name_or_ref, ParameterSpec):
            return name_or_ref.name
        if isinstance(name_or_ref, BoxRef):
            return self._box_parameters.get(str(name_or_ref), str(name_or_ref))
        return None if name_or_ref is None else str(name_or_ref)

    def add_box(self, box_dict: dict) -> BoxRef:
        """Add a raw box dict and return a typed handle."""
        self.boxes.append(box_dict)
        box_id = box_dict["box"]["id"]
        self._reserved_ids.add(box_id)
        spec = extract_parameter_spec(box_dict)
        if spec is not None:
            self.register_parameter(spec, box_id=box_id)
        return self._make_box_ref(box_id)

    def add_line(self, source_id, source_outlet=0, dest_id=None, dest_inlet=0, **kwargs):
        """Add a patchline between raw IDs or typed endpoint refs."""
        if isinstance(source_id, OutletRef):
            if dest_id is None:
                dest_id = source_outlet
            source_outlet = source_id.outlet
            source_id = source_id.box_id

        if isinstance(dest_id, InletRef):
            dest_inlet = dest_id.inlet
            dest_id = dest_id.box_id

        if dest_id is None:
            raise TypeError("dest_id is required unless using add_line(OutletRef, InletRef)")

        source_id = str(source_id)
        dest_id = str(dest_id)
        self.lines.append(patchline(source_id, source_outlet, dest_id, dest_inlet, **kwargs))

    def connect(self, source, dest, **kwargs):
        """Connect typed endpoints or box handles without manual index plumbing."""
        if isinstance(source, OutletRef) and isinstance(dest, InletRef):
            self.add_line(source, dest, **kwargs)
            return
        if isinstance(source, BoxRef):
            source = source.outlet(0)
        if isinstance(dest, BoxRef):
            dest = dest.inlet(0)
        self.add_line(source, dest, **kwargs)

    def add_dsp(self, boxes: list, lines: list):
        """Add all boxes and lines from a DSP block tuple to this graph."""
        for box in boxes:
            self.add_box(box)
        for line in lines:
            self.lines.append(line)

    def add_newobj(self, id: str = None, text: str = "", *, numinlets: int, numoutlets: int, **kwargs) -> BoxRef:
        """Add a raw Max object and return its typed handle."""
        if id is None:
            base = text or "obj"
            id = self.unique_id(base)
        return self.add_box(newobj(id, text, numinlets=numinlets, numoutlets=numoutlets, **kwargs))

    def wire_chain(self, obj_ids: list, outlet: int = 0, inlet: int = 0):
        """Connect objects end-to-end, each output feeding the next input."""
        for i in range(len(obj_ids) - 1):
            self.add_line(obj_ids[i], outlet, obj_ids[i + 1], inlet)

    def lint(self, *, device_type: str = None):
        """Return structured validation issues for this graph."""
        from .validation import lint_graph

        effective_device_type = device_type or getattr(self, "device_type", None)
        return lint_graph(self.boxes, self.lines, device_type=effective_device_type)

    def validate(self) -> list[str]:
        """Return compatibility warning strings for this graph."""
        return [issue.message for issue in self.lint()]

    def add_stage(self, stage, *args, **kwargs):
        """Mount a stage callable or Stage instance on this graph."""
        from .modules import ModuleSpec, mount_module
        from .stages import Stage, coerce_stage_result

        if isinstance(stage, Stage):
            result = stage.build(self, *args, **kwargs)
            name = getattr(stage, "name", stage.__class__.__name__)
        else:
            result = stage(self, *args, **kwargs)
            name = getattr(stage, "__name__", stage.__class__.__name__)
        if isinstance(result, ModuleSpec):
            return mount_module(self, result)
        if isinstance(result, tuple) and len(result) == 2:
            return mount_module(self, ModuleSpec(boxes=result[0], lines=result[1], name=name))
        return coerce_stage_result(result, name=name)

    def add_module(self, module, *args, **kwargs):
        """Mount a module spec or legacy DSP block on this graph."""
        from .modules import ModuleSpec, mount_module

        spec = module(*args, **kwargs) if callable(module) and not isinstance(module, ModuleSpec) else module
        if isinstance(spec, ModuleSpec):
            return mount_module(self, spec)
        if isinstance(spec, tuple) and len(spec) == 2:
            name = getattr(module, "__name__", getattr(spec, "name", "module"))
            spec = ModuleSpec(boxes=spec[0], lines=spec[1], name=name)
            return mount_module(self, spec)
        raise TypeError(f"Modules must resolve to ModuleSpec or (boxes, lines), got {type(spec)!r}")

    @staticmethod
    def _sanitize_id_part(value: str) -> str:
        value = re.sub(r"[^0-9A-Za-z_]+", "_", str(value or "")).strip("_")
        return value or "obj"
