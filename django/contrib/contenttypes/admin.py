from functools import partial

from django.contrib.admin.checks import InlineModelAdminChecks
from django.contrib.admin.options import InlineModelAdmin, flatten_fieldsets
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.forms import (
    BaseGenericInlineFormSet,
    generic_inlineformset_factory,
)
from django.core import checks
from django.core.exceptions import FieldDoesNotExist
from django.forms import ALL_FIELDS
from django.forms.models import modelform_defines_fields


class GenericInlineModelAdminChecks(InlineModelAdminChecks):
    def _check_exclude_of_parent_model(self, obj, parent_model):
        # There's no FK to exclude, so no exclusion checks are required.
        return []

    def _check_relation(self, obj, parent_model):
        # There's no FK, but we do need to confirm that the ct_field and
        # ct_fk_field are valid, and that they are part of a GenericForeignKey.

        gfks = [
            f
            for f in obj.model._meta.private_fields
            if isinstance(f, GenericForeignKey)
        ]
        if not gfks:
            return [
                checks.Error(
                    "'%s' has no GenericForeignKey." % obj.model._meta.label,
                    obj=obj.__class__,
                    id="admin.E301",
                )
            ]
        else:
            # Check that the ct_field and ct_fk_fields exist
            try:
                obj.model._meta.get_field(obj.ct_field)
            except FieldDoesNotExist:
                return [
                    checks.Error(
                        "'ct_field' references '%s', which is not a field on '%s'."
                        % (
                            obj.ct_field,
                            obj.model._meta.label,
                        ),
                        obj=obj.__class__,
                        id="admin.E302",
                    )
                ]

            try:
                obj.model._meta.get_field(obj.ct_fk_field)
            except FieldDoesNotExist:
                return [
                    checks.Error(
                        "'ct_fk_field' references '%s', which is not a field on '%s'."
                        % (
                            obj.ct_fk_field,
                            obj.model._meta.label,
                        ),
                        obj=obj.__class__,
                        id="admin.E303",
                    )
                ]

            # There's one or more GenericForeignKeys; make sure that one of them
            # uses the right ct_field and ct_fk_field.
            for gfk in gfks:
                if gfk.ct_field == obj.ct_field and gfk.fk_field == obj.ct_fk_field:
                    return []

            return [
                checks.Error(
                    "'%s' has no GenericForeignKey using content type field '%s' and "
                    "object ID field '%s'."
                    % (
                        obj.model._meta.label,
                        obj.ct_field,
                        obj.ct_fk_field,
                    ),
                    obj=obj.__class__,
                    id="admin.E304",
                )
            ]


class GenericInlineModelAdmin(InlineModelAdmin):
    ct_field = "content_type"
    ct_fk_field = "object_id"
    formset = BaseGenericInlineFormSet

    checks_class = GenericInlineModelAdminChecks

    def get_formset(self, request, obj=None, **kwargs):
        if "fields" in kwargs:
            fields = kwargs.pop("fields")
        else:
            fields = flatten_fieldsets(self.get_fieldsets(request, obj))
        exclude = [*(self.exclude or []), *self.get_readonly_fields(request, obj)]
        if (
            self.exclude is None
            and hasattr(self.form, "_meta")
            and self.form._meta.exclude
        ):
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
            "exclude": exclude,
            **kwargs,
        }

        if defaults["fields"] is None and not modelform_defines_fields(
            defaults["form"]
        ):
            defaults["fields"] = ALL_FIELDS

        return generic_inlineformset_factory(self.model, **defaults)


class GenericStackedInline(GenericInlineModelAdmin):
    template = "admin/edit_inline/stacked.html"


class GenericTabularInline(GenericInlineModelAdmin):
    template = "admin/edit_inline/tabular.html"
