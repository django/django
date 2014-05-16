import warnings

from django.utils.deprecation import RemovedInDjango19Warning

warnings.warn(
    "The django.contrib.gis.db.backends.util module has been renamed. "
    "Use django.contrib.gis.db.backends.utils instead.",
    RemovedInDjango19Warning, stacklevel=2)

from django.contrib.gis.db.backends.utils import *  # NOQA
