import warnings

from django.utils.deprecation import RemovedInDjango20Warning

default_app_config = 'django.contrib.webdesign.apps.WebDesignConfig'

warnings.warn(
    "django.contrib.webdesign will be removed in Django 2.0. The "
    "{% lorem %} tag is now included in the built-in tags.",
    RemovedInDjango20Warning
)
