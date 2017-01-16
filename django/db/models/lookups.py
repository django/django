import itertools
import math
import warnings
from copy import copy
from decimal import Decimal

from django.core.exceptions import EmptyResultSet
from django.db.models.expressions import Func, Value
from django.db.models.fields import (
    DateTimeField, DecimalField, Field, IntegerField,
)
from django.db.models.query_utils import RegisterLookupMixin
from django.utils.deprecation import RemovedInDjango20Warning
from django.utils.functional import cached_property
from django.utils.six.moves import range


class Lookup(object):
    lookup_name = None
    prepare_rhs = True

    def __init__(self, lhs, rhs):
        self.lhs, self.rhs = lhs, rhs
        self.rhs = self.get_prep_lookup()
        if hasattr(self.lhs, 'get_bilateral_transforms'):
            bilateral_transforms = self.lhs.get_bilateral_transforms()
        else:
            bilateral_transforms = []
        if bilateral_transforms:
            # Warn the user as soon as possible if they are trying to apply
            # a bilateral transformation on a nested QuerySet: that won't work.
            from django.db.models.sql.query import Query  # avoid circular import
            if isinstance(rhs, Query):
                raise NotImplementedError("Bilateral transformations on nested querysets are not supported.")
        self.bilateral_transforms = bilateral_transforms

    def apply_bilateral_transforms(self, value):
        for transform in self.bilateral_transforms:
            value = transform(value)
        return value

    def batch_process_rhs(self, compiler, connection, rhs=None):
        if rhs is None:
            rhs = self.rhs
        if self.bilateral_transforms:
            sqls, sqls_params = [], []
            for p in rhs:
                value = Value(p, output_field=self.lhs.output_field)
                value = self.apply_bilateral_transforms(value)
                value = value.resolve_expression(compiler.query)
                sql, sql_params = compiler.compile(value)
                sqls.append(sql)
                sqls_params.extend(sql_params)
        else:
            _, params = self.get_db_prep_lookup(rhs, connection)
            sqls, sqls_params = ['%s'] * len(params), params
        return sqls, sqls_params

    def get_source_expressions(self):
        if self.rhs_is_direct_value():
            return [self.lhs]
        return [self.lhs, self.rhs]

    def set_source_expressions(self, new_exprs):
        if len(new_exprs) == 1:
            self.lhs = new_exprs[0]
        else:
            self.lhs, self.rhs = new_exprs

    def get_prep_lookup(self):
        if hasattr(self.rhs, '_prepare'):
            return self.rhs._prepare(self.lhs.output_field)
        if self.prepare_rhs and hasattr(self.lhs.output_field, 'get_prep_value'):
            return self.lhs.output_field.get_prep_value(self.rhs)
        return self.rhs

    def get_db_prep_lookup(self, value, connection):
        return ('%s', [value])

    def process_lhs(self, compiler, connection, lhs=None):
        lhs = lhs or self.lhs
        return compiler.compile(lhs)

    def process_rhs(self, compiler, connection):
        value = self.rhs
        if self.bilateral_transforms:
            if self.rhs_is_direct_value():
                # Do not call get_db_prep_lookup here as the value will be
                # transformed before being used for lookup
                value = Value(value, output_field=self.lhs.output_field)
            value = self.apply_bilateral_transforms(value)
            value = value.resolve_expression(compiler.query)
        # Due to historical reasons there are a couple of different
        # ways to produce sql here. get_compiler is likely a Query
        # instance and as_sql just something with as_sql. Finally the value
        # can of course be just plain Python value.
        if hasattr(value, 'get_compiler'):
            value = value.get_compiler(connection=connection)
        if hasattr(value, 'as_sql'):
            sql, params = compiler.compile(value)
            return '(' + sql + ')', params
        else:
            return self.get_db_prep_lookup(value, connection)

    def rhs_is_direct_value(self):
        return not(
            hasattr(self.rhs, 'as_sql') or
            hasattr(self.rhs, 'get_compiler'))

    def relabeled_clone(self, relabels):
        new = copy(self)
        new.lhs = new.lhs.relabeled_clone(relabels)
        if hasattr(new.rhs, 'relabeled_clone'):
            new.rhs = new.rhs.relabeled_clone(relabels)
        return new

    def get_group_by_cols(self):
        cols = self.lhs.get_group_by_cols()
        if hasattr(self.rhs, 'get_group_by_cols'):
            cols.extend(self.rhs.get_group_by_cols())
        return cols

    def as_sql(self, compiler, connection):
        raise NotImplementedError

    @cached_property
    def contains_aggregate(self):
        return self.lhs.contains_aggregate or getattr(self.rhs, 'contains_aggregate', False)

    @property
    def is_summary(self):
        return self.lhs.is_summary or getattr(self.rhs, 'is_summary', False)


class Transform(RegisterLookupMixin, Func):
    """
    RegisterLookupMixin() is first so that get_lookup() and get_transform()
    first examine self and then check output_field.
    """
    bilateral = False
    arity = 1

    @property
    def lhs(self):
        return self.get_source_expressions()[0]

    def get_bilateral_transforms(self):
        if hasattr(self.lhs, 'get_bilateral_transforms'):
            bilateral_transforms = self.lhs.get_bilateral_transforms()
        else:
            bilateral_transforms = []
        if self.bilateral:
            bilateral_transforms.append(self.__class__)
        return bilateral_transforms


class BuiltinLookup(Lookup):
    def process_lhs(self, compiler, connection, lhs=None):
        lhs_sql, params = super(BuiltinLookup, self).process_lhs(
            compiler, connection, lhs)
        field_internal_type = self.lhs.output_field.get_internal_type()
        db_type = self.lhs.output_field.db_type(connection=connection)
        lhs_sql = connection.ops.field_cast_sql(
            db_type, field_internal_type) % lhs_sql
        lhs_sql = connection.ops.lookup_cast(self.lookup_name, field_internal_type) % lhs_sql
        return lhs_sql, list(params)

    def as_sql(self, compiler, connection):
        lhs_sql, params = self.process_lhs(compiler, connection)
        rhs_sql, rhs_params = self.process_rhs(compiler, connection)
        params.extend(rhs_params)
        rhs_sql = self.get_rhs_op(connection, rhs_sql)
        return '%s %s' % (lhs_sql, rhs_sql), params

    def get_rhs_op(self, connection, rhs):
        return connection.operators[self.lookup_name] % rhs


class FieldGetDbPrepValueMixin(object):
    """
    Some lookups require Field.get_db_prep_value() to be called on their
    inputs.
    """
    get_db_prep_lookup_value_is_iterable = False

    def get_db_prep_lookup(self, value, connection):
        # For relational fields, use the output_field of the 'field' attribute.
        field = getattr(self.lhs.output_field, 'field', None)
        get_db_prep_value = getattr(field, 'get_db_prep_value', None)
        if not get_db_prep_value:
            get_db_prep_value = self.lhs.output_field.get_db_prep_value
        return (
            '%s',
            [get_db_prep_value(v, connection, prepared=True) for v in value]
            if self.get_db_prep_lookup_value_is_iterable else
            [get_db_prep_value(value, connection, prepared=True)]
        )


class FieldGetDbPrepValueIterableMixin(FieldGetDbPrepValueMixin):
    """
    Some lookups require Field.get_db_prep_value() to be called on each value
    in an iterable.
    """
    get_db_prep_lookup_value_is_iterable = True

    def get_prep_lookup(self):
        prepared_values = []
        if hasattr(self.rhs, '_prepare'):
            # A subquery is like an iterable but its items shouldn't be
            # prepared independently.
            return self.rhs._prepare(self.lhs.output_field)
        for rhs_value in self.rhs:
            if hasattr(rhs_value, 'resolve_expression'):
                # An expression will be handled by the database but can coexist
                # alongside real values.
                pass
            elif self.prepare_rhs and hasattr(self.lhs.output_field, 'get_prep_value'):
                rhs_value = self.lhs.output_field.get_prep_value(rhs_value)
            prepared_values.append(rhs_value)
        return prepared_values

    def process_rhs(self, compiler, connection):
        if self.rhs_is_direct_value():
            # rhs should be an iterable of values. Use batch_process_rhs()
            # to prepare/transform those values.
            return self.batch_process_rhs(compiler, connection)
        else:
            return super(FieldGetDbPrepValueIterableMixin, self).process_rhs(compiler, connection)

    def resolve_expression_parameter(self, compiler, connection, sql, param):
        params = [param]
        if hasattr(param, 'resolve_expression'):
            param = param.resolve_expression(compiler.query)
        if hasattr(param, 'as_sql'):
            sql, params = param.as_sql(compiler, connection)
        return sql, params

    def batch_process_rhs(self, compiler, connection, rhs=None):
        pre_processed = super(FieldGetDbPrepValueIterableMixin, self).batch_process_rhs(compiler, connection, rhs)
        # The params list may contain expressions which compile to a
        # sql/param pair. Zip them to get sql and param pairs that refer to the
        # same argument and attempt to replace them with the result of
        # compiling the param step.
        sql, params = zip(*(
            self.resolve_expression_parameter(compiler, connection, sql, param)
            for sql, param in zip(*pre_processed)
        ))
        params = itertools.chain.from_iterable(params)
        return sql, tuple(params)


@Field.register_lookup
class Exact(FieldGetDbPrepValueMixin, BuiltinLookup):
    lookup_name = 'exact'


@Field.register_lookup
class IExact(BuiltinLookup):
    lookup_name = 'iexact'
    prepare_rhs = False

    def process_rhs(self, qn, connection):
        rhs, params = super(IExact, self).process_rhs(qn, connection)
        if params:
            params[0] = connection.ops.prep_for_iexact_query(params[0])
        return rhs, params


@Field.register_lookup
class GreaterThan(FieldGetDbPrepValueMixin, BuiltinLookup):
    lookup_name = 'gt'


@Field.register_lookup
class GreaterThanOrEqual(FieldGetDbPrepValueMixin, BuiltinLookup):
    lookup_name = 'gte'


@Field.register_lookup
class LessThan(FieldGetDbPrepValueMixin, BuiltinLookup):
    lookup_name = 'lt'


@Field.register_lookup
class LessThanOrEqual(FieldGetDbPrepValueMixin, BuiltinLookup):
    lookup_name = 'lte'


class IntegerFieldFloatRounding(object):
    """
    Allow floats to work as query values for IntegerField. Without this, the
    decimal portion of the float would always be discarded.
    """
    def get_prep_lookup(self):
        if isinstance(self.rhs, float):
            self.rhs = math.ceil(self.rhs)
        return super(IntegerFieldFloatRounding, self).get_prep_lookup()


@IntegerField.register_lookup
class IntegerGreaterThanOrEqual(IntegerFieldFloatRounding, GreaterThanOrEqual):
    pass


@IntegerField.register_lookup
class IntegerLessThan(IntegerFieldFloatRounding, LessThan):
    pass


class DecimalComparisonLookup(object):
    def as_sqlite(self, compiler, connection):
        lhs_sql, params = self.process_lhs(compiler, connection)
        rhs_sql, rhs_params = self.process_rhs(compiler, connection)
        params.extend(rhs_params)
        # For comparisons whose lhs is a DecimalField, cast rhs AS NUMERIC
        # because the rhs will have been converted to a string by the
        # rev_typecast_decimal() adapter.
        if isinstance(self.rhs, Decimal):
            rhs_sql = 'CAST(%s AS NUMERIC)' % rhs_sql
        rhs_sql = self.get_rhs_op(connection, rhs_sql)
        return '%s %s' % (lhs_sql, rhs_sql), params


@DecimalField.register_lookup
class DecimalGreaterThan(DecimalComparisonLookup, GreaterThan):
    pass


@DecimalField.register_lookup
class DecimalGreaterThanOrEqual(DecimalComparisonLookup, GreaterThanOrEqual):
    pass


@DecimalField.register_lookup
class DecimalLessThan(DecimalComparisonLookup, LessThan):
    pass


@DecimalField.register_lookup
class DecimalLessThanOrEqual(DecimalComparisonLookup, LessThanOrEqual):
    pass


@Field.register_lookup
class In(FieldGetDbPrepValueIterableMixin, BuiltinLookup):
    lookup_name = 'in'

    def process_rhs(self, compiler, connection):
        db_rhs = getattr(self.rhs, '_db', None)
        if db_rhs is not None and db_rhs != connection.alias:
            raise ValueError(
                "Subqueries aren't allowed across different databases. Force "
                "the inner query to be evaluated using `list(inner_query)`."
            )

        if self.rhs_is_direct_value():
            try:
                rhs = set(self.rhs)
            except TypeError:  # Unhashable items in self.rhs
                rhs = self.rhs

            if not rhs:
                raise EmptyResultSet

            # rhs should be an iterable; use batch_process_rhs() to
            # prepare/transform those values.
            sqls, sqls_params = self.batch_process_rhs(compiler, connection, rhs)
            placeholder = '(' + ', '.join(sqls) + ')'
            return (placeholder, sqls_params)
        else:
            return super(In, self).process_rhs(compiler, connection)

    def get_rhs_op(self, connection, rhs):
        return 'IN %s' % rhs

    def as_sql(self, compiler, connection):
        max_in_list_size = connection.ops.max_in_list_size()
        if self.rhs_is_direct_value() and max_in_list_size and len(self.rhs) > max_in_list_size:
            return self.split_parameter_list_as_sql(compiler, connection)
        return super(In, self).as_sql(compiler, connection)

    def split_parameter_list_as_sql(self, compiler, connection):
        # This is a special case for databases which limit the number of
        # elements which can appear in an 'IN' clause.
        max_in_list_size = connection.ops.max_in_list_size()
        lhs, lhs_params = self.process_lhs(compiler, connection)
        rhs, rhs_params = self.batch_process_rhs(compiler, connection)
        in_clause_elements = ['(']
        params = []
        for offset in range(0, len(rhs_params), max_in_list_size):
            if offset > 0:
                in_clause_elements.append(' OR ')
            in_clause_elements.append('%s IN (' % lhs)
            params.extend(lhs_params)
            sqls = rhs[offset: offset + max_in_list_size]
            sqls_params = rhs_params[offset: offset + max_in_list_size]
            param_group = ', '.join(sqls)
            in_clause_elements.append(param_group)
            in_clause_elements.append(')')
            params.extend(sqls_params)
        in_clause_elements.append(')')
        return ''.join(in_clause_elements), params


class PatternLookup(BuiltinLookup):

    def get_rhs_op(self, connection, rhs):
        # Assume we are in startswith. We need to produce SQL like:
        #     col LIKE %s, ['thevalue%']
        # For python values we can (and should) do that directly in Python,
        # but if the value is for example reference to other column, then
        # we need to add the % pattern match to the lookup by something like
        #     col LIKE othercol || '%%'
        # So, for Python values we don't need any special pattern, but for
        # SQL reference values or SQL transformations we need the correct
        # pattern added.
        if hasattr(self.rhs, 'get_compiler') or hasattr(self.rhs, 'as_sql') or self.bilateral_transforms:
            pattern = connection.pattern_ops[self.lookup_name].format(connection.pattern_esc)
            return pattern.format(rhs)
        else:
            return super(PatternLookup, self).get_rhs_op(connection, rhs)


@Field.register_lookup
class Contains(PatternLookup):
    lookup_name = 'contains'
    prepare_rhs = False

    def process_rhs(self, qn, connection):
        rhs, params = super(Contains, self).process_rhs(qn, connection)
        if params and not self.bilateral_transforms:
            params[0] = "%%%s%%" % connection.ops.prep_for_like_query(params[0])
        return rhs, params


@Field.register_lookup
class IContains(Contains):
    lookup_name = 'icontains'
    prepare_rhs = False


@Field.register_lookup
class StartsWith(PatternLookup):
    lookup_name = 'startswith'
    prepare_rhs = False

    def process_rhs(self, qn, connection):
        rhs, params = super(StartsWith, self).process_rhs(qn, connection)
        if params and not self.bilateral_transforms:
            params[0] = "%s%%" % connection.ops.prep_for_like_query(params[0])
        return rhs, params


@Field.register_lookup
class IStartsWith(PatternLookup):
    lookup_name = 'istartswith'
    prepare_rhs = False

    def process_rhs(self, qn, connection):
        rhs, params = super(IStartsWith, self).process_rhs(qn, connection)
        if params and not self.bilateral_transforms:
            params[0] = "%s%%" % connection.ops.prep_for_like_query(params[0])
        return rhs, params


@Field.register_lookup
class EndsWith(PatternLookup):
    lookup_name = 'endswith'
    prepare_rhs = False

    def process_rhs(self, qn, connection):
        rhs, params = super(EndsWith, self).process_rhs(qn, connection)
        if params and not self.bilateral_transforms:
            params[0] = "%%%s" % connection.ops.prep_for_like_query(params[0])
        return rhs, params


@Field.register_lookup
class IEndsWith(PatternLookup):
    lookup_name = 'iendswith'
    prepare_rhs = False

    def process_rhs(self, qn, connection):
        rhs, params = super(IEndsWith, self).process_rhs(qn, connection)
        if params and not self.bilateral_transforms:
            params[0] = "%%%s" % connection.ops.prep_for_like_query(params[0])
        return rhs, params


@Field.register_lookup
class Range(FieldGetDbPrepValueIterableMixin, BuiltinLookup):
    lookup_name = 'range'

    def get_rhs_op(self, connection, rhs):
        return "BETWEEN %s AND %s" % (rhs[0], rhs[1])


@Field.register_lookup
class IsNull(BuiltinLookup):
    lookup_name = 'isnull'
    prepare_rhs = False

    def as_sql(self, compiler, connection):
        sql, params = compiler.compile(self.lhs)
        if self.rhs:
            return "%s IS NULL" % sql, params
        else:
            return "%s IS NOT NULL" % sql, params


@Field.register_lookup
class Search(BuiltinLookup):
    lookup_name = 'search'
    prepare_rhs = False

    def as_sql(self, compiler, connection):
        warnings.warn(
            'The `__search` lookup is deprecated. See the 1.10 release notes '
            'for how to replace it.', RemovedInDjango20Warning, stacklevel=2
        )
        lhs, lhs_params = self.process_lhs(compiler, connection)
        rhs, rhs_params = self.process_rhs(compiler, connection)
        sql_template = connection.ops.fulltext_search_sql(field_name=lhs)
        return sql_template, lhs_params + rhs_params


@Field.register_lookup
class Regex(BuiltinLookup):
    lookup_name = 'regex'
    prepare_rhs = False

    def as_sql(self, compiler, connection):
        if self.lookup_name in connection.operators:
            return super(Regex, self).as_sql(compiler, connection)
        else:
            lhs, lhs_params = self.process_lhs(compiler, connection)
            rhs, rhs_params = self.process_rhs(compiler, connection)
            sql_template = connection.ops.regex_lookup(self.lookup_name)
            return sql_template % (lhs, rhs), lhs_params + rhs_params


@Field.register_lookup
class IRegex(Regex):
    lookup_name = 'iregex'


class YearLookup(Lookup):
    def year_lookup_bounds(self, connection, year):
        output_field = self.lhs.lhs.output_field
        if isinstance(output_field, DateTimeField):
            bounds = connection.ops.year_lookup_bounds_for_datetime_field(year)
        else:
            bounds = connection.ops.year_lookup_bounds_for_date_field(year)
        return bounds


class YearComparisonLookup(YearLookup):
    def as_sql(self, compiler, connection):
        # We will need to skip the extract part and instead go
        # directly with the originating field, that is self.lhs.lhs.
        lhs_sql, params = self.process_lhs(compiler, connection, self.lhs.lhs)
        rhs_sql, rhs_params = self.process_rhs(compiler, connection)
        rhs_sql = self.get_rhs_op(connection, rhs_sql)
        start, finish = self.year_lookup_bounds(connection, rhs_params[0])
        params.append(self.get_bound(start, finish))
        return '%s %s' % (lhs_sql, rhs_sql), params

    def get_rhs_op(self, connection, rhs):
        return connection.operators[self.lookup_name] % rhs

    def get_bound(self):
        raise NotImplementedError(
            'subclasses of YearComparisonLookup must provide a get_bound() method'
        )


class YearExact(YearLookup, Exact):
    lookup_name = 'exact'

    def as_sql(self, compiler, connection):
        # We will need to skip the extract part and instead go
        # directly with the originating field, that is self.lhs.lhs.
        lhs_sql, params = self.process_lhs(compiler, connection, self.lhs.lhs)
        rhs_sql, rhs_params = self.process_rhs(compiler, connection)
        try:
            # Check that rhs_params[0] exists (IndexError),
            # it isn't None (TypeError), and is a number (ValueError)
            int(rhs_params[0])
        except (IndexError, TypeError, ValueError):
            # Can't determine the bounds before executing the query, so skip
            # optimizations by falling back to a standard exact comparison.
            return super(Exact, self).as_sql(compiler, connection)
        bounds = self.year_lookup_bounds(connection, rhs_params[0])
        params.extend(bounds)
        return '%s BETWEEN %%s AND %%s' % lhs_sql, params


class YearGt(YearComparisonLookup):
    lookup_name = 'gt'

    def get_bound(self, start, finish):
        return finish


class YearGte(YearComparisonLookup):
    lookup_name = 'gte'

    def get_bound(self, start, finish):
        return start


class YearLt(YearComparisonLookup):
    lookup_name = 'lt'

    def get_bound(self, start, finish):
        return start


class YearLte(YearComparisonLookup):
    lookup_name = 'lte'

    def get_bound(self, start, finish):
        return finish
