import warnings

warnings.warn("django.utils.unittest will be removed in Django 1.9.",
    PendingDeprecationWarning)

try:
    from unittest2 import *
except ImportError:
    from unittest import *
