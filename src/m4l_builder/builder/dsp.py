"""DSP building blocks."""

import inspect

from .. import dsp as _dsp

__all__ = [
    name
    for name, value in vars(_dsp).items()
    if inspect.isfunction(value) and getattr(value, "__module__", None) == _dsp.__name__
]

globals().update({name: getattr(_dsp, name) for name in __all__})
