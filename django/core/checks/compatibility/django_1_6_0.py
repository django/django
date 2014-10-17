# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

from django.apps import apps

from .. import Warning, register, Tags


@register(Tags.compatibility)
def check_1_6_compatibility(**kwargs):
    errors = []
    errors.extend(_check_boolean_field_default_value(**kwargs))
    return errors


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
            "BooleanField does not have a default value.",
            hint=("Django 1.6 changed the default value of BooleanField from False to None. "
                  "See https://docs.djangoproject.com/en/1.6/ref/models/fields/#booleanfield "
                  "for more information."),
            obj=field,
            id='1_6.W002',
        )
        for field in problem_fields
    ]
