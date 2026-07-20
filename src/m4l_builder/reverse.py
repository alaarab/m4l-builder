"""Split reverse-engineering facade.

The public reverse API now fans out across smaller modules:

- `reverse_snapshot`: AMXD/snapshot IO
- `reverse_patterns`: pattern, motif, and candidate extraction
- `reverse_analysis`: higher-level structural interpretation
- `reverse_codegen`: Python regeneration helpers
"""

from .reverse_analysis import *  # noqa: F401,F403
from .reverse_analysis import __all__ as _analysis_all
from .reverse_codegen import *  # noqa: F401,F403
from .reverse_codegen import __all__ as _codegen_all
from .reverse_patterns import *  # noqa: F401,F403
from .reverse_patterns import __all__ as _patterns_all
from .reverse_snapshot import *  # noqa: F401,F403
from .reverse_snapshot import __all__ as _snapshot_all

__all__ = [
    *_snapshot_all,
    *_patterns_all,
    *_analysis_all,
    *_codegen_all,
]
