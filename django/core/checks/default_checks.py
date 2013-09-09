# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from . import Warning, register


# All these checks are registered in __init__.py file.

@register('models')
def check_all_models(apps=None, **kwargs):
    from django.db import models

    errors = []
    for cls in models.get_models_from_apps(apps, include_swapped=True):
        errors.extend(cls.check())
    return errors


@register('compatibility')
def check_1_6_compatibility(**kwargs):
    return _check_test_runner(**kwargs) + _check_boolean_field_default_value(**kwargs)


def _check_test_runner(apps=None, **kwargs):
    """ Warn an user if the user has *not* set explicitly the ``TEST_RUNNER``
    setting. """

    if apps is not None:
        return []

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
                id='W047',
            )
        ]
    else:
        return []


def _check_boolean_field_default_value(apps=None, **kwargs):
    """
    Checks if there are any BooleanFields without a default value, &
    warns the user that the default has changed from False to Null.
    """

    from django.db import models

    invalid_fields = [field
        for cls in models.get_models_from_apps(apps)
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
            id='W048',
        )
        for field in invalid_fields]
