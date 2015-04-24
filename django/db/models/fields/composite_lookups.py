from django.db.models.expressions import Expression
from django.db.models.lookups import Exact, In, IsNull, Transform
from django.utils import six
from django.utils.functional import cached_property


class CompositeCol(Expression):

    contains_aggregate = False

    def __init__(self, alias, target):
        self.alias, self.target = alias, target
        super(CompositeCol, self).__init__(output_field=target)

    def relabeled_clone(self, relabels):
        return self._class__(relabels.get(self.alias, self.alias), self.field)

    @cached_property
    def subcols(self):
        return [
            field.get_col(self.alias)
            for field in self.target.subfields.values()
        ]

    @cached_property
    def width(self):
        return len(self.subcols)

    @property
    def aliased_subcols(self):
        prefix = self.target.name
        for col in self.subcols:
            yield col, '%s_%s' % (prefix, col.target.name)

    def as_sql(self, compiler, connection):
        sql = []
        prefix = self.target.name + '_'
        for subcol in self.subcols:
            s_sql, s_params = subcol.as_sql(compiler, connection)
            sql.append('%s AS %s' % (s_sql, prefix + subcol.target.name))
        return ','.join(sql), []

    def __repr__(self):
        return "{}({}, {})".format(
            self.__class__.__name__, self.alias, self.target)

    def get_db_converters(self, connection):
        return self.target.get_db_converters(connection)


class CompositeExact(Exact):
    def as_sql(self, compiler, connection):
        from django.db.models.sql.where import WhereNode, AND
        constraint = WhereNode()

        subfields = six.iteritems(self.lhs.field.subfields)
        subfield_values = self.lhs.field.value_to_dict(self.rhs)

        for subfield_name, subfield in subfields:
            try:
                subfield_value = subfield_values[subfield_name]
            except KeyError:
                # TODO: Raise more appropriate error
                raise
            subfield_col = subfield.get_col(self.lhs.alias)
            constraint.add(
                subfield.get_lookup('exact')(subfield_col, subfield_value),
                AND
            )
        return constraint.as_sql(compiler, connection)


class CompositeIsNull(IsNull):
    def as_sql(self, compiler, connection):
        from django.db.models.sql.where import WhereNode, NothingNode

        if not self.lhs.field.null:
            # Avoid sending a deserialization of `None` on composite fields
            # which can't support it.
            constraint = NothingNode() if self.rhs else WhereNode()
        else:
            # Perform an exact lookup on whichever combination of subfields
            # corresponds to a python `None` value for the object. We assume
            # that value_to_dict is deterministic.
            constraint = self.lhs.get_lookup('exact')(self.lhs, None)
            constraint.negated = not self.rhs
        return constraint


class CompositeIn(In):
    def as_sql(self, compiler, connection):
        from django.db.models.sql.where import WhereNode, OR
        constraint = WhereNode()
        if not self.rhs_is_direct_value():
            for value in self.rhs:
                exact_lookup = self.lhs.get_lookup('exact')(self.lhs, value)
                constraint.add(exact_lookup.as_sql(compiler, connection), OR)
        else:
            raise NotImplementedError(
                'Only direct lookups are supported on composite fields'
            )
        return constraint


class SubfieldTransform(Transform):
    def __init__(self, lhs, init_lookups):
        self.output_field = lhs.target.get_subfield(init_lookups[0])
        lhs = self.output_field.get_col(lhs.alias)
        super(SubfieldTransform, self).__init__(lhs, init_lookups)

    def as_sql(self, compiler, connection):
        lhs, params = compiler.compile(self.lhs)
        return '%s' % lhs, params
