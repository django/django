from __future__ import absolute_import

import warnings

from freedom.utils.deprecation import RemovedInFreedom19Warning

warnings.warn("freedom.utils.unittest will be removed in Freedom 1.9.",
    RemovedInFreedom19Warning, stacklevel=2)

try:
    from unittest2 import *
except ImportError:
    from unittest import *
