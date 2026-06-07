"""Shared pytest configuration.

Pin ``SOURCE_DATE_EPOCH`` so generated .amxd patches carry a deterministic
creation/modification timestamp. Several round-trip tests build the same logical
device twice and compare the bytes; without a fixed epoch those two builds can
straddle a one-second boundary and disagree only on the embedded timestamp,
producing a flaky failure. ``setdefault`` keeps any value the caller already set.
"""

import os

os.environ.setdefault("SOURCE_DATE_EPOCH", "1700000000")
