from django.db.models.expressions import Cols
from django.db.models.fields.composite import unnest_composite_fields
from django.db.models.fields.tuple_lookups import tuple_lookups
from django.db.models.lookups import (
    Exact,
    GreaterThan,
    GreaterThanOrEqual,
    In,
    IsNull,
    LessThan,
    LessThanOrEqual,
)


def get_normalized_value(value, lhs):
    from django.db.models import Model

    if isinstance(value, Model):
        pk = value.pk
        opts = value._meta
        if not opts.pk.is_set(pk):
            raise ValueError("Model instances passed to related filters must be saved.")
        value_list = []
        sources = unnest_composite_fields(lhs.output_field.path_infos[-1].target_fields)
        for source in sources:
            while not isinstance(value, source.model) and source.remote_field:
                source = source.remote_field.model._meta.get_field(
                    source.remote_field.field_name
                )
            try:
                value_list.append(getattr(value, source.attname))
            except AttributeError:
                # A case like Restaurant.objects.filter(place=restaurant_instance),
                # where place is a OneToOneField and the primary key of Restaurant.
                return pk if isinstance(pk, tuple) else (pk,)
        return tuple(value_list)
    if not isinstance(value, tuple):
        return (value,)
    return value


class RelatedIn(In):
    def get_prep_lookup(self):
        if not isinstance(self.lhs, Cols):
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
        if isinstance(self.lhs, Cols):
            # For multicolumn lookups we need to build a multicolumn where clause.
            # This clause is either a SubqueryConstraint (for values that need
            # to be compiled to SQL) or an OR-combined list of
            # (col1 = val1 AND col2 = val2 AND ...) clauses.
            from django.db.models.sql.where import SubqueryConstraint

            if self.rhs_is_direct_value():
                values = [get_normalized_value(value, self.lhs) for value in self.rhs]
                lookup_cls = tuple_lookups["in"]
                lookup = lookup_cls(self.lhs, values)
                return lookup.as_sql(compiler, connection)
            else:
                return SubqueryConstraint(
                    self.lhs.alias,
                    [target.column for target in self.lhs.targets],
                    [source.name for source in self.lhs.sources],
                    self.rhs,
                ).as_sql(compiler, connection)
        return super().as_sql(compiler, connection)


class RelatedLookupMixin:
    def get_prep_lookup(self):
        if not isinstance(self.lhs, Cols) and not hasattr(
            self.rhs, "resolve_expression"
        ):
            # If we get here, we are dealing with single-column relations.
            self.rhs = get_normalized_value(self.rhs, self.lhs)[0]
            # We need to run the related field's get_prep_value(). Consider case
            # ForeignKey to IntegerField given value 'abc'. The ForeignKey itself
            # doesn't have validation for non-integers, so we must run validation
            # using the target field.
            if self.prepare_rhs and hasattr(self.lhs.output_field, "path_infos"):
                # Get the target field. We can safely assume there is only one
                # as we don't get to the direct value branch otherwise.
                target_field = self.lhs.output_field.path_infos[-1].target_fields[-1]
                self.rhs = target_field.get_prep_value(self.rhs)

        return super().get_prep_lookup()

    def as_sql(self, compiler, connection):
        if isinstance(self.lhs, Cols):
            assert self.rhs_is_direct_value()
            self.rhs = get_normalized_value(self.rhs, self.lhs)
            lookup_cls = tuple_lookups[self.lookup_name]
            lookup = lookup_cls(self.lhs, self.rhs)
            return lookup.as_sql(compiler, connection)
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
