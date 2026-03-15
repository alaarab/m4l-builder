"""Structured builder namespace for authoring Max for Live devices."""

from . import core, dsp, live, recipes, ui
from .core import *  # noqa: F401,F403
from .dsp import *  # noqa: F401,F403
from .live import *  # noqa: F401,F403
from .recipes import *  # noqa: F401,F403
from .ui import *  # noqa: F401,F403

__all__ = [
    "core",
    "ui",
    "dsp",
    "live",
    "recipes",
    *core.__all__,
    *ui.__all__,
    *dsp.__all__,
    *live.__all__,
    *recipes.__all__,
]
