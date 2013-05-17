from __future__ import unicode_literals
import warnings

from django.utils import importlib


COMPAT_CHECKS = [
    # Add new modules here, so we keep things in descending order.
    u'django_1_6_0',
]


def check_compatibility():
    """
    Runs through compatibility checks to warn the user with an existing install
    about changes in an up-to-date Django.

    Modules should be located in ``django.core.compat_checks`` (typically one
    per release of Django) & must have a ``run_checks`` function that runs
    all the checks.

    Returns a list of information messages about incompatibilities.
    """
    messages = []

    for check_name in COMPAT_CHECKS:
        mod_name = u'django.core.compat_checks.' + check_name
        check_module = importlib.import_module(mod_name)
        check = getattr(check_module, u'run_checks', None)

        if check is None:
            warnings.warn(
                u"The '%s' module lacks a 'run_checks' method, which is " +
                u"needed to verify compatibility."
            )
            continue

        messages.extend(check())

    return messages
