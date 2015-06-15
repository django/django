import warnings

from django.utils.deprecation import RemovedInDjango110Warning


default_app_config = 'django.contrib.webdesign.apps.WebDesignConfig'

warnings.warn(
    "django.contrib.webdesign will be removed in Django 1.10. The "
    "{% lorem %} tag is now included in the built-in tags.",
    RemovedInDjango110Warning
)
