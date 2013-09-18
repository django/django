import warnings

warnings.warn(
    "The django.contrib.admin.util module has been renamed. "
    "Use django.contrib.admin.utils instead.", PendingDeprecationWarning)

from django.contrib.admin.utils import *
