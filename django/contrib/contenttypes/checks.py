# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.apps import apps
from django.contrib.admin.checks import InlineModelAdminChecks
from django.contrib.contenttypes.fields import GenericForeignKey
from django.core import checks
from django.forms.models import _get_foreign_key
from django.utils import six


class GenericInlineModelAdminChecks(InlineModelAdminChecks):

    def _check_fk_name(self, cls, parent_model):
        try:
            _get_foreign_key(parent_model, cls.model, fk_name=cls.fk_name)
        except ValueError as e:
            # Check if generic, if not add error.
            is_generic_inline_admin = any(
                isinstance(vf, GenericForeignKey) for vf in parent_model._meta.virtual_fields)
            if is_generic_inline_admin:
                return []
            return [checks.Error(e.args[0], hint=None, obj=cls, id='admin.E202')]
        else:
            return []


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
