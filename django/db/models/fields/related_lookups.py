import warnings
from collections.abc import Iterator

from django.db.models.expressions import ColPairs
from django.db.models.fields import composite
from django.db.models.fields.tuple_lookups import TupleIn, tuple_lookups
from django.db.models.lookups import (
    Exact,
    GreaterThan,
    GreaterThanOrEqual,
    In,
    IsNull,
    LessThan,
    LessThanOrEqual,
)
from django.utils.deprecation import RemovedInDjango2029Warning
from django.utils.warnings import django_file_prefixes


def warn_new_instance(value):
    from django.db.models import Model

    # RemovedInDjango2029Warning: raise ValueError instead.
    if isinstance(value, Model) and value._state.adding and value._is_pk_set():
        warnings.warn(
            "Passing a newly constructed model instance to related filters is "
            "deprecated. Pass target field values instead.",
            RemovedInDjango2029Warning,
            skip_file_prefixes=django_file_prefixes(),
        )


def get_target_values(instance, field):
    """
    Return the values of instance that a related lookup on field compares.
    """
    if not instance._is_pk_set():
        raise ValueError("Model instances passed to related filters must be saved.")
    value_list = []
    for source in composite.unnest(field.path_infos[-1].target_fields):
        while not isinstance(instance, source.model) and source.remote_field:
            source = source.remote_field.model._meta.get_field(
                source.remote_field.field_name
            )
        try:
            value_list.append(getattr(instance, source.attname))
        except AttributeError:
            # A case like
            # Restaurant.objects.filter(place=restaurant_instance), where
            # place is a OneToOneField and the primary key of Restaurant.
            pk = instance.pk
            return pk if isinstance(pk, tuple) else (pk,)
    return tuple(value_list)


def get_normalized_value(value, lhs, warn=True):
    from django.db.models import Model

    if isinstance(value, Model):
        if not value._is_pk_set():
            raise ValueError("Model instances passed to related filters must be saved.")
        if warn:
            warn_new_instance(value)
        return get_target_values(value, lhs.output_field)
    if not isinstance(value, tuple):
        return (value,)
    return value


class RelatedIn(In):
    def get_prep_lookup(self):
        from django.db.models.sql.query import Query  # avoid circular import

        if isinstance(self.lhs, ColPairs):
            if (
                isinstance(self.rhs, Query)
                and not self.rhs.has_select_fields
                and self.lhs.output_field.related_model is self.rhs.model
            ):
                self.rhs.set_values([f.name for f in self.lhs.sources])
            elif self.rhs_is_direct_value():
                # Multi-column values are normalized at compile time.
                if isinstance(self.rhs, Iterator):
                    self.rhs = list(self.rhs)
                for value in self.rhs:
                    warn_new_instance(value)
        else:
            if self.rhs_is_direct_value():
                # If we get here, we are dealing with single-column relations.
                self.rhs = [get_normalized_value(val, self.lhs)[0] for val in self.rhs]
                # We need to run the related field's get_prep_value(). Consider
                # case ForeignKey to IntegerField given value 'abc'. The
                # ForeignKey itself doesn't have validation for non-integers,
                # so we must run validation using the target field.
                if hasattr(self.lhs.output_field, "path_infos"):
                    # Run the target field's get_prep_value. We can safely
                    # assume there is only one as we don't get to the direct
                    # value branch otherwise.
                    target_field = self.lhs.output_field.path_infos[-1].target_fields[
                        -1
                    ]
                    self.rhs = [target_field.get_prep_value(v) for v in self.rhs]
                    self.prepare_rhs = False
            elif not getattr(self.rhs, "has_select_fields", True) and not getattr(
                self.lhs.field.target_field, "primary_key", False
            ):
                if (
                    getattr(self.lhs.output_field, "primary_key", False)
                    and self.lhs.output_field.model == self.rhs.model
                ):
                    # A case like
                    # Restaurant.objects.filter(place__in=restaurant_qs), where
                    # place is a OneToOneField and the primary key of
                    # Restaurant.
                    target_field = self.lhs.field.name
                else:
                    target_field = self.lhs.field.target_field.name
                self.rhs.set_values([target_field])
        return super().get_prep_lookup()

    def as_sql(self, compiler, connection):
        if isinstance(self.lhs, ColPairs):
            if self.rhs_is_direct_value():
                values = [
                    get_normalized_value(value, self.lhs, warn=False)
                    for value in self.rhs
                ]
                lookup = TupleIn(self.lhs, values)
            else:
                lookup = TupleIn(self.lhs, self.rhs)
            return compiler.compile(lookup)

        return super().as_sql(compiler, connection)


class RelatedLookupMixin:
    def get_prep_lookup(self):
        if isinstance(self.lhs, ColPairs) and not hasattr(
            self.rhs, "resolve_expression"
        ):
            # Multi-column values are normalized at compile time.
            warn_new_instance(self.rhs)
        if not isinstance(self.lhs, ColPairs) and not hasattr(
            self.rhs, "resolve_expression"
        ):
            # If we get here, we are dealing with single-column relations.
            self.rhs = get_normalized_value(self.rhs, self.lhs)[0]
            # We need to run the related field's get_prep_value(). Consider
            # case ForeignKey to IntegerField given value 'abc'. The ForeignKey
            # itself doesn't have validation for non-integers, so we must run
            # validation using the target field.
            if self.prepare_rhs and hasattr(self.lhs.output_field, "path_infos"):
                # Get the target field. We can safely assume there is only one
                # as we don't get to the direct value branch otherwise.
                target_field = self.lhs.output_field.path_infos[-1].target_fields[-1]
                self.rhs = target_field.get_prep_value(self.rhs)

        return super().get_prep_lookup()

    def as_sql(self, compiler, connection):
        if isinstance(self.lhs, ColPairs):
            if not self.rhs_is_direct_value():
                raise ValueError(
                    f"'{self.lookup_name}' doesn't support multi-column subqueries."
                )
            self.rhs = get_normalized_value(self.rhs, self.lhs, warn=False)
            lookup_class = tuple_lookups[self.lookup_name]
            lookup = lookup_class(self.lhs, self.rhs)
            return compiler.compile(lookup)

        return super().as_sql(compiler, connection)


class RelatedExact(RelatedLookupMixin, Exact):
    pass


class RelatedLessThan(RelatedLookupMixin, LessThan):
    pass


class RelatedGreaterThan(RelatedLookupMixin, GreaterThan):
    pass


class RelatedGreaterThanOrEqual(RelatedLookupMixin, GreaterThanOrEqual):
    pass


class RelatedLessThanOrEqual(RelatedLookupMixin, LessThanOrEqual):
    pass


class RelatedIsNull(RelatedLookupMixin, IsNull):
    pass
