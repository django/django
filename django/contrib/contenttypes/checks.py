# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from .generic import GenericForeignKey, GenericRelation


# This check is registered in __init__.py file.
def check_generic_foreign_keys(**kwargs):
    from django.db import models

    errors = []
    fields = (obj
        for cls in models.get_models()
        for obj in vars(cls).itervalues()
        if isinstance(obj, GenericForeignKey))
    for field in fields:
        errors.extend(field.check())
    return errors

def check_generic_relationships(**kwargs):
    from django.db import models

    errors = []
    fields = (obj
        for cls in models.get_models()
        for obj in vars(cls).itervalues()
        if isinstance(obj, GenericRelation))
    for field in fields:
        errors.extend(field.check())
    return errors
