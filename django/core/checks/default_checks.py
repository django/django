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
    return _check_test_runner(**kwargs) + _check_boolean_field_default_value(**kwargs)


def _check_test_runner(**kwargs):
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


def _check_boolean_field_default_value():
    """
    Checks if there are any BooleanFields without a default value, &
    warns the user that the default has changed from False to Null.
    """

    from django.db import models

    invalid_fields = [field
        for cls in models.get_models()
        for field in cls._meta.local_fields
        if isinstance(field, models.BooleanField) and not field.has_default()]

    return [
        Warning(
            'The field has not set a default value. In Django 1.6 '
                'the default value of BooleanField was changed from '
                'False to Null when Field.default is not defined. '
                'See https://docs.djangoproject.com/en/1.6/ref/models/fields/#booleanfield '
                'for more information.',
            hint=None,
            obj=field,
        )
        for field in invalid_fields]
