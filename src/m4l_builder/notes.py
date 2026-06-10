"""Pure-Python builders for Live 12 MIDI Tool notes dictionaries.

A MIDI Generator (and Transformation) exchanges notes with Live as a
dictionary shaped like ``{"notes": [{"pitch": ..., "start_time": ...,
"duration": ..., ...}, ...]}`` (see docs/midi_tools.md). These helpers build
that structure in Python so a device script can embed it — e.g. as a baked
``dict`` message or inside a ``v8``/``js`` script — without hand-writing JSON.

This module only constructs the documented dictionary *structure*. Wiring the
result into ``live.miditool.out`` (via Max ``dict`` objects or an embedded
script) is not handled here, and the emission mechanism itself has not been
validated inside Ableton Live.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

_REQUIRED_KEYS = ("pitch", "start_time", "duration")


@dataclass
class NoteEvent:
    """One note in a MIDI Tool notes dictionary.

    Required fields mirror Live's contract: ``pitch`` (MIDI note 0-127),
    ``start_time`` (beats from clip start), and ``duration`` (beats).
    Optional fields are omitted from the output dict while ``None``.
    """

    pitch: int
    start_time: float
    duration: float
    velocity: float | None = None
    probability: float | None = None
    velocity_deviation: float | None = None
    release_velocity: float | None = None
    mute: int | None = None

    def __post_init__(self):
        if not isinstance(self.pitch, int) or isinstance(self.pitch, bool):
            raise ValueError(f"pitch must be an int, got {self.pitch!r}")
        if not 0 <= self.pitch <= 127:
            raise ValueError(f"pitch must be in 0..127, got {self.pitch}")
        if self.start_time < 0:
            raise ValueError(f"start_time must be >= 0, got {self.start_time}")
        if self.duration <= 0:
            raise ValueError(f"duration must be > 0, got {self.duration}")
        if self.velocity is not None and not 0 <= self.velocity <= 127:
            raise ValueError(f"velocity must be in 0..127, got {self.velocity}")
        if self.probability is not None and not 0 <= self.probability <= 1:
            raise ValueError(f"probability must be in 0..1, got {self.probability}")
        if self.velocity_deviation is not None and not -127 <= self.velocity_deviation <= 127:
            raise ValueError(
                f"velocity_deviation must be in -127..127, got {self.velocity_deviation}"
            )
        if self.release_velocity is not None and not 0 <= self.release_velocity <= 127:
            raise ValueError(f"release_velocity must be in 0..127, got {self.release_velocity}")
        if self.mute is not None and self.mute not in (0, 1):
            raise ValueError(f"mute must be 0 or 1, got {self.mute}")

    def to_dict(self) -> dict:
        """Return the note as a dict, omitting unset optional fields."""
        note = {
            "pitch": self.pitch,
            "start_time": self.start_time,
            "duration": self.duration,
        }
        for key in ("velocity", "probability", "velocity_deviation", "release_velocity", "mute"):
            value = getattr(self, key)
            if value is not None:
                note[key] = value
        return note


def notes_dict(events: Iterable[NoteEvent | Mapping]) -> dict:
    """Build a ``{"notes": [...]}`` dictionary for ``live.miditool.out``.

    Accepts an iterable of ``NoteEvent`` instances and/or plain mappings.
    Mappings must carry the required ``pitch`` / ``start_time`` / ``duration``
    keys and are copied through untouched otherwise. The result serializes
    directly with ``json.dumps``.
    """
    notes = []
    for event in events:
        if isinstance(event, NoteEvent):
            notes.append(event.to_dict())
            continue
        if isinstance(event, Mapping):
            missing = [key for key in _REQUIRED_KEYS if key not in event]
            if missing:
                raise ValueError(f"note mapping missing required keys: {', '.join(missing)}")
            notes.append(dict(event))
            continue
        raise TypeError(f"expected NoteEvent or mapping, got {type(event).__name__}")
    return {"notes": notes}
