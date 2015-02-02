from django.db.models.lookups import (
    In, Exact, LessThan, LessThanOrEqual, GreaterThan, GreaterThanOrEqual)


class MultiColSource(object):
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


def get_normalized_value(value, lhs):
    from django.db.models import Model
    if isinstance(value, Model):
        value_list = []
        # Account for one-to-one relations when sent a different model
        sources = lhs.output_field.get_path_info()[-1].target_fields
        for source in sources:
            while not isinstance(value, source.model) and source.rel:
                source = source.rel.to._meta.get_field(source.rel.field_name)
            value_list.append(getattr(value, source.attname))
        return tuple(value_list)
    if not isinstance(value, tuple):
        return (value,)
    return value


class RelatedIn(In):
    def process_rhs(self, compiler, connection):
        if self.rhs_is_direct_value():
            # Note that if we get here, we are dealing with single-column relations
            self.rhs = [get_normalized_value(val, self.lhs)[0] for val in self.rhs]
        return super(RelatedIn, self).process_rhs(compiler, connection)

    def as_sql(self, compiler, connection):
        if isinstance(self.lhs, MultiColSource):
            # For multicolumn lookups we need to build a multicolumn where clause
            # This clause is either a SubqueryConstraint (for values that need to be compiled to
            # SQL), or a OR-combined list of (col1 = val1 AND col2 = val2 AND ...) clauses.
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
            return super(RelatedIn, self).as_sql(compiler, connection)


class RelatedLookupMixin(object):
    def process_rhs(self, compiler, connection):
        if self.rhs_is_direct_value():
            # Note that if we get here, we are dealing with single-column relations
            self.rhs = get_normalized_value(self.rhs, self.lhs)[0]
        return super(RelatedLookupMixin, self).process_rhs(compiler, connection)

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
        return super(RelatedLookupMixin, self).as_sql(compiler, connection)


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
