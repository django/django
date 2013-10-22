import warnings

warnings.warn(
    "The django.db.backends.util module has been renamed. "
    "Use django.db.backends.utils instead.", PendingDeprecationWarning)

from django.db.backends.utils import *  # NOQA
