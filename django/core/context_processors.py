import warnings

from django.template.context_processors import *  # NOQA
from django.utils.deprecation import RemovedInDjango20Warning

warnings.warn(
    "django.core.context_processors is deprecated in favor of "
    "django.template.context_processors.",
    RemovedInDjango20Warning, stacklevel=2)
