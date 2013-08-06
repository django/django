# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from .generic import GenericForeignKey


# This check is registered in __init__.py file.
def check_generic_foreign_keys(**kwargs):
    from django.db import models

    errors = []
    fields = (obj
        for cls in models.get_models(include_swapped=True)
        for obj in vars(cls).itervalues()
        if isinstance(obj, GenericForeignKey))
    for field in fields:
        errors.extend(field.check())
    return errors
