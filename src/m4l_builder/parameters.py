"""First-class Max for Live parameter metadata."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Iterable, Optional


_UNSET = object()
PARAM_HIDDEN = 0
PARAM_VISIBLE = 1
LIVE_NATIVE_INT_MIN = 0
LIVE_NATIVE_INT_MAX = 255


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
    shortname: Optional[str] = None
    parameter_type: int = 0
    minimum: Optional[float] = None
    maximum: Optional[float] = None
    initial: Any = _UNSET
    initial_enable: Optional[bool] = None
    unitstyle: Optional[int] = None
    exponent: Optional[float] = None
    enum: Optional[list[str]] = None
    visible: int = 1
    bank: Optional[int] = None
    position: Optional[int] = None
    bank_name: Optional[str] = None
    integer_like: bool = False
    allow_wide_range: bool = False

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
            normalized = [_normalize_label(option, field_name="enum option") for option in self.enum]
            if not normalized:
                raise ValueError("enumerated parameters require at least one option")
            self.enum = normalized
        elif self.parameter_type == 2:
            raise ValueError("enumerated parameters require options")

    def copy(self, **changes: Any) -> "ParameterSpec":
        """Return a copied spec with optional overrides."""
        return replace(self, **changes)

    def with_bank(self, bank: int, position: int, bank_name: str = None) -> "ParameterSpec":
        """Return a copied spec with Push bank metadata attached."""
        return self.copy(bank=bank, position=position, bank_name=bank_name)

    def with_visibility(self, visible: int) -> "ParameterSpec":
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
        initial_enable: Optional[bool] = True,
        unitstyle: int = None,
        exponent: float = None,
        bank: int = None,
        position: int = None,
        bank_name: str = None,
        visible: int = 1,
    ) -> "ParameterSpec":
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
        initial_enable: Optional[bool] = True,
        unitstyle: int = None,
        bank: int = None,
        position: int = None,
        bank_name: str = None,
        visible: int = PARAM_VISIBLE,
        allow_wide_range: bool = False,
    ) -> "ParameterSpec":
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
        initial_enable: Optional[bool] = None,
        bank: int = None,
        position: int = None,
        bank_name: str = None,
        visible: int = 1,
    ) -> "ParameterSpec":
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
    ) -> "ParameterSpec":
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
            bank=bank,
            position=position,
            bank_name=bank_name,
            integer_like=False,
            allow_wide_range=False,
        )


def extract_parameter_spec(box_dict: dict) -> Optional[ParameterSpec]:
    """Return a ParameterSpec when a box stores Max parameter metadata."""
    box = box_dict.get("box", {})
    valueof = box.get("saved_attribute_attributes", {}).get("valueof")
    if not valueof:
        return None
    return ParameterSpec.from_valueof_dict(valueof)
