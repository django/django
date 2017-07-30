from django.db.models.lookups import (
    Exact, GreaterThan, GreaterThanOrEqual, In, IsNull, LessThan,
    LessThanOrEqual,
)


class MultiColSource:
    contains_aggregate = False

    def __init__(self, alias, targets, sources, field):
        self.targets, self.sources, self.field, self.alias = targets, sources, field, alias
        self.output_field = self.field

    def __repr__(self):
        return "{}({}, {})".format(
            self.__class__.__name__, self.alias, self.field)

    def relabeled_clone(self, relabels):
        return self.__class__(relabels.get(self.alias, self.alias),
                              self.targets, self.sources, self.field)

    def get_lookup(self, lookup):
        return self.output_field.get_lookup(lookup)


def get_normalized_value(value, lhs):
    from django.db.models import Model
    if isinstance(value, Model):
        value_list = []
        sources = lhs.output_field.get_path_info()[-1].target_fields
        for source in sources:
            while not isinstance(value, source.model) and source.remote_field:
                source = source.remote_field.model._meta.get_field(source.remote_field.field_name)
            try:
                value_list.append(getattr(value, source.attname))
            except AttributeError:
                # A case like Restaurant.objects.filter(place=restaurant_instance),
                # where place is a OneToOneField and the primary key of Restaurant.
                return (value.pk,)
        return tuple(value_list)
    if not isinstance(value, tuple):
        return (value,)
    return value


class RelatedIn(In):
    def get_prep_lookup(self):
        if not isinstance(self.lhs, MultiColSource) and self.rhs_is_direct_value():
            # If we get here, we are dealing with single-column relations.
            self.rhs = [get_normalized_value(val, self.lhs)[0] for val in self.rhs]
            # We need to run the related field's get_prep_value(). Consider case
            # ForeignKey to IntegerField given value 'abc'. The ForeignKey itself
            # doesn't have validation for non-integers, so we must run validation
            # using the target field.
            if hasattr(self.lhs.output_field, 'get_path_info'):
                # Run the target field's get_prep_value. We can safely assume there is
                # only one as we don't get to the direct value branch otherwise.
                target_field = self.lhs.output_field.get_path_info()[-1].target_fields[-1]
                self.rhs = [target_field.get_prep_value(v) for v in self.rhs]
        return super().get_prep_lookup()

    def as_sql(self, compiler, connection):
        if isinstance(self.lhs, MultiColSource):
            # For multicolumn lookups we need to build a multicolumn where clause.
            # This clause is either a SubqueryConstraint (for values that need to be compiled to
            # SQL) or a OR-combined list of (col1 = val1 AND col2 = val2 AND ...) clauses.
            from django.db.models.sql.where import WhereNode, SubqueryConstraint, AND, OR

            root_constraint = WhereNode(connector=OR)
            if self.rhs_is_direct_value():
                values = [get_normalized_value(value, self.lhs) for value in self.rhs]
                for value in values:
                    value_constraint = WhereNode()
                    for source, target, val in zip(self.lhs.sources, self.lhs.targets, value):
                        lookup_class = target.get_lookup('exact')
                        lookup = lookup_class(target.get_col(self.lhs.alias, source), val)
                        value_constraint.add(lookup, AND)
                    root_constraint.add(value_constraint, OR)
            else:
                root_constraint.add(
                    SubqueryConstraint(
                        self.lhs.alias, [target.column for target in self.lhs.targets],
                        [source.name for source in self.lhs.sources], self.rhs),
                    AND)
            return root_constraint.as_sql(compiler, connection)
        else:
            if (not getattr(self.rhs, 'has_select_fields', True) and
                    not getattr(self.lhs.field.target_field, 'primary_key', False)):
                self.rhs.clear_select_clause()
                if (getattr(self.lhs.output_field, 'primary_key', False) and
                        self.lhs.output_field.model == self.rhs.model):
                    # A case like Restaurant.objects.filter(place__in=restaurant_qs),
                    # where place is a OneToOneField and the primary key of
                    # Restaurant.
                    target_field = self.lhs.field.name
                else:
                    target_field = self.lhs.field.target_field.name
                self.rhs.add_fields([target_field], True)
            return super().as_sql(compiler, connection)


class RelatedLookupMixin:
    def get_prep_lookup(self):
        if not isinstance(self.lhs, MultiColSource) and self.rhs_is_direct_value():
            # If we get here, we are dealing with single-column relations.
            self.rhs = get_normalized_value(self.rhs, self.lhs)[0]
            # We need to run the related field's get_prep_value(). Consider case
            # ForeignKey to IntegerField given value 'abc'. The ForeignKey itself
            # doesn't have validation for non-integers, so we must run validation
            # using the target field.
            if self.prepare_rhs and hasattr(self.lhs.output_field, 'get_path_info'):
                # Get the target field. We can safely assume there is only one
                # as we don't get to the direct value branch otherwise.
                target_field = self.lhs.output_field.get_path_info()[-1].target_fields[-1]
                self.rhs = target_field.get_prep_value(self.rhs)

        return super().get_prep_lookup()

    def as_sql(self, compiler, connection):
        if isinstance(self.lhs, MultiColSource):
            assert self.rhs_is_direct_value()
            self.rhs = get_normalized_value(self.rhs, self.lhs)
            from django.db.models.sql.where import WhereNode, AND
            root_constraint = WhereNode()
            for target, source, val in zip(self.lhs.targets, self.lhs.sources, self.rhs):
                lookup_class = target.get_lookup(self.lookup_name)
                root_constraint.add(
                    lookup_class(target.get_col(self.lhs.alias, source), val), AND)
            return root_constraint.as_sql(compiler, connection)
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
