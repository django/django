import warnings
from unittest import skipIf

from django.conf import settings
from django.utils.deprecation import RemovedInDjango20Warning


def skipIfCustomUser(test_func):
    """
    Skip a test if a custom user model is in use.
    """
    warnings.warn(
        "django.contrib.auth.tests.utils.skipIfCustomUser is deprecated.",
        RemovedInDjango20Warning, stacklevel=2)

    return skipIf(settings.AUTH_USER_MODEL != 'auth.User', 'Custom user model in use')(test_func)
