import warnings

from django.urls import *  # NOQA
from django.utils.deprecation import RemovedInDjango20Warning

warnings.warn(
    "django.core.urlresolvers is deprecated and will be removed"
    "in Django 2.0. Use django.urls instead.",
    RemovedInDjango20Warning, stacklevel=2
)
