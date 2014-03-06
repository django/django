# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.utils import six
from django.apps import apps


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


def check_generic_relations(**kwargs):
    from .fields import ReverseGenericRelatedObjectsDescriptor

    errors = []
    descriptors = (obj
        for cls in apps.get_models()
        for obj in six.itervalues(vars(cls))
        if isinstance(obj, ReverseGenericRelatedObjectsDescriptor))
    for descriptor in descriptors:
        errors.extend(descriptor.field.check())
    return errors
