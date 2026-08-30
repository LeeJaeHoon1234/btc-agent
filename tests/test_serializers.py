import math

import numpy as np

from backend.serializers import _clean


def test_clean_replaces_non_finite_values():
    result = _clean({"nan": float("nan"), "inf": np.float64(math.inf), "ok": np.float64(1.5)})
    assert result == {"nan": None, "inf": None, "ok": 1.5}
