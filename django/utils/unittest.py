from __future__ import absolute_import

import warnings

from django.utils.deprecation import RemovedInDjango19Warning

warnings.warn("django.utils.unittest will be removed in Django 1.9.",
    RemovedInDjango19Warning, stacklevel=2)

try:
    from unittest2 import *
except ImportError:
    from unittest import *
