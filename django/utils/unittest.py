from __future__ import absolute_import

import warnings

warnings.warn("django.utils.unittest will be removed in Django 1.9.",
    PendingDeprecationWarning, stacklevel=2)

try:
    from unittest2 import *
except ImportError:
    from unittest import *
