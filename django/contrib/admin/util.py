import warnings

from django.utils.deprecation import RemovedInDjango19Warning

warnings.warn(
    "The django.contrib.admin.util module has been renamed. "
    "Use django.contrib.admin.utils instead.", RemovedInDjango19Warning)

from django.contrib.admin.utils import *  # NOQA isort:skip
