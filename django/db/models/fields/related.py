import functools
import inspect
import warnings
from functools import partial

from django import forms
from django.apps import apps
from django.conf import SettingsReference, settings
from django.core import checks, exceptions
from django.db import connection, router
from django.db.backends import utils
from django.db.models import Q
from django.db.models.constants import LOOKUP_SEP
from django.db.models.deletion import CASCADE, SET_DEFAULT, SET_NULL
from django.db.models.query_utils import PathInfo
from django.db.models.utils import make_model_tuple
from django.utils.deprecation import RemovedInDjango60Warning
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

from . import Field
from .mixins import FieldCacheMixin
from .related_descriptors import (
    ForeignKeyDeferredAttribute,
    ForwardManyToOneDescriptor,
    ForwardOneToOneDescriptor,
    ManyToManyDescriptor,
    ReverseManyToOneDescriptor,
    ReverseOneToOneDescriptor,
)
from .related_lookups import (
    RelatedExact,
    RelatedGreaterThan,
    RelatedGreaterThanOrEqual,
    RelatedIn,
    RelatedIsNull,
    RelatedLessThan,
    RelatedLessThanOrEqual,
)
from .reverse_related import ForeignObjectRel, ManyToManyRel, ManyToOneRel, OneToOneRel

RECURSIVE_RELATIONSHIP_CONSTANT = "self"


def resolve_relation(scope_model, relation):
    """
    Transform relation into a model or fully-qualified model string of the form
    "app_label.ModelName", relative to scope_model.

    The relation argument can be:
      * RECURSIVE_RELATIONSHIP_CONSTANT, i.e. the string "self", in which case
        the model argument will be returned.
      * A bare model name without an app_label, in which case scope_model's
        app_label will be prepended.
      * An "app_label.ModelName" string.
      * A model class, which will be returned unchanged.
    """
    # Check for recursive relations
    if relation == RECURSIVE_RELATIONSHIP_CONSTANT:
        relation = scope_model

    # Look for an "app.Model" relation
    if isinstance(relation, str):
        if "." not in relation:
            relation = "%s.%s" % (scope_model._meta.app_label, relation)

    return relation


def lazy_related_operation(function, model, *related_models, **kwargs):
    """
    Schedule `function` to be called once `model` and all `related_models`
    have been imported and registered with the app registry. `function` will
    be called with the newly-loaded model classes as its positional arguments,
    plus any optional keyword arguments.

    The `model` argument must be a model class. Each subsequent positional
    argument is another model, or a reference to another model - see
    `resolve_relation()` for the various forms these may take. Any relative
    references will be resolved relative to `model`.

    This is a convenience wrapper for `Apps.lazy_model_operation` - the app
    registry model used is the one found in `model._meta.apps`.
    """
    models = [model] + [resolve_relation(model, rel) for rel in related_models]
    model_keys = (make_model_tuple(m) for m in models)
    apps = model._meta.apps
    return apps.lazy_model_operation(partial(function, **kwargs), *model_keys)


class RelatedField(FieldCacheMixin, Field):
    """Base class that all relational fields inherit from."""

    # Field flags
    one_to_many = False
    one_to_one = False
    many_to_many = False
    many_to_one = False

    def __init__(
        self,
        related_name=None,
        related_query_name=None,
        limit_choices_to=None,
        **kwargs,
    ):
        self._related_name = related_name
        self._related_query_name = related_query_name
        self._limit_choices_to = limit_choices_to
        super().__init__(**kwargs)

    @cached_property
    def related_model(self):
        # Can't cache this property until all the models are loaded.
        apps.check_models_ready()
        return self.remote_field.model

    def check(self, **kwargs):
        return [
            *super().check(**kwargs),
            *self._check_related_name_is_valid(),
            *self._check_related_query_name_is_valid(),
            *self._check_relation_model_exists(),
            *self._check_referencing_to_swapped_model(),
            *self._check_clashes(),
        ]

    def _check_related_name_is_valid(self):
        import keyword

        related_name = self.remote_field.related_name
        if related_name is None:
            return []
        is_valid_id = (
            not keyword.iskeyword(related_name) and related_name.isidentifier()
        )
        if not (is_valid_id or related_name.endswith("+")):
            return [
                checks.Error(
                    "The name '%s' is invalid related_name for field %s.%s"
                    % (
                        self.remote_field.related_name,
                        self.model._meta.object_name,
                        self.name,
                    ),
                    hint=(
                        "Related name must be a valid Python identifier or end with a "
                        "'+'"
                    ),
                    obj=self,
                    id="fields.E306",
                )
            ]
        return []

    def _check_related_query_name_is_valid(self):
        if self.remote_field.hidden:
            return []
        rel_query_name = self.related_query_name()
        errors = []
        if rel_query_name.endswith("_"):
            errors.append(
                checks.Error(
                    "Reverse query name '%s' must not end with an underscore."
                    % rel_query_name,
                    hint=(
                        "Add or change a related_name or related_query_name "
                        "argument for this field."
                    ),
                    obj=self,
                    id="fields.E308",
                )
            )
        if LOOKUP_SEP in rel_query_name:
            errors.append(
                checks.Error(
                    "Reverse query name '%s' must not contain '%s'."
                    % (rel_query_name, LOOKUP_SEP),
                    hint=(
                        "Add or change a related_name or related_query_name "
                        "argument for this field."
                    ),
                    obj=self,
                    id="fields.E309",
                )
            )
        return errors

    def _check_relation_model_exists(self):
        rel_is_missing = self.remote_field.model not in self.opts.apps.get_models(
            include_auto_created=True
        )
        rel_is_string = isinstance(self.remote_field.model, str)
        model_name = (
            self.remote_field.model
            if rel_is_string
            else self.remote_field.model._meta.object_name
        )
        if rel_is_missing and (
            rel_is_string or not self.remote_field.model._meta.swapped
        ):
            return [
                checks.Error(
                    "Field defines a relation with model '%s', which is either "
                    "not installed, or is abstract." % model_name,
                    obj=self,
                    id="fields.E300",
                )
            ]
        return []

    def _check_referencing_to_swapped_model(self):
        if (
            self.remote_field.model not in self.opts.apps.get_models()
            and not isinstance(self.remote_field.model, str)
            and self.remote_field.model._meta.swapped
        ):
            return [
                checks.Error(
                    "Field defines a relation with the model '%s', which has "
                    "been swapped out." % self.remote_field.model._meta.label,
                    hint="Update the relation to point at 'settings.%s'."
                    % self.remote_field.model._meta.swappable,
                    obj=self,
                    id="fields.E301",
                )
            ]
        return []

    def _check_clashes(self):
        """Check accessor and reverse query name clashes."""
        from django.db.models.base import ModelBase

        errors = []
        opts = self.model._meta

        # f.remote_field.model may be a string instead of a model. Skip if
        # model name is not resolved.
        if not isinstance(self.remote_field.model, ModelBase):
            return []

        # Consider that we are checking field `Model.foreign` and the models
        # are:
        #
        #     class Target(models.Model):
        #         model = models.IntegerField()
        #         model_set = models.IntegerField()
        #
        #     class Model(models.Model):
        #         foreign = models.ForeignKey(Target)
        #         m2m = models.ManyToManyField(Target)

        # rel_opts.object_name == "Target"
        rel_opts = self.remote_field.model._meta
        # If the field doesn't install a backward relation on the target model
        # (so `is_hidden` returns True), then there are no clashes to check
        # and we can skip these fields.
        rel_is_hidden = self.remote_field.hidden
        rel_name = self.remote_field.accessor_name  # i. e. "model_set"
        rel_query_name = self.related_query_name()  # i. e. "model"
        # i.e. "app_label.Model.field".
        field_name = "%s.%s" % (opts.label, self.name)

        # Check clashes between accessor or reverse query name of `field`
        # and any other field name -- i.e. accessor for Model.foreign is
        # model_set and it clashes with Target.model_set.
        potential_clashes = rel_opts.fields + rel_opts.many_to_many
        for clash_field in potential_clashes:
            if not rel_is_hidden and clash_field.name == rel_name:
                clash_name = f"{rel_opts.label}.{clash_field.name}"
                errors.append(
                    checks.Error(
                        f"Reverse accessor '{rel_opts.object_name}.{rel_name}' "
                        f"for '{field_name}' clashes with field name "
                        f"'{clash_name}'.",
                        hint=(
                            "Rename field '%s', or add/change a related_name "
                            "argument to the definition for field '%s'."
                        )
                        % (clash_name, field_name),
                        obj=self,
                        id="fields.E302",
                    )
                )

            if clash_field.name == rel_query_name:
                clash_name = f"{rel_opts.label}.{clash_field.name}"
                errors.append(
                    checks.Error(
                        "Reverse query name for '%s' clashes with field name '%s'."
                        % (field_name, clash_name),
                        hint=(
                            "Rename field '%s', or add/change a related_name "
                            "argument to the definition for field '%s'."
                        )
                        % (clash_name, field_name),
                        obj=self,
                        id="fields.E303",
                    )
                )

        # Check clashes between accessors/reverse query names of `field` and
        # any other field accessor -- i. e. Model.foreign accessor clashes with
        # Model.m2m accessor.
        potential_clashes = (r for r in rel_opts.related_objects if r.field is not self)
        for clash_field in potential_clashes:
            if not rel_is_hidden and clash_field.accessor_name == rel_name:
                clash_name = (
                    f"{clash_field.related_model._meta.label}.{clash_field.field.name}"
                )
                errors.append(
                    checks.Error(
                        f"Reverse accessor '{rel_opts.object_name}.{rel_name}' "
                        f"for '{field_name}' clashes with reverse accessor for "
                        f"'{clash_name}'.",
                        hint=(
                            "Add or change a related_name argument "
                            "to the definition for '%s' or '%s'."
                        )
                        % (field_name, clash_name),
                        obj=self,
                        id="fields.E304",
                    )
                )

            if clash_field.accessor_name == rel_query_name:
                clash_name = (
                    f"{clash_field.related_model._meta.label}.{clash_field.field.name}"
                )
                errors.append(
                    checks.Error(
                        "Reverse query name for '%s' clashes with reverse query name "
                        "for '%s'." % (field_name, clash_name),
                        hint=(
                            "Add or change a related_name argument "
                            "to the definition for '%s' or '%s'."
                        )
                        % (field_name, clash_name),
                        obj=self,
                        id="fields.E305",
                    )
                )

        return errors

    def db_type(self, connection):
        # By default related field will not have a column as it relates to
        # columns from another table.
        return None

    def contribute_to_class(self, cls, name, private_only=False, **kwargs):
        super().contribute_to_class(cls, name, private_only=private_only, **kwargs)

        self.opts = cls._meta

        if not cls._meta.abstract:
            if self.remote_field.related_name:
                related_name = self.remote_field.related_name
            else:
                related_name = self.opts.default_related_name
            if related_name:
                related_name %= {
                    "class": cls.__name__.lower(),
                    "model_name": cls._meta.model_name.lower(),
                    "app_label": cls._meta.app_label.lower(),
                }
                self.remote_field.related_name = related_name

            if self.remote_field.related_query_name:
                related_query_name = self.remote_field.related_query_name % {
                    "class": cls.__name__.lower(),
                    "app_label": cls._meta.app_label.lower(),
                }
                self.remote_field.related_query_name = related_query_name

            def resolve_related_class(model, related, field):
                field.remote_field.model = related
                field.do_related_class(related, model)

            lazy_related_operation(
                resolve_related_class, cls, self.remote_field.model, field=self
            )

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if self._limit_choices_to:
            kwargs["limit_choices_to"] = self._limit_choices_to
        if self._related_name is not None:
            kwargs["related_name"] = self._related_name
        if self._related_query_name is not None:
            kwargs["related_query_name"] = self._related_query_name
        return name, path, args, kwargs

    def get_forward_related_filter(self, obj):
        """
        Return the keyword arguments that when supplied to
        self.model.object.filter(), would select all instances related through
        this field to the remote obj. This is used to build the querysets
        returned by related descriptors. obj is an instance of
        self.related_field.model.
        """
        return {
            "%s__%s" % (self.name, rh_field.name): getattr(obj, rh_field.attname)
            for _, rh_field in self.related_fields
        }

    def get_reverse_related_filter(self, obj):
        """
        Complement to get_forward_related_filter(). Return the keyword
        arguments that when passed to self.related_field.model.object.filter()
        select all instances of self.related_field.model related through
        this field to obj. obj is an instance of self.model.
        """
        base_q = Q.create(
            [
                (rh_field.attname, getattr(obj, lh_field.attname))
                for lh_field, rh_field in self.related_fields
            ]
        )
        descriptor_filter = self.get_extra_descriptor_filter(obj)
        if isinstance(descriptor_filter, dict):
            return base_q & Q(**descriptor_filter)
        elif descriptor_filter:
            return base_q & descriptor_filter
        return base_q

    @property
    def swappable_setting(self):
        """
        Get the setting that this is powered from for swapping, or None
        if it's not swapped in / marked with swappable=False.
        """
        if self.swappable:
            # Work out string form of "to"
            if isinstance(self.remote_field.model, str):
                to_string = self.remote_field.model
            else:
                to_string = self.remote_field.model._meta.label
            return apps.get_swappable_settings_name(to_string)
        return None

    def set_attributes_from_rel(self):
        self.name = self.name or (
            self.remote_field.model._meta.model_name
            + "_"
            + self.remote_field.model._meta.pk.name
        )
        if self.verbose_name is None:
            self.verbose_name = self.remote_field.model._meta.verbose_name
        self.remote_field.set_field_name()

    def do_related_class(self, other, cls):
        self.set_attributes_from_rel()
        self.contribute_to_related_class(other, self.remote_field)

    def get_limit_choices_to(self):
        """
        Return ``limit_choices_to`` for this model field.

        If it is a callable, it will be invoked and the result will be
        returned.
        """
        if callable(self.remote_field.limit_choices_to):
            return self.remote_field.limit_choices_to()
        return self.remote_field.limit_choices_to

    def formfield(self, **kwargs):
        """
        Pass ``limit_choices_to`` to the field being constructed.

        Only passes it if there is a type that supports related fields.
        This is a similar strategy used to pass the ``queryset`` to the field
        being constructed.
        """
        defaults = {}
        if hasattr(self.remote_field, "get_related_field"):
            # If this is a callable, do not invoke it here. Just pass
            # it in the defaults for when the form class will later be
            # instantiated.
            limit_choices_to = self.remote_field.limit_choices_to
            defaults.update(
                {
                    "limit_choices_to": limit_choices_to,
                }
            )
        defaults.update(kwargs)
        return super().formfield(**defaults)

    def related_query_name(self):
        """
        Define the name that can be used to identify this related object in a
        table-spanning query.
        """
        return (
            self.remote_field.related_query_name
            or self.remote_field.related_name
            or self.opts.model_name
        )

    @property
    def target_field(self):
        """
        When filtering against this relation, return the field on the remote
        model against which the filtering should happen.
        """
        target_fields = self.path_infos[-1].target_fields
        if len(target_fields) > 1:
            raise exceptions.FieldError(
                "The relation has multiple target fields, but only single target field "
                "was asked for"
            )
        return target_fields[0]

    @cached_property
    def cache_name(self):
        return self.name


class ForeignObject(RelatedField):
    """
    Abstraction of the ForeignKey relation to support multi-column relations.
    """

    # Field flags
    many_to_many = False
    many_to_one = True
    one_to_many = False
    one_to_one = False

    requires_unique_target = True
    related_accessor_class = ReverseManyToOneDescriptor
    forward_related_accessor_class = ForwardManyToOneDescriptor
    rel_class = ForeignObjectRel

    def __init__(
        self,
        to,
        on_delete,
        from_fields,
        to_fields,
        rel=None,
        related_name=None,
        related_query_name=None,
        limit_choices_to=None,
        parent_link=False,
        swappable=True,
        **kwargs,
    ):
        if rel is None:
            rel = self.rel_class(
                self,
                to,
                related_name=related_name,
                related_query_name=related_query_name,
                limit_choices_to=limit_choices_to,
                parent_link=parent_link,
                on_delete=on_delete,
            )

        super().__init__(
            rel=rel,
            related_name=related_name,
            related_query_name=related_query_name,
            limit_choices_to=limit_choices_to,
            **kwargs,
        )

        self.from_fields = from_fields
        self.to_fields = to_fields
        self.swappable = swappable

    def __copy__(self):
        obj = super().__copy__()
        # Remove any cached PathInfo values.
        obj.__dict__.pop("path_infos", None)
        obj.__dict__.pop("reverse_path_infos", None)
        return obj

    def check(self, **kwargs):
        return [
            *super().check(**kwargs),
            *self._check_to_fields_exist(),
            *self._check_unique_target(),
        ]

    def _check_to_fields_exist(self):
        # Skip nonexistent models.
        if isinstance(self.remote_field.model, str):
            return []

        errors = []
        for to_field in self.to_fields:
            if to_field:
                try:
                    self.remote_field.model._meta.get_field(to_field)
                except exceptions.FieldDoesNotExist:
                    errors.append(
                        checks.Error(
                            "The to_field '%s' doesn't exist on the related "
                            "model '%s'."
                            % (to_field, self.remote_field.model._meta.label),
                            obj=self,
                            id="fields.E312",
                        )
                    )
        return errors

    def _check_unique_target(self):
        rel_is_string = isinstance(self.remote_field.model, str)
        if rel_is_string or not self.requires_unique_target:
            return []

        try:
            self.foreign_related_fields
        except exceptions.FieldDoesNotExist:
            return []

        if not self.foreign_related_fields:
            return []

        has_unique_constraint = any(
            rel_field.unique for rel_field in self.foreign_related_fields
        )
        if not has_unique_constraint:
            foreign_fields = {f.name for f in self.foreign_related_fields}
            remote_opts = self.remote_field.model._meta
            has_unique_constraint = any(
                frozenset(ut) <= foreign_fields for ut in remote_opts.unique_together
            ) or any(
                frozenset(uc.fields) <= foreign_fields
                for uc in remote_opts.total_unique_constraints
            )

        if not has_unique_constraint:
            if len(self.foreign_related_fields) > 1:
                field_combination = ", ".join(
                    f"'{rel_field.name}'" for rel_field in self.foreign_related_fields
                )
                model_name = self.remote_field.model.__name__
                return [
                    checks.Error(
                        f"No subset of the fields {field_combination} on model "
                        f"'{model_name}' is unique.",
                        hint=(
                            "Mark a single field as unique=True or add a set of "
                            "fields to a unique constraint (via unique_together "
                            "or a UniqueConstraint (without condition) in the "
                            "model Meta.constraints)."
                        ),
                        obj=self,
                        id="fields.E310",
                    )
                ]
            else:
                field_name = self.foreign_related_fields[0].name
                model_name = self.remote_field.model.__name__
                return [
                    checks.Error(
                        f"'{model_name}.{field_name}' must be unique because it is "
                        "referenced by a foreign key.",
                        hint=(
                            "Add unique=True to this field or add a "
                            "UniqueConstraint (without condition) in the model "
                            "Meta.constraints."
                        ),
                        obj=self,
                        id="fields.E311",
                    )
                ]
        return []

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs["on_delete"] = self.remote_field.on_delete
        kwargs["from_fields"] = self.from_fields
        kwargs["to_fields"] = self.to_fields

        if self.remote_field.parent_link:
            kwargs["parent_link"] = self.remote_field.parent_link
        if isinstance(self.remote_field.model, str):
            if "." in self.remote_field.model:
                app_label, model_name = self.remote_field.model.split(".")
                kwargs["to"] = "%s.%s" % (app_label, model_name.lower())
            else:
                kwargs["to"] = self.remote_field.model.lower()
        else:
            kwargs["to"] = self.remote_field.model._meta.label_lower
        # If swappable is True, then see if we're actually pointing to the target
        # of a swap.
        swappable_setting = self.swappable_setting
        if swappable_setting is not None:
            # If it's already a settings reference, error
            if hasattr(kwargs["to"], "setting_name"):
                if kwargs["to"].setting_name != swappable_setting:
                    raise ValueError(
                        "Cannot deconstruct a ForeignKey pointing to a model "
                        "that is swapped in place of more than one model (%s and %s)"
                        % (kwargs["to"].setting_name, swappable_setting)
                    )
            # Set it
            kwargs["to"] = SettingsReference(
                kwargs["to"],
                swappable_setting,
            )
        return name, path, args, kwargs

    def resolve_related_fields(self):
        if not self.from_fields or len(self.from_fields) != len(self.to_fields):
            raise ValueError(
                "Foreign Object from and to fields must be the same non-zero length"
            )
        if isinstance(self.remote_field.model, str):
            raise ValueError(
                "Related model %r cannot be resolved" % self.remote_field.model
            )
        related_fields = []
        for from_field_name, to_field_name in zip(self.from_fields, self.to_fields):
            from_field = (
                self
                if from_field_name == RECURSIVE_RELATIONSHIP_CONSTANT
                else self.opts.get_field(from_field_name)
            )
            to_field = (
                self.remote_field.model._meta.pk
                if to_field_name is None
                else self.remote_field.model._meta.get_field(to_field_name)
            )
            related_fields.append((from_field, to_field))
        return related_fields

    @cached_property
    def related_fields(self):
        return self.resolve_related_fields()

    @cached_property
    def reverse_related_fields(self):
        return [(rhs_field, lhs_field) for lhs_field, rhs_field in self.related_fields]

    @cached_property
    def local_related_fields(self):
        return tuple(lhs_field for lhs_field, rhs_field in self.related_fields)

    @cached_property
    def foreign_related_fields(self):
        return tuple(
            rhs_field for lhs_field, rhs_field in self.related_fields if rhs_field
        )

    def get_local_related_value(self, instance):
        return self.get_instance_value_for_fields(instance, self.local_related_fields)

    def get_foreign_related_value(self, instance):
        return self.get_instance_value_for_fields(instance, self.foreign_related_fields)

    @staticmethod
    def get_instance_value_for_fields(instance, fields):
        ret = []
        opts = instance._meta
        for field in fields:
            # Gotcha: in some cases (like fixture loading) a model can have
            # different values in parent_ptr_id and parent's id. So, use
            # instance.pk (that is, parent_ptr_id) when asked for instance.id.
            if field.primary_key:
                possible_parent_link = opts.get_ancestor_link(field.model)
                if (
                    not possible_parent_link
                    or possible_parent_link.primary_key
                    or possible_parent_link.model._meta.abstract
                ):
                    ret.append(instance.pk)
                    continue
            ret.append(getattr(instance, field.attname))
        return tuple(ret)

    def get_attname_column(self):
        attname, column = super().get_attname_column()
        return attname, None

    def get_joining_columns(self, reverse_join=False):
        warnings.warn(
            "ForeignObject.get_joining_columns() is deprecated. Use "
            "get_joining_fields() instead.",
            RemovedInDjango60Warning,
            stacklevel=2,
        )
        source = self.reverse_related_fields if reverse_join else self.related_fields
        return tuple(
            (lhs_field.column, rhs_field.column) for lhs_field, rhs_field in source
        )

    def get_reverse_joining_columns(self):
        warnings.warn(
            "ForeignObject.get_reverse_joining_columns() is deprecated. Use "
            "get_reverse_joining_fields() instead.",
            RemovedInDjango60Warning,
            stacklevel=2,
        )
        return self.get_joining_columns(reverse_join=True)

    def get_joining_fields(self, reverse_join=False):
        return tuple(
            self.reverse_related_fields if reverse_join else self.related_fields
        )

    def get_reverse_joining_fields(self):
        return self.get_joining_fields(reverse_join=True)

    def get_extra_descriptor_filter(self, instance):
        """
        Return an extra filter condition for related object fetching when
        user does 'instance.fieldname', that is the extra filter is used in
        the descriptor of the field.

        The filter should be either a dict usable in .filter(**kwargs) call or
        a Q-object. The condition will be ANDed together with the relation's
        joining columns.

        A parallel method is get_extra_restriction() which is used in
        JOIN and subquery conditions.
        """
        return {}

    def get_extra_restriction(self, alias, related_alias):
        """
        Return a pair condition used for joining and subquery pushdown. The
        condition is something that responds to as_sql(compiler, connection)
        method.

        Note that currently referring both the 'alias' and 'related_alias'
        will not work in some conditions, like subquery pushdown.

        A parallel method is get_extra_descriptor_filter() which is used in
        instance.fieldname related object fetching.
        """
        return None

    def get_path_info(self, filtered_relation=None):
        """Get path from this field to the related model."""
        opts = self.remote_field.model._meta
        from_opts = self.model._meta
        return [
            PathInfo(
                from_opts=from_opts,
                to_opts=opts,
                target_fields=self.foreign_related_fields,
                join_field=self,
                m2m=False,
                direct=True,
                filtered_relation=filtered_relation,
            )
        ]

    @cached_property
    def path_infos(self):
        return self.get_path_info()

    def get_reverse_path_info(self, filtered_relation=None):
        """Get path from the related model to this field's model."""
        opts = self.model._meta
        from_opts = self.remote_field.model._meta
        return [
            PathInfo(
                from_opts=from_opts,
                to_opts=opts,
                target_fields=(opts.pk,),
                join_field=self.remote_field,
                m2m=not self.unique,
                direct=False,
                filtered_relation=filtered_relation,
            )
        ]

    @cached_property
    def reverse_path_infos(self):
        return self.get_reverse_path_info()

    @classmethod
    @functools.cache
    def get_class_lookups(cls):
        bases = inspect.getmro(cls)
        bases = bases[: bases.index(ForeignObject) + 1]
        class_lookups = [parent.__dict__.get("class_lookups", {}) for parent in bases]
        return cls.merge_dicts(class_lookups)

    def contribute_to_class(self, cls, name, private_only=False, **kwargs):
        super().contribute_to_class(cls, name, private_only=private_only, **kwargs)
        setattr(cls, self.name, self.forward_related_accessor_class(self))

    def contribute_to_related_class(self, cls, related):
        # Internal FK's - i.e., those with a related name ending with '+' -
        # and swapped models don't get a related descriptor.
        if not self.remote_field.hidden and not related.related_model._meta.swapped:
            setattr(
                cls._meta.concrete_model,
                related.accessor_name,
                self.related_accessor_class(related),
            )
            # While 'limit_choices_to' might be a callable, simply pass
            # it along for later - this is too early because it's still
            # model load time.
            if self.remote_field.limit_choices_to:
                cls._meta.related_fkey_lookups.append(
                    self.remote_field.limit_choices_to
                )


ForeignObject.register_lookup(RelatedIn)
ForeignObject.register_lookup(RelatedExact)
ForeignObject.register_lookup(RelatedLessThan)
ForeignObject.register_lookup(RelatedGreaterThan)
ForeignObject.register_lookup(RelatedGreaterThanOrEqual)
ForeignObject.register_lookup(RelatedLessThanOrEqual)
ForeignObject.register_lookup(RelatedIsNull)


class ForeignKey(ForeignObject):
    """
    Provide a many-to-one relation by adding a column to the local model
    to hold the remote value.

    By default ForeignKey will target the pk of the remote model but this
    behavior can be changed by using the ``to_field`` argument.
    """

    descriptor_class = ForeignKeyDeferredAttribute
    # Field flags
    many_to_many = False
    many_to_one = True
    one_to_many = False
    one_to_one = False

    rel_class = ManyToOneRel

    empty_strings_allowed = False
    default_error_messages = {
        "invalid": _(
            "%(model)s instance with %(field)s %(value)r is not a valid choice."
        )
    }
    description = _("Foreign Key (type determined by related field)")

    def __init__(
        self,
        to,
        on_delete,
        related_name=None,
        related_query_name=None,
        limit_choices_to=None,
        parent_link=False,
        to_field=None,
        db_constraint=True,
        **kwargs,
    ):
        try:
            to._meta.model_name
        except AttributeError:
            if not isinstance(to, str):
                raise TypeError(
                    "%s(%r) is invalid. First parameter to ForeignKey must be "
                    "either a model, a model name, or the string %r"
                    % (
                        self.__class__.__name__,
                        to,
                        RECURSIVE_RELATIONSHIP_CONSTANT,
                    )
                )
        else:
            # For backwards compatibility purposes, we need to *try* and set
            # the to_field during FK construction. It won't be guaranteed to
            # be correct until contribute_to_class is called. Refs #12190.
            to_field = to_field or (to._meta.pk and to._meta.pk.name)
        if not callable(on_delete):
            raise TypeError("on_delete must be callable.")

        kwargs["rel"] = self.rel_class(
            self,
            to,
            to_field,
            related_name=related_name,
            related_query_name=related_query_name,
            limit_choices_to=limit_choices_to,
            parent_link=parent_link,
            on_delete=on_delete,
        )
        kwargs.setdefault("db_index", True)

        super().__init__(
            to,
            on_delete,
            related_name=related_name,
            related_query_name=related_query_name,
            limit_choices_to=limit_choices_to,
            from_fields=[RECURSIVE_RELATIONSHIP_CONSTANT],
            to_fields=[to_field],
            **kwargs,
        )
        self.db_constraint = db_constraint

    def __class_getitem__(cls, *args, **kwargs):
        return cls

    def check(self, **kwargs):
        return [
            *super().check(**kwargs),
            *self._check_on_delete(),
            *self._check_unique(),
        ]

    def _check_on_delete(self):
        on_delete = getattr(self.remote_field, "on_delete", None)
        if on_delete == SET_NULL and not self.null:
            return [
                checks.Error(
                    "Field specifies on_delete=SET_NULL, but cannot be null.",
                    hint=(
                        "Set null=True argument on the field, or change the on_delete "
                        "rule."
                    ),
                    obj=self,
                    id="fields.E320",
                )
            ]
        elif on_delete == SET_DEFAULT and not self.has_default():
            return [
                checks.Error(
                    "Field specifies on_delete=SET_DEFAULT, but has no default value.",
                    hint="Set a default value, or change the on_delete rule.",
                    obj=self,
                    id="fields.E321",
                )
            ]
        else:
            return []

    def _check_unique(self, **kwargs):
        return (
            [
                checks.Warning(
                    "Setting unique=True on a ForeignKey has the same effect as using "
                    "a OneToOneField.",
                    hint=(
                        "ForeignKey(unique=True) is usually better served by a "
                        "OneToOneField."
                    ),
                    obj=self,
                    id="fields.W342",
                )
            ]
            if self.unique
            else []
        )

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        del kwargs["to_fields"]
        del kwargs["from_fields"]
        # Handle the simpler arguments
        if self.db_index:
            del kwargs["db_index"]
        else:
            kwargs["db_index"] = False
        if self.db_constraint is not True:
            kwargs["db_constraint"] = self.db_constraint
        # Rel needs more work.
        to_meta = getattr(self.remote_field.model, "_meta", None)
        if self.remote_field.field_name and (
            not to_meta
            or (to_meta.pk and self.remote_field.field_name != to_meta.pk.name)
        ):
            kwargs["to_field"] = self.remote_field.field_name
        return name, path, args, kwargs

    def to_python(self, value):
        return self.target_field.to_python(value)

    @property
    def target_field(self):
        return self.foreign_related_fields[0]

    def validate(self, value, model_instance):
        if self.remote_field.parent_link:
            return
        super().validate(value, model_instance)
        if value is None:
            return

        using = router.db_for_read(self.remote_field.model, instance=model_instance)
        qs = self.remote_field.model._base_manager.using(using).filter(
            **{self.remote_field.field_name: value}
        )
        qs = qs.complex_filter(self.get_limit_choices_to())
        if not qs.exists():
            raise exceptions.ValidationError(
                self.error_messages["invalid"],
                code="invalid",
                params={
                    "model": self.remote_field.model._meta.verbose_name,
                    "pk": value,
                    "field": self.remote_field.field_name,
                    "value": value,
                },  # 'pk' is included for backwards compatibility
            )

    def resolve_related_fields(self):
        related_fields = super().resolve_related_fields()
        for from_field, to_field in related_fields:
            if (
                to_field
                and to_field.model != self.remote_field.model._meta.concrete_model
            ):
                raise exceptions.FieldError(
                    "'%s.%s' refers to field '%s' which is not local to model "
                    "'%s'."
                    % (
                        self.model._meta.label,
                        self.name,
                        to_field.name,
                        self.remote_field.model._meta.concrete_model._meta.label,
                    )
                )
        return related_fields

    def get_attname(self):
        return "%s_id" % self.name

    def get_attname_column(self):
        attname = self.get_attname()
        column = self.db_column or attname
        return attname, column

    def get_default(self):
        """Return the to_field if the default value is an object."""
        field_default = super().get_default()
        if isinstance(field_default, self.remote_field.model):
            return getattr(field_default, self.target_field.attname)
        return field_default

    def get_db_prep_save(self, value, connection):
        if value is None or (
            value == ""
            and (
                not self.target_field.empty_strings_allowed
                or connection.features.interprets_empty_strings_as_nulls
            )
        ):
            return None
        else:
            return self.target_field.get_db_prep_save(value, connection=connection)

    def get_db_prep_value(self, value, connection, prepared=False):
        return self.target_field.get_db_prep_value(value, connection, prepared)

    def get_prep_value(self, value):
        return self.target_field.get_prep_value(value)

    def contribute_to_related_class(self, cls, related):
        super().contribute_to_related_class(cls, related)
        if self.remote_field.field_name is None:
            self.remote_field.field_name = cls._meta.pk.name

    def formfield(self, *, using=None, **kwargs):
        if isinstance(self.remote_field.model, str):
            raise ValueError(
                "Cannot create form field for %r yet, because "
                "its related model %r has not been loaded yet"
                % (self.name, self.remote_field.model)
            )
        return super().formfield(
            **{
                "form_class": forms.ModelChoiceField,
                "queryset": self.remote_field.model._default_manager.using(using),
                "to_field_name": self.remote_field.field_name,
                **kwargs,
                "blank": self.blank,
            }
        )

    def db_check(self, connection):
        return None

    def db_type(self, connection):
        return self.target_field.rel_db_type(connection=connection)

    def cast_db_type(self, connection):
        return self.target_field.cast_db_type(connection=connection)

    def db_parameters(self, connection):
        target_db_parameters = self.target_field.db_parameters(connection)
        return {
            "type": self.db_type(connection),
            "check": self.db_check(connection),
            "collation": target_db_parameters.get("collation"),
        }

    def convert_empty_strings(self, value, expression, connection):
        if (not value) and isinstance(value, str):
            return None
        return value

    def get_db_converters(self, connection):
        converters = super().get_db_converters(connection)
        if connection.features.interprets_empty_strings_as_nulls:
            converters += [self.convert_empty_strings]
        return converters

    def get_col(self, alias, output_field=None):
        if output_field is None:
            output_field = self.target_field
            while isinstance(output_field, ForeignKey):
                output_field = output_field.target_field
                if output_field is self:
                    raise ValueError("Cannot resolve output_field.")
        return super().get_col(alias, output_field)


class OneToOneField(ForeignKey):
    """
    A OneToOneField is essentially the same as a ForeignKey, with the exception
    that it always carries a "unique" constraint with it and the reverse
    relation always returns the object pointed to (since there will only ever
    be one), rather than returning a list.
    """

    # Field flags
    many_to_many = False
    many_to_one = False
    one_to_many = False
    one_to_one = True

    related_accessor_class = ReverseOneToOneDescriptor
    forward_related_accessor_class = ForwardOneToOneDescriptor
    rel_class = OneToOneRel

    description = _("One-to-one relationship")

    def __init__(self, to, on_delete, to_field=None, **kwargs):
        kwargs["unique"] = True
        super().__init__(to, on_delete, to_field=to_field, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if "unique" in kwargs:
            del kwargs["unique"]
        return name, path, args, kwargs

    def formfield(self, **kwargs):
        if self.remote_field.parent_link:
            return None
        return super().formfield(**kwargs)

    def save_form_data(self, instance, data):
        if isinstance(data, self.remote_field.model):
            setattr(instance, self.name, data)
        else:
            setattr(instance, self.attname, data)
            # Remote field object must be cleared otherwise Model.save()
            # will reassign attname using the related object pk.
            if data is None:
                setattr(instance, self.name, data)

    def _check_unique(self, **kwargs):
        # Override ForeignKey since check isn't applicable here.
        return []


def create_many_to_many_intermediary_model(field, klass):
    from django.db import models

    def set_managed(model, related, through):
        through._meta.managed = model._meta.managed or related._meta.managed

    to_model = resolve_relation(klass, field.remote_field.model)
    name = "%s_%s" % (klass._meta.object_name, field.name)
    lazy_related_operation(set_managed, klass, to_model, name)

    to = make_model_tuple(to_model)[1]
    from_ = klass._meta.model_name
    if to == from_:
        to = "to_%s" % to
        from_ = "from_%s" % from_

    meta = type(
        "Meta",
        (),
        {
            "db_table": field._get_m2m_db_table(klass._meta),
            "auto_created": klass,
            "app_label": klass._meta.app_label,
            "db_tablespace": klass._meta.db_tablespace,
            "unique_together": (from_, to),
            "verbose_name": _("%(from)s-%(to)s relationship")
            % {"from": from_, "to": to},
            "verbose_name_plural": _("%(from)s-%(to)s relationships")
            % {"from": from_, "to": to},
            "apps": field.model._meta.apps,
        },
    )
    # Construct and return the new class.
    return type(
        name,
        (models.Model,),
        {
            "Meta": meta,
            "__module__": klass.__module__,
            from_: models.ForeignKey(
                klass,
                related_name="%s+" % name,
                db_tablespace=field.db_tablespace,
                db_constraint=field.remote_field.db_constraint,
                on_delete=CASCADE,
            ),
            to: models.ForeignKey(
                to_model,
                related_name="%s+" % name,
                db_tablespace=field.db_tablespace,
                db_constraint=field.remote_field.db_constraint,
                on_delete=CASCADE,
            ),
        },
    )


class ManyToManyField(RelatedField):
    """
    Provide a many-to-many relation by using an intermediary model that
    holds two ForeignKey fields pointed at the two sides of the relation.

    Unless a ``through`` model was provided, ManyToManyField will use the
    create_many_to_many_intermediary_model factory to automatically generate
    the intermediary model.
    """

    # Field flags
    many_to_many = True
    many_to_one = False
    one_to_many = False
    one_to_one = False

    rel_class = ManyToManyRel

    description = _("Many-to-many relationship")

    def __init__(
        self,
        to,
        related_name=None,
        related_query_name=None,
        limit_choices_to=None,
        symmetrical=None,
        through=None,
        through_fields=None,
        db_constraint=True,
        db_table=None,
        swappable=True,
        **kwargs,
    ):
        try:
            to._meta
        except AttributeError:
            if not isinstance(to, str):
                raise TypeError(
                    "%s(%r) is invalid. First parameter to ManyToManyField "
                    "must be either a model, a model name, or the string %r"
                    % (
                        self.__class__.__name__,
                        to,
                        RECURSIVE_RELATIONSHIP_CONSTANT,
                    )
                )

        if symmetrical is None:
            symmetrical = to == RECURSIVE_RELATIONSHIP_CONSTANT

        if through is not None and db_table is not None:
            raise ValueError(
                "Cannot specify a db_table if an intermediary model is used."
            )

        kwargs["rel"] = self.rel_class(
            self,
            to,
            related_name=related_name,
            related_query_name=related_query_name,
            limit_choices_to=limit_choices_to,
            symmetrical=symmetrical,
            through=through,
            through_fields=through_fields,
            db_constraint=db_constraint,
        )
        self.has_null_arg = "null" in kwargs

        super().__init__(
            related_name=related_name,
            related_query_name=related_query_name,
            limit_choices_to=limit_choices_to,
            **kwargs,
        )

        self.db_table = db_table
        self.swappable = swappable

    def check(self, **kwargs):
        return [
            *super().check(**kwargs),
            *self._check_unique(**kwargs),
            *self._check_relationship_model(**kwargs),
            *self._check_ignored_options(**kwargs),
            *self._check_table_uniqueness(**kwargs),
        ]

    def _check_unique(self, **kwargs):
        if self.unique:
            return [
                checks.Error(
                    "ManyToManyFields cannot be unique.",
                    obj=self,
                    id="fields.E330",
                )
            ]
        return []

    def _check_ignored_options(self, **kwargs):
        warnings = []

        if self.has_null_arg:
            warnings.append(
                checks.Warning(
                    "null has no effect on ManyToManyField.",
                    obj=self,
                    id="fields.W340",
                )
            )

        if self._validators:
            warnings.append(
                checks.Warning(
                    "ManyToManyField does not support validators.",
                    obj=self,
                    id="fields.W341",
                )
            )
        if self.remote_field.symmetrical and self._related_name:
            warnings.append(
                checks.Warning(
                    "related_name has no effect on ManyToManyField "
                    'with a symmetrical relationship, e.g. to "self".',
                    obj=self,
                    id="fields.W345",
                )
            )
        if self.db_comment:
            warnings.append(
                checks.Warning(
                    "db_comment has no effect on ManyToManyField.",
                    obj=self,
                    id="fields.W346",
                )
            )

        return warnings

    def _check_relationship_model(self, from_model=None, **kwargs):
        if hasattr(self.remote_field.through, "_meta"):
            qualified_model_name = "%s.%s" % (
                self.remote_field.through._meta.app_label,
                self.remote_field.through.__name__,
            )
        else:
            qualified_model_name = self.remote_field.through

        errors = []

        if self.remote_field.through not in self.opts.apps.get_models(
            include_auto_created=True
        ):
            # The relationship model is not installed.
            errors.append(
                checks.Error(
                    "Field specifies a many-to-many relation through model "
                    "'%s', which has not been installed." % qualified_model_name,
                    obj=self,
                    id="fields.E331",
                )
            )

        else:
            assert from_model is not None, (
                "ManyToManyField with intermediate "
                "tables cannot be checked if you don't pass the model "
                "where the field is attached to."
            )
            # Set some useful local variables
            to_model = resolve_relation(from_model, self.remote_field.model)
            from_model_name = from_model._meta.object_name
            if isinstance(to_model, str):
                to_model_name = to_model
            else:
                to_model_name = to_model._meta.object_name
            relationship_model_name = self.remote_field.through._meta.object_name
            self_referential = from_model == to_model
            # Count foreign keys in intermediate model
            if self_referential:
                seen_self = sum(
                    from_model == getattr(field.remote_field, "model", None)
                    for field in self.remote_field.through._meta.fields
                )

                if seen_self > 2 and not self.remote_field.through_fields:
                    errors.append(
                        checks.Error(
                            "The model is used as an intermediate model by "
                            "'%s', but it has more than two foreign keys "
                            "to '%s', which is ambiguous. You must specify "
                            "which two foreign keys Django should use via the "
                            "through_fields keyword argument."
                            % (self, from_model_name),
                            hint=(
                                "Use through_fields to specify which two foreign keys "
                                "Django should use."
                            ),
                            obj=self.remote_field.through,
                            id="fields.E333",
                        )
                    )

            else:
                # Count foreign keys in relationship model
                seen_from = sum(
                    from_model == getattr(field.remote_field, "model", None)
                    for field in self.remote_field.through._meta.fields
                )
                seen_to = sum(
                    to_model == getattr(field.remote_field, "model", None)
                    for field in self.remote_field.through._meta.fields
                )

                if seen_from > 1 and not self.remote_field.through_fields:
                    errors.append(
                        checks.Error(
                            (
                                "The model is used as an intermediate model by "
                                "'%s', but it has more than one foreign key "
                                "from '%s', which is ambiguous. You must specify "
                                "which foreign key Django should use via the "
                                "through_fields keyword argument."
                            )
                            % (self, from_model_name),
                            hint=(
                                "If you want to create a recursive relationship, "
                                'use ManyToManyField("%s", through="%s").'
                            )
                            % (
                                RECURSIVE_RELATIONSHIP_CONSTANT,
                                relationship_model_name,
                            ),
                            obj=self,
                            id="fields.E334",
                        )
                    )

                if seen_to > 1 and not self.remote_field.through_fields:
                    errors.append(
                        checks.Error(
                            "The model is used as an intermediate model by "
                            "'%s', but it has more than one foreign key "
                            "to '%s', which is ambiguous. You must specify "
                            "which foreign key Django should use via the "
                            "through_fields keyword argument." % (self, to_model_name),
                            hint=(
                                "If you want to create a recursive relationship, "
                                'use ManyToManyField("%s", through="%s").'
                            )
                            % (
                                RECURSIVE_RELATIONSHIP_CONSTANT,
                                relationship_model_name,
                            ),
                            obj=self,
                            id="fields.E335",
                        )
                    )

                if seen_from == 0 or seen_to == 0:
                    errors.append(
                        checks.Error(
                            "The model is used as an intermediate model by "
                            "'%s', but it does not have a foreign key to '%s' or '%s'."
                            % (self, from_model_name, to_model_name),
                            obj=self.remote_field.through,
                            id="fields.E336",
                        )
                    )

        # Validate `through_fields`.
        if self.remote_field.through_fields is not None:
            # Validate that we're given an iterable of at least two items
            # and that none of them is "falsy".
            if not (
                len(self.remote_field.through_fields) >= 2
                and self.remote_field.through_fields[0]
                and self.remote_field.through_fields[1]
            ):
                errors.append(
                    checks.Error(
                        "Field specifies 'through_fields' but does not provide "
                        "the names of the two link fields that should be used "
                        "for the relation through model '%s'." % qualified_model_name,
                        hint=(
                            "Make sure you specify 'through_fields' as "
                            "through_fields=('field1', 'field2')"
                        ),
                        obj=self,
                        id="fields.E337",
                    )
                )

            # Validate the given through fields -- they should be actual
            # fields on the through model, and also be foreign keys to the
            # expected models.
            else:
                assert from_model is not None, (
                    "ManyToManyField with intermediate "
                    "tables cannot be checked if you don't pass the model "
                    "where the field is attached to."
                )

                source, through, target = (
                    from_model,
                    self.remote_field.through,
                    self.remote_field.model,
                )
                source_field_name, target_field_name = self.remote_field.through_fields[
                    :2
                ]

                for field_name, related_model in (
                    (source_field_name, source),
                    (target_field_name, target),
                ):
                    possible_field_names = []
                    for f in through._meta.fields:
                        if (
                            hasattr(f, "remote_field")
                            and getattr(f.remote_field, "model", None) == related_model
                        ):
                            possible_field_names.append(f.name)
                    if possible_field_names:
                        hint = (
                            "Did you mean one of the following foreign keys to '%s': "
                            "%s?"
                            % (
                                related_model._meta.object_name,
                                ", ".join(possible_field_names),
                            )
                        )
                    else:
                        hint = None

                    try:
                        field = through._meta.get_field(field_name)
                    except exceptions.FieldDoesNotExist:
                        errors.append(
                            checks.Error(
                                "The intermediary model '%s' has no field '%s'."
                                % (qualified_model_name, field_name),
                                hint=hint,
                                obj=self,
                                id="fields.E338",
                            )
                        )
                    else:
                        if not (
                            hasattr(field, "remote_field")
                            and getattr(field.remote_field, "model", None)
                            == related_model
                        ):
                            errors.append(
                                checks.Error(
                                    "'%s.%s' is not a foreign key to '%s'."
                                    % (
                                        through._meta.object_name,
                                        field_name,
                                        related_model._meta.object_name,
                                    ),
                                    hint=hint,
                                    obj=self,
                                    id="fields.E339",
                                )
                            )

        return errors

    def _check_table_uniqueness(self, **kwargs):
        if (
            isinstance(self.remote_field.through, str)
            or not self.remote_field.through._meta.managed
        ):
            return []
        registered_tables = {
            model._meta.db_table: model
            for model in self.opts.apps.get_models(include_auto_created=True)
            if model != self.remote_field.through and model._meta.managed
        }
        m2m_db_table = self.m2m_db_table()
        model = registered_tables.get(m2m_db_table)
        # The second condition allows multiple m2m relations on a model if
        # some point to a through model that proxies another through model.
        if (
            model
            and model._meta.concrete_model
            != self.remote_field.through._meta.concrete_model
        ):
            if model._meta.auto_created:

                def _get_field_name(model):
                    for field in model._meta.auto_created._meta.many_to_many:
                        if field.remote_field.through is model:
                            return field.name

                opts = model._meta.auto_created._meta
                clashing_obj = "%s.%s" % (opts.label, _get_field_name(model))
            else:
                clashing_obj = model._meta.label
            if settings.DATABASE_ROUTERS:
                error_class, error_id = checks.Warning, "fields.W344"
                error_hint = (
                    "You have configured settings.DATABASE_ROUTERS. Verify "
                    "that the table of %r is correctly routed to a separate "
                    "database." % clashing_obj
                )
            else:
                error_class, error_id = checks.Error, "fields.E340"
                error_hint = None
            return [
                error_class(
                    "The field's intermediary table '%s' clashes with the "
                    "table name of '%s'." % (m2m_db_table, clashing_obj),
                    obj=self,
                    hint=error_hint,
                    id=error_id,
                )
            ]
        return []

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        # Handle the simpler arguments.
        if self.db_table is not None:
            kwargs["db_table"] = self.db_table
        if self.remote_field.db_constraint is not True:
            kwargs["db_constraint"] = self.remote_field.db_constraint
        # Lowercase model names as they should be treated as case-insensitive.
        if isinstance(self.remote_field.model, str):
            if "." in self.remote_field.model:
                app_label, model_name = self.remote_field.model.split(".")
                kwargs["to"] = "%s.%s" % (app_label, model_name.lower())
            else:
                kwargs["to"] = self.remote_field.model.lower()
        else:
            kwargs["to"] = self.remote_field.model._meta.label_lower
        if getattr(self.remote_field, "through", None) is not None:
            if isinstance(self.remote_field.through, str):
                kwargs["through"] = self.remote_field.through
            elif not self.remote_field.through._meta.auto_created:
                kwargs["through"] = self.remote_field.through._meta.label
        # If swappable is True, then see if we're actually pointing to the target
        # of a swap.
        swappable_setting = self.swappable_setting
        if swappable_setting is not None:
            # If it's already a settings reference, error.
            if hasattr(kwargs["to"], "setting_name"):
                if kwargs["to"].setting_name != swappable_setting:
                    raise ValueError(
                        "Cannot deconstruct a ManyToManyField pointing to a "
                        "model that is swapped in place of more than one model "
                        "(%s and %s)" % (kwargs["to"].setting_name, swappable_setting)
                    )

            kwargs["to"] = SettingsReference(
                kwargs["to"],
                swappable_setting,
            )
        return name, path, args, kwargs

    def _get_path_info(self, direct=False, filtered_relation=None):
        """Called by both direct and indirect m2m traversal."""
        int_model = self.remote_field.through
        linkfield1 = int_model._meta.get_field(self.m2m_field_name())
        linkfield2 = int_model._meta.get_field(self.m2m_reverse_field_name())
        if direct:
            join1infos = linkfield1.reverse_path_infos
            if filtered_relation:
                join2infos = linkfield2.get_path_info(filtered_relation)
            else:
                join2infos = linkfield2.path_infos
        else:
            join1infos = linkfield2.reverse_path_infos
            if filtered_relation:
                join2infos = linkfield1.get_path_info(filtered_relation)
            else:
                join2infos = linkfield1.path_infos
        # Get join infos between the last model of join 1 and the first model
        # of join 2. Assume the only reason these may differ is due to model
        # inheritance.
        join1_final = join1infos[-1].to_opts
        join2_initial = join2infos[0].from_opts
        if join1_final is join2_initial:
            intermediate_infos = []
        elif issubclass(join1_final.model, join2_initial.model):
            intermediate_infos = join1_final.get_path_to_parent(join2_initial.model)
        else:
            intermediate_infos = join2_initial.get_path_from_parent(join1_final.model)

        return [*join1infos, *intermediate_infos, *join2infos]

    def get_path_info(self, filtered_relation=None):
        return self._get_path_info(direct=True, filtered_relation=filtered_relation)

    @cached_property
    def path_infos(self):
        return self.get_path_info()

    def get_reverse_path_info(self, filtered_relation=None):
        return self._get_path_info(direct=False, filtered_relation=filtered_relation)

    @cached_property
    def reverse_path_infos(self):
        return self.get_reverse_path_info()

    def _get_m2m_db_table(self, opts):
        """
        Function that can be curried to provide the m2m table name for this
        relation.
        """
        if self.remote_field.through is not None:
            return self.remote_field.through._meta.db_table
        elif self.db_table:
            return self.db_table
        else:
            m2m_table_name = "%s_%s" % (utils.strip_quotes(opts.db_table), self.name)
            return utils.truncate_name(m2m_table_name, connection.ops.max_name_length())

    def _get_m2m_attr(self, related, attr):
        """
        Function that can be curried to provide the source accessor or DB
        column name for the m2m table.
        """
        cache_attr = "_m2m_%s_cache" % attr
        if hasattr(self, cache_attr):
            return getattr(self, cache_attr)
        if self.remote_field.through_fields is not None:
            link_field_name = self.remote_field.through_fields[0]
        else:
            link_field_name = None
        for f in self.remote_field.through._meta.fields:
            if (
                f.is_relation
                and f.remote_field.model == related.related_model
                and (link_field_name is None or link_field_name == f.name)
            ):
                setattr(self, cache_attr, getattr(f, attr))
                return getattr(self, cache_attr)

    def _get_m2m_reverse_attr(self, related, attr):
        """
        Function that can be curried to provide the related accessor or DB
        column name for the m2m table.
        """
        cache_attr = "_m2m_reverse_%s_cache" % attr
        if hasattr(self, cache_attr):
            return getattr(self, cache_attr)
        found = False
        if self.remote_field.through_fields is not None:
            link_field_name = self.remote_field.through_fields[1]
        else:
            link_field_name = None
        for f in self.remote_field.through._meta.fields:
            if f.is_relation and f.remote_field.model == related.model:
                if link_field_name is None and related.related_model == related.model:
                    # If this is an m2m-intermediate to self,
                    # the first foreign key you find will be
                    # the source column. Keep searching for
                    # the second foreign key.
                    if found:
                        setattr(self, cache_attr, getattr(f, attr))
                        break
                    else:
                        found = True
                elif link_field_name is None or link_field_name == f.name:
                    setattr(self, cache_attr, getattr(f, attr))
                    break
        return getattr(self, cache_attr)

    def contribute_to_class(self, cls, name, **kwargs):
        # To support multiple relations to self, it's useful to have a non-None
        # related name on symmetrical relations for internal reasons. The
        # concept doesn't make a lot of sense externally ("you want me to
        # specify *what* on my non-reversible relation?!"), so we set it up
        # automatically. The funky name reduces the chance of an accidental
        # clash.
        if self.remote_field.symmetrical and (
            self.remote_field.model == RECURSIVE_RELATIONSHIP_CONSTANT
            or self.remote_field.model == cls._meta.object_name
        ):
            self.remote_field.related_name = "%s_rel_+" % name
        elif self.remote_field.hidden:
            # If the backwards relation is disabled, replace the original
            # related_name with one generated from the m2m field name. Django
            # still uses backwards relations internally and we need to avoid
            # clashes between multiple m2m fields with related_name == '+'.
            self.remote_field.related_name = "_%s_%s_%s_+" % (
                cls._meta.app_label,
                cls.__name__.lower(),
                name,
            )

        super().contribute_to_class(cls, name, **kwargs)

        # The intermediate m2m model is not auto created if:
        #  1) There is a manually specified intermediate, or
        #  2) The class owning the m2m field is abstract.
        #  3) The class owning the m2m field has been swapped out.
        if not cls._meta.abstract:
            if self.remote_field.through:

                def resolve_through_model(_, model, field):
                    field.remote_field.through = model

                lazy_related_operation(
                    resolve_through_model, cls, self.remote_field.through, field=self
                )
            elif not cls._meta.swapped:
                self.remote_field.through = create_many_to_many_intermediary_model(
                    self, cls
                )

        # Add the descriptor for the m2m relation.
        setattr(cls, self.name, ManyToManyDescriptor(self.remote_field, reverse=False))

        # Set up the accessor for the m2m table name for the relation.
        self.m2m_db_table = partial(self._get_m2m_db_table, cls._meta)

    def contribute_to_related_class(self, cls, related):
        # Internal M2Ms (i.e., those with a related name ending with '+')
        # and swapped models don't get a related descriptor.
        if not self.remote_field.hidden and not related.related_model._meta.swapped:
            setattr(
                cls,
                related.accessor_name,
                ManyToManyDescriptor(self.remote_field, reverse=True),
            )

        # Set up the accessors for the column names on the m2m table.
        self.m2m_column_name = partial(self._get_m2m_attr, related, "column")
        self.m2m_reverse_name = partial(self._get_m2m_reverse_attr, related, "column")

        self.m2m_field_name = partial(self._get_m2m_attr, related, "name")
        self.m2m_reverse_field_name = partial(
            self._get_m2m_reverse_attr, related, "name"
        )

        get_m2m_rel = partial(self._get_m2m_attr, related, "remote_field")
        self.m2m_target_field_name = lambda: get_m2m_rel().field_name
        get_m2m_reverse_rel = partial(
            self._get_m2m_reverse_attr, related, "remote_field"
        )
        self.m2m_reverse_target_field_name = lambda: get_m2m_reverse_rel().field_name

    def set_attributes_from_rel(self):
        pass

    def value_from_object(self, obj):
        return list(getattr(obj, self.attname).all()) if obj._is_pk_set() else []

    def save_form_data(self, instance, data):
        getattr(instance, self.attname).set(data)

    def formfield(self, *, using=None, **kwargs):
        defaults = {
            "form_class": forms.ModelMultipleChoiceField,
            "queryset": self.remote_field.model._default_manager.using(using),
            **kwargs,
        }
        # If initial is passed in, it's a list of related objects, but the
        # MultipleChoiceField takes a list of IDs.
        if defaults.get("initial") is not None:
            initial = defaults["initial"]
            if callable(initial):
                initial = initial()
            defaults["initial"] = [i.pk for i in initial]
        return super().formfield(**defaults)

    def db_check(self, connection):
        return None

    def db_type(self, connection):
        # A ManyToManyField is not represented by a single column,
        # so return None.
        return None

    def db_parameters(self, connection):
        return {"type": None, "check": None}
