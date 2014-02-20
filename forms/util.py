import warnings

warnings.warn(
    "The django.forms.util module has been renamed. "
    "Use django.forms.utils instead.", PendingDeprecationWarning)

from django.forms.utils import *  # NOQA
