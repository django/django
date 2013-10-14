import warnings

warnings.warn(
    "The django.contrib.gis.db.backends.util module has been renamed. "
    "Use django.contrib.gis.db.backends.utils instead.", PendingDeprecationWarning)

from django.contrib.gis.db.backends.utils import *
