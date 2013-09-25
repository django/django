from __future__ import unicode_literals
import warnings

from django.core.checks.compatibility import django_1_6_0


COMPAT_CHECKS = [
    # Add new modules at the top, so we keep things in descending order.
    # After two-three minor releases, old versions should get dropped.
    django_1_6_0,
]


def check_compatibility():
    """
    Runs through compatibility checks to warn the user with an existing install
    about changes in an up-to-date Django.

    Modules should be located in ``django.core.compat_checks`` (typically one
    per release of Django) & must have a ``run_checks`` function that runs
    all the checks.

    Returns a list of informational messages about incompatibilities.
    """
    messages = []

    for check_module in COMPAT_CHECKS:
        check = getattr(check_module, 'run_checks', None)

        if check is None:
            warnings.warn(
                "The '%s' module lacks a " % check_module.__name__ +
                "'run_checks' method, which is needed to verify compatibility."
            )
            continue

        messages.extend(check())

    return messages
