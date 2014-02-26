"""XViewMiddleware has been moved to django.contrib.admindocs.middleware."""

import warnings

from django.utils.deprecation import RemovedInDjango18Warning

warnings.warn(__doc__, RemovedInDjango18Warning, stacklevel=2)

from django.contrib.admindocs.middleware import XViewMiddleware  # NOQA
