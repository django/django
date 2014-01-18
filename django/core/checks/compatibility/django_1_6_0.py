# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

from django.apps import apps

from .. import Warning, register


@register('compatibility')
def check_1_6_compatibility(**kwargs):
    errors = []
    errors.extend(_check_test_runner(**kwargs))
    errors.extend(_check_boolean_field_default_value(**kwargs))
    return errors


def _check_test_runner(app_configs=None, **kwargs):
    """
    Checks if the user has *not* overridden the ``TEST_RUNNER`` setting &
    warns them about the default behavior changes.

    If the user has overridden that setting, we presume they know what they're
    doing & avoid generating a message.
    """
    from django.conf import settings
    new_default = 'django.test.runner.DiscoverRunner'
    test_runner_setting = getattr(settings, 'TEST_RUNNER', new_default)

    if test_runner_setting == new_default and not settings.is_overridden("TEST_RUNNER"):
        return [
            Warning(
                "Django 1.6 introduced a new default test runner ('%s'). "
                    "You should ensure your tests are all running & behaving as expected." % new_default,
                hint="See https://docs.djangoproject.com/en/dev/releases/1.6/#discovery-of-tests-in-any-test-module "
                    "for more information.",
                obj=None,
                id='1_6.W001',
            )
        ]
    else:
        return []


def _check_boolean_field_default_value(app_configs=None, **kwargs):
    """
    Checks if there are any BooleanFields without a default value, &
    warns the user that the default has changed from False to None.
    """
    from django.db import models

    problem_fields = [
        field
        for model in apps.get_models(**kwargs)
        if app_configs is None or model._meta.app_config in app_configs
        for field in model._meta.local_fields
        if isinstance(field, models.BooleanField) and not field.has_default()
    ]

    return [
        Warning(
            "BooleanField does not have a default value. "
                "Django 1.6 changed the default value of BooleanField from False to None",
            hint="See https://docs.djangoproject.com/en/1.6/ref/models/fields/#booleanfield "
                "for more information.",
            obj=field,
            id='1_6.W002',
        )
        for field in problem_fields
    ]
