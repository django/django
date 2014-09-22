from __future__ import unicode_literals

from functools import partial

from django.contrib.admin.checks import InlineModelAdminChecks
from django.contrib.admin.options import InlineModelAdmin, flatten_fieldsets
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.forms import (
    BaseGenericInlineFormSet, generic_inlineformset_factory
)
from django.core import checks
from django.db.models.fields import FieldDoesNotExist
from django.forms import ALL_FIELDS
from django.forms.models import modelform_defines_fields


class GenericInlineModelAdminChecks(InlineModelAdminChecks):
    def _check_exclude_of_parent_model(self, cls, parent_model):
        # There's no FK to exclude, so no exclusion checks are required.
        return []

    def _check_relation(self, cls, parent_model):
        # There's no FK, but we do need to confirm that the ct_field and ct_fk_field are valid,
        # and that they are part of a GenericForeignKey.

        gfks = [
            f for f in cls.model._meta.virtual_fields
            if isinstance(f, GenericForeignKey)
        ]
        if len(gfks) == 0:
            return [
                checks.Error(
                    "'%s.%s' has no GenericForeignKey." % (
                        cls.model._meta.app_label, cls.model._meta.object_name
                    ),
                    hint=None,
                    obj=cls,
                    id='admin.E301'
                )
            ]
        else:
            # Check that the ct_field and ct_fk_fields exist
            try:
                cls.model._meta.get_field(cls.ct_field)
            except FieldDoesNotExist:
                return [
                    checks.Error(
                        "'ct_field' references '%s', which is not a field on '%s.%s'." % (
                            cls.ct_field, cls.model._meta.app_label, cls.model._meta.object_name
                        ),
                        hint=None,
                        obj=cls,
                        id='admin.E302'
                    )
                ]

            try:
                cls.model._meta.get_field(cls.ct_fk_field)
            except FieldDoesNotExist:
                return [
                    checks.Error(
                        "'ct_fk_field' references '%s', which is not a field on '%s.%s'." % (
                            cls.ct_fk_field, cls.model._meta.app_label, cls.model._meta.object_name
                        ),
                        hint=None,
                        obj=cls,
                        id='admin.E303'
                    )
                ]

            # There's one or more GenericForeignKeys; make sure that one of them
            # uses the right ct_field and ct_fk_field.
            for gfk in gfks:
                if gfk.ct_field == cls.ct_field and gfk.fk_field == cls.ct_fk_field:
                    return []

            return [
                checks.Error(
                    "'%s.%s' has no GenericForeignKey using content type field '%s' and object ID field '%s'." % (
                        cls.model._meta.app_label, cls.model._meta.object_name, cls.ct_field, cls.ct_fk_field
                    ),
                    hint=None,
                    obj=cls,
                    id='admin.E304'
                )
            ]


class GenericInlineModelAdmin(InlineModelAdmin):
    ct_field = "content_type"
    ct_fk_field = "object_id"
    formset = BaseGenericInlineFormSet

    checks_class = GenericInlineModelAdminChecks

    def get_formset(self, request, obj=None, **kwargs):
        if 'fields' in kwargs:
            fields = kwargs.pop('fields')
        else:
            fields = flatten_fieldsets(self.get_fieldsets(request, obj))
        if self.exclude is None:
            exclude = []
        else:
            exclude = list(self.exclude)
        exclude.extend(self.get_readonly_fields(request, obj))
        if self.exclude is None and hasattr(self.form, '_meta') and self.form._meta.exclude:
            # Take the custom ModelForm's Meta.exclude into account only if the
            # GenericInlineModelAdmin doesn't define its own.
            exclude.extend(self.form._meta.exclude)
        exclude = exclude or None
        can_delete = self.can_delete and self.has_delete_permission(request, obj)
        defaults = {
            "ct_field": self.ct_field,
            "fk_field": self.ct_fk_field,
            "form": self.form,
            "formfield_callback": partial(self.formfield_for_dbfield, request=request),
            "formset": self.formset,
            "extra": self.get_extra(request, obj),
            "can_delete": can_delete,
            "can_order": False,
            "fields": fields,
            "min_num": self.get_min_num(request, obj),
            "max_num": self.get_max_num(request, obj),
            "exclude": exclude
        }
        defaults.update(kwargs)

        if defaults['fields'] is None and not modelform_defines_fields(defaults['form']):
            defaults['fields'] = ALL_FIELDS

        return generic_inlineformset_factory(self.model, **defaults)


class GenericStackedInline(GenericInlineModelAdmin):
    template = 'admin/edit_inline/stacked.html'


class GenericTabularInline(GenericInlineModelAdmin):
    template = 'admin/edit_inline/tabular.html'
