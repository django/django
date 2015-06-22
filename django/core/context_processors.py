import warnings

from django.template.context_processors import *  # NOQA
from django.utils.deprecation import RemovedInDjango110Warning

warnings.warn(
    "django.core.context_processors is deprecated in favor of "
    "django.template.context_processors.",
    RemovedInDjango110Warning, stacklevel=2)
