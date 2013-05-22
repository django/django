"""XViewMiddleware has been moved to django.contrib.admindocs.middleware."""

import warnings
warnings.warn(__doc__, PendingDeprecationWarning, stacklevel=2)

from django.contrib.admindocs.middleware import XViewMiddleware
