import warnings

from django.utils.deprecation import RemovedInDjango19Warning

warnings.warn(
    "The django.forms.util module has been renamed. "
    "Use django.forms.utils instead.", RemovedInDjango19Warning, stacklevel=2)

from django.forms.utils import *  # NOQA isort:skip
