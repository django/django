import sys

import numpy as np

if sys.version_info >= (3, 11):
    from typing import assert_type
else:
    from typing_extensions import assert_type

assert_type(np.ModuleDeprecationWarning(), np.ModuleDeprecationWarning)
assert_type(np.VisibleDeprecationWarning(), np.VisibleDeprecationWarning)
assert_type(np.ComplexWarning(), np.ComplexWarning)
assert_type(np.RankWarning(), np.RankWarning)
assert_type(np.TooHardError(), np.TooHardError)
assert_type(np.AxisError("test"), np.AxisError)
assert_type(np.AxisError(5, 1), np.AxisError)
