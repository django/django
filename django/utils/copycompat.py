"""
Fixes Python 2.4's failure to deepcopy unbound functions.
"""

import copy
import types
import warnings

warnings.warn("django.utils.copycompat is deprecated; use the native copy module instead",
              PendingDeprecationWarning)

# Monkeypatch copy's deepcopy registry to handle functions correctly.
if (hasattr(copy, '_deepcopy_dispatch') and types.FunctionType not in copy._deepcopy_dispatch):
    copy._deepcopy_dispatch[types.FunctionType] = copy._deepcopy_atomic

# Pose as the copy module now.
del copy, types
from copy import *
