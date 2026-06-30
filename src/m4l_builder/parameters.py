"""First-class Max for Live parameter metadata."""

from __future__ import annotations

from collections.abc import Iterable
from contextlib import contextmanager
from dataclasses import dataclass, replace
from typing import Any

_UNSET = object()

# When reconstructing a ParameterSpec from a REAL device's valueof (cloning a
# shipping .amxd), Live's data legitimately violates our stricter AUTHORING rules
# (e.g. an enum initial index beyond the option count, an empty enum option). This
# flag relaxes those opinionated raises so a faithful clone preserves the original
# values verbatim. Authoring (the default) stays strict. NOT a dataclass field — a
# field would ripple through the reverse-codegen subsystem (the A0 blocker).
_STRICT_VALIDATION = True


@contextmanager
def tolerant_reconstruction():
    """Within this context, ParameterSpec skips opinionated authoring validation
    (for faithfully cloning real devices). Restores the prior setting on exit."""
    global _STRICT_VALIDATION
    prev = _STRICT_VALIDATION
    _STRICT_VALIDATION = False
    try:
        yield
    finally:
        _STRICT_VALIDATION = prev
PARAM_HIDDEN = 0
PARAM_VISIBLE = 1
LIVE_NATIVE_INT_MIN = 0
LIVE_NATIVE_INT_MAX = 255

# Max for Live "Parameter Visibility" (the `parameter_invisible` valueof attr).
# This is DISTINCT from `visible` above, which is Push parameter-bank membership.
#   AUTOMATED_AND_STORED (0): default — stored in the set/presets AND exposed to
#       Live's automation + MIDI/key mapping. A parameter driven continuously by
#       patch logic (a metro-fed probe dial, a meter snapshot) at this setting
#       floods Live's undo history with a constant stream of the same action —
#       Ableton's own production guidelines call this out as making undo unusable.
#   STORED_ONLY (1): value is saved with the set/preset but is NOT shown to
#       automation. Good for state you want recalled but not automatable.
#   HIDDEN (2): neither stored nor automatable — the right setting for diagnostic
#       / DSP-probe parameters that exist only to be read back via the Live API
#       (get_device_parameters still enumerates them; they just leave no undo or
#       automation footprint).
PARAM_VIS_AUTOMATED_AND_STORED = 0
PARAM_VIS_STORED_ONLY = 1
PARAM_VIS_HIDDEN = 2


def _normalize_label(value: Any, *, field_name: str) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError(f"parameter {field_name} must be a non-empty string")
    return text


def _is_int_like(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return True
    return isinstance(value, float) and value.is_integer()


@dataclass
class ParameterSpec:
    """Semantic description of a Max for Live parameter."""

    name: str
    shortname: str | None = None
    parameter_type: int = 0
    minimum: float | None = None
    maximum: float | None = None
    initial: Any = _UNSET
    initial_enable: bool | None = None
    unitstyle: int | None = None
    exponent: float | None = None
    enum: list[str] | None = None
    visible: int = 1
    invisible: int | None = None
    bank: int | None = None
    position: int | None = None
    bank_name: str | None = None
    integer_like: bool = False
    allow_wide_range: bool = False
    annotation_name: str | None = None  # parameter_annotation_name (hover-help title)
    info: str | None = None             # parameter_info (hover-help body)
    units: str | None = None            # parameter_units printf fmt (with unitstyle=9 Custom)
    steps: int | None = None            # parameter_steps: quantize the range into N discrete steps

    def __post_init__(self) -> None:
        self.name = _normalize_label(self.name, field_name="name")
        if self.shortname is not None:
            shortname = str(self.shortname).strip()
            self.shortname = shortname or None
        if isinstance(self.visible, bool):
            self.visible = PARAM_VISIBLE if self.visible else PARAM_HIDDEN
        else:
            self.visible = int(self.visible)
        if self.visible < 0:
            raise ValueError("parameter visible must be >= 0")
        if self.invisible is not None:
            self.invisible = int(self.invisible)
            if self.invisible not in (0, 1, 2):
                raise ValueError(
                    "parameter invisible must be 0 (Automated and Stored), "
                    "1 (Stored Only), or 2 (Hidden)"
                )
        if self.minimum is not None and self.maximum is not None and self.minimum > self.maximum:
            raise ValueError("parameter minimum cannot exceed maximum")
        if self.bank is not None and self.bank < 0:
            raise ValueError("parameter bank must be >= 0")
        if self.position is not None and self.position < 0:
            raise ValueError("parameter position must be >= 0")
        if self.bank_name is not None:
            bank_name = str(self.bank_name).strip()
            self.bank_name = bank_name or None
        if self.enum is not None:
            if _STRICT_VALIDATION:
                normalized = [_normalize_label(option, field_name="enum option") for option in self.enum]
                if not normalized:
                    raise ValueError("enumerated parameters require at least one option")
                # Duplicate options in a real MENU (3+ choices) are a typo bug; a
                # 2-option enum with identical labels is the legitimate toggle pattern
                # (a button that keeps one label and only changes its highlight).
                if len(normalized) > 2 and len(set(normalized)) != len(normalized):
                    raise ValueError(f"enumerated parameter {self.name!r} has duplicate options: {normalized}")
                self.enum = normalized
            else:
                # Tolerant clone: keep options verbatim (Live allows empty/dupes).
                self.enum = [str(option) for option in self.enum]
        elif self.parameter_type == 2 and _STRICT_VALIDATION:
            raise ValueError("enumerated parameters require options")
        # Exponent drives Max's log/exp fader scaling; <= 0 silently breaks it.
        if self.exponent is not None and self.exponent <= 0:
            raise ValueError(f"parameter {self.name!r} exponent must be > 0, got {self.exponent}")
        # An out-of-range initial is silently clamped (continuous) or mis-indexed
        # (enumerated) at load — turn it into a build error. allow_wide_range opts
        # out, matching the existing integer-range escape hatch.
        if (self.initial is not _UNSET and self.initial is not None
                and not self.allow_wide_range and _STRICT_VALIDATION):
            inits = self.initial if isinstance(self.initial, (list, tuple)) else [self.initial]
            for v in inits:
                if not isinstance(v, (int, float)) or isinstance(v, bool):
                    continue
                if self.enum is not None:
                    if _is_int_like(v) and not (0 <= int(v) <= len(self.enum) - 1):
                        raise ValueError(
                            f"parameter {self.name!r} enumerated initial index {v} "
                            f"out of range 0..{len(self.enum) - 1}"
                        )
                else:
                    if self.minimum is not None and v < self.minimum:
                        raise ValueError(
                            f"parameter {self.name!r} initial {v} below minimum {self.minimum}")
                    if self.maximum is not None and v > self.maximum:
                        raise ValueError(
                            f"parameter {self.name!r} initial {v} above maximum {self.maximum}")

    def copy(self, **changes: Any) -> ParameterSpec:
        """Return a copied spec with optional overrides."""
        return replace(self, **changes)

    def with_bank(self, bank: int, position: int, bank_name: str = None) -> ParameterSpec:
        """Return a copied spec with Push bank metadata attached."""
        return self.copy(bank=bank, position=position, bank_name=bank_name)

    def with_visibility(self, visible: int) -> ParameterSpec:
        """Return a copied spec with updated parameter-bank visibility."""
        return self.copy(visible=visible)

    def to_valueof_dict(self) -> dict:
        """Return the Max `saved_attribute_attributes.valueof` payload."""
        valueof = {
            "parameter_longname": self.name,
            "parameter_shortname": self.shortname or self.name,
            "parameter_type": self.parameter_type,
        }
        if self.minimum is not None:
            valueof["parameter_mmin"] = self.minimum
        if self.maximum is not None:
            valueof["parameter_mmax"] = self.maximum
        if self.initial_enable is not None:
            valueof["parameter_initial_enable"] = int(bool(self.initial_enable))
        if self.initial is not _UNSET:
            initial = self.initial
            if isinstance(initial, tuple):
                initial = list(initial)
            elif not isinstance(initial, list):
                initial = [initial]
            valueof["parameter_initial"] = initial
        if self.unitstyle is not None:
            valueof["parameter_unitstyle"] = self.unitstyle
        if self.exponent is not None:
            valueof["parameter_exponent"] = self.exponent
        if self.enum is not None:
            valueof["parameter_enum"] = list(self.enum)
        if self.invisible is not None:
            valueof["parameter_invisible"] = self.invisible
        if self.annotation_name:
            valueof["parameter_annotation_name"] = self.annotation_name
        if self.info:
            valueof["parameter_info"] = self.info
        if self.units:
            valueof["parameter_units"] = self.units
        if self.steps is not None:
            valueof["parameter_steps"] = self.steps
        return valueof

    def to_saved_attributes(self) -> dict:
        """Return the `saved_attribute_attributes` wrapper payload."""
        return {"valueof": self.to_valueof_dict()}

    @classmethod
    def continuous(
        cls,
        name: str,
        *,
        shortname: str = None,
        minimum: float = None,
        maximum: float = None,
        initial: Any = _UNSET,
        initial_enable: bool | None = True,
        unitstyle: int = None,
        exponent: float = None,
        bank: int = None,
        position: int = None,
        bank_name: str = None,
        visible: int = 1,
        annotation_name: str = None,
        info: str = None,
        units: str = None,
        steps: int = None,
    ) -> ParameterSpec:
        """Build a continuous parameter spec."""
        return cls(
            name=name,
            shortname=shortname,
            parameter_type=0,
            minimum=minimum,
            maximum=maximum,
            initial=initial,
            initial_enable=initial_enable,
            unitstyle=unitstyle,
            exponent=exponent,
            bank=bank,
            position=position,
            bank_name=bank_name,
            visible=visible,
            integer_like=False,
            allow_wide_range=False,
            annotation_name=annotation_name,
            info=info,
            units=units,
            steps=steps,
        )

    @classmethod
    def integer(
        cls,
        name: str,
        *,
        shortname: str = None,
        minimum: int = LIVE_NATIVE_INT_MIN,
        maximum: int = LIVE_NATIVE_INT_MAX,
        initial: Any = _UNSET,
        initial_enable: bool | None = True,
        unitstyle: int = None,
        bank: int = None,
        position: int = None,
        bank_name: str = None,
        visible: int = PARAM_VISIBLE,
        allow_wide_range: bool = False,
    ) -> ParameterSpec:
        """Build an integer-like parameter spec with native-range guardrails."""
        integer_values = [minimum, maximum]
        if initial is not _UNSET:
            integer_values.append(initial)
        if not all(_is_int_like(value) for value in integer_values):
            raise ValueError("integer parameters require integer-like minimum, maximum, and initial values")
        if not allow_wide_range and (
            minimum < LIVE_NATIVE_INT_MIN or maximum > LIVE_NATIVE_INT_MAX
        ):
            raise ValueError(
                f"integer parameters beyond {LIVE_NATIVE_INT_MIN}-{LIVE_NATIVE_INT_MAX} "
                "require allow_wide_range=True"
            )
        return cls.continuous(
            name=name,
            shortname=shortname,
            minimum=float(minimum),
            maximum=float(maximum),
            initial=initial,
            initial_enable=initial_enable,
            unitstyle=unitstyle,
            bank=bank,
            position=position,
            bank_name=bank_name,
            visible=visible,
        ).copy(integer_like=True, allow_wide_range=allow_wide_range)

    @classmethod
    def enumerated(
        cls,
        name: str,
        options: Iterable[str],
        *,
        shortname: str = None,
        minimum: float = None,
        maximum: float = None,
        initial: Any = _UNSET,
        initial_enable: bool | None = None,
        bank: int = None,
        position: int = None,
        bank_name: str = None,
        visible: int = 1,
    ) -> ParameterSpec:
        """Build an enum parameter spec."""
        option_list = list(options)
        return cls(
            name=name,
            shortname=shortname,
            parameter_type=2,
            minimum=0 if minimum is None else minimum,
            maximum=max(len(option_list) - 1, 0) if maximum is None else maximum,
            initial=initial,
            initial_enable=initial_enable,
            enum=option_list,
            bank=bank,
            position=position,
            bank_name=bank_name,
            visible=visible,
        )

    @classmethod
    def from_valueof_dict(
        cls, valueof: dict, *, bank: int = None, position: int = None, bank_name: str = None
    ) -> ParameterSpec:
        """Rebuild a spec from a Max `valueof` dict."""
        initial = valueof.get("parameter_initial", _UNSET)
        if isinstance(initial, list) and len(initial) == 1:
            initial = initial[0]
        return cls(
            name=valueof.get("parameter_longname") or valueof.get("parameter_shortname") or "",
            shortname=valueof.get("parameter_shortname"),
            parameter_type=valueof.get("parameter_type", 0),
            minimum=valueof.get("parameter_mmin"),
            maximum=valueof.get("parameter_mmax"),
            initial=initial,
            initial_enable=(
                None
                if "parameter_initial_enable" not in valueof
                else bool(valueof.get("parameter_initial_enable"))
            ),
            unitstyle=valueof.get("parameter_unitstyle"),
            exponent=valueof.get("parameter_exponent"),
            enum=list(valueof["parameter_enum"]) if "parameter_enum" in valueof else None,
            invisible=valueof.get("parameter_invisible"),
            bank=bank,
            position=position,
            bank_name=bank_name,
            integer_like=False,
            allow_wide_range=False,
            annotation_name=valueof.get("parameter_annotation_name"),
            info=valueof.get("parameter_info"),
            units=valueof.get("parameter_units"),
            steps=valueof.get("parameter_steps"),
        )


def extract_parameter_spec(box_dict: dict) -> ParameterSpec | None:
    """Return a ParameterSpec when a box stores Max parameter metadata."""
    box = box_dict.get("box", {})
    valueof = box.get("saved_attribute_attributes", {}).get("valueof")
    if not valueof:
        return None
    return ParameterSpec.from_valueof_dict(valueof)
