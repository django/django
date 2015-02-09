import warnings

from django.utils.deprecation import RemovedInDjango19Warning

warnings.warn(
    "The django.db.backends.util module has been renamed. "
    "Use django.db.backends.utils instead.", RemovedInDjango19Warning,
    stacklevel=2)

from django.db.backends.utils import *  # NOQA isort:skip
