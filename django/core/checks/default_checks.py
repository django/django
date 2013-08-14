# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from . import Warning

# All these checks are registered in __init__.py file.

def check_all_models(**kwargs):
    from django.db import models

    errors = []
    for cls in models.get_models(include_swapped=True):
        errors.extend(cls.check())
    return errors


def check_1_6_compatibility(**kwargs):
    """ Warn an user if the user has *not* set explicitly the ``TEST_RUNNER``
    setting. """

    from django.conf import settings

    if not hasattr(settings.RAW_SETTINGS_MODULE, 'TEST_RUNNER'):
        return [
            Warning(
                'You have not explicitly set "TEST_RUNNER". In Django 1.6, '
                'there is a new test runner ("django.test.runner.DiscoverRunner") '
                'by default. You should ensure your tests are still all '
                'running & behaving as expected. See '
                'https://docs.djangoproject.com/en/dev/releases/1.6/#discovery-of-tests-in-any-test-module '
                'for more information.',
                hint=None,
                obj=None,
            )
        ]
    else:
        return []
