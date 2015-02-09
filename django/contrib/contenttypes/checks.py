# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.apps import apps
from django.utils import six


def check_generic_foreign_keys(**kwargs):
    from .fields import GenericForeignKey

    errors = []
    fields = (obj
        for cls in apps.get_models()
        for obj in six.itervalues(vars(cls))
        if isinstance(obj, GenericForeignKey))
    for field in fields:
        errors.extend(field.check())
    return errors
