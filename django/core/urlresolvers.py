import warnings

from django.utils.deprecation import RemovedInDjango20Warning


warnings.warn(
    "django.core.urlresolvers is deprecated and will be removed"
    "in Django 2.0. Use django.core.urls instead.",
    RemovedInDjango20Warning, stacklevel=2
)


from django.core.urls import *  # NOQA
