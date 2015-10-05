from copy import copy

from django.conf import settings
from django.db.models.expressions import Func, Value
from django.db.models.fields import (
    DateField, DateTimeField, Field, IntegerField, TimeField,
)
from django.db.models.query_utils import RegisterLookupMixin
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.six.moves import range


class Lookup(object):
    lookup_name = None

    def __init__(self, lhs, rhs):
        self.lhs, self.rhs = lhs, rhs
        self.rhs = self.get_prep_lookup()
        if hasattr(self.lhs, 'get_bilateral_transforms'):
            bilateral_transforms = self.lhs.get_bilateral_transforms()
        else:
            bilateral_transforms = []
        if bilateral_transforms:
            # We should warn the user as soon as possible if he is trying to apply
            # a bilateral transformation on a nested QuerySet: that won't work.
            # We need to import QuerySet here so as to avoid circular
            from django.db.models.query import QuerySet
            if isinstance(rhs, QuerySet):
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
            params = self.lhs.output_field.get_db_prep_lookup(
                self.lookup_name, rhs, connection, prepared=True)
            sqls, sqls_params = ['%s'] * len(params), params
        return sqls, sqls_params

    def get_prep_lookup(self):
        return self.lhs.output_field.get_prep_lookup(self.lookup_name, self.rhs)

    def get_db_prep_lookup(self, value, connection):
        return (
            '%s', self.lhs.output_field.get_db_prep_lookup(
                self.lookup_name, value, connection, prepared=True))

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
        # instance, _as_sql QuerySet and as_sql just something with
        # as_sql. Finally the value can of course be just plain
        # Python value.
        if hasattr(value, 'get_compiler'):
            value = value.get_compiler(connection=connection)
        if hasattr(value, 'as_sql'):
            sql, params = compiler.compile(value)
            return '(' + sql + ')', params
        if hasattr(value, '_as_sql'):
            sql, params = value._as_sql(connection=connection)
            return '(' + sql + ')', params
        else:
            return self.get_db_prep_lookup(value, connection)

    def rhs_is_direct_value(self):
        return not(
            hasattr(self.rhs, 'as_sql') or
            hasattr(self.rhs, '_as_sql') or
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


class Transform(RegisterLookupMixin, Func):
    """
    RegisterLookupMixin() is first so that get_lookup() and get_transform()
    first examine self and then check output_field.
    """
    bilateral = False

    def __init__(self, expression, **extra):
        # Restrict Transform to allow only a single expression.
        super(Transform, self).__init__(expression, **extra)

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


class Exact(BuiltinLookup):
    lookup_name = 'exact'
Field.register_lookup(Exact)


class IExact(BuiltinLookup):
    lookup_name = 'iexact'

    def process_rhs(self, qn, connection):
        rhs, params = super(IExact, self).process_rhs(qn, connection)
        if params:
            params[0] = connection.ops.prep_for_iexact_query(params[0])
        return rhs, params


Field.register_lookup(IExact)


class GreaterThan(BuiltinLookup):
    lookup_name = 'gt'
Field.register_lookup(GreaterThan)


class GreaterThanOrEqual(BuiltinLookup):
    lookup_name = 'gte'
Field.register_lookup(GreaterThanOrEqual)


class LessThan(BuiltinLookup):
    lookup_name = 'lt'
Field.register_lookup(LessThan)


class LessThanOrEqual(BuiltinLookup):
    lookup_name = 'lte'
Field.register_lookup(LessThanOrEqual)


class In(BuiltinLookup):
    lookup_name = 'in'

    def process_rhs(self, compiler, connection):
        if self.rhs_is_direct_value():
            # rhs should be an iterable, we use batch_process_rhs
            # to prepare/transform those values
            rhs = list(self.rhs)
            if not rhs:
                from django.db.models.sql.datastructures import EmptyResultSet
                raise EmptyResultSet
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
Field.register_lookup(In)


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
        if (hasattr(self.rhs, 'get_compiler') or hasattr(self.rhs, 'as_sql')
                or hasattr(self.rhs, '_as_sql') or self.bilateral_transforms):
            pattern = connection.pattern_ops[self.lookup_name].format(connection.pattern_esc)
            return pattern.format(rhs)
        else:
            return super(PatternLookup, self).get_rhs_op(connection, rhs)


class Contains(PatternLookup):
    lookup_name = 'contains'

    def process_rhs(self, qn, connection):
        rhs, params = super(Contains, self).process_rhs(qn, connection)
        if params and not self.bilateral_transforms:
            params[0] = "%%%s%%" % connection.ops.prep_for_like_query(params[0])
        return rhs, params
Field.register_lookup(Contains)


class IContains(Contains):
    lookup_name = 'icontains'
Field.register_lookup(IContains)


class StartsWith(PatternLookup):
    lookup_name = 'startswith'

    def process_rhs(self, qn, connection):
        rhs, params = super(StartsWith, self).process_rhs(qn, connection)
        if params and not self.bilateral_transforms:
            params[0] = "%s%%" % connection.ops.prep_for_like_query(params[0])
        return rhs, params
Field.register_lookup(StartsWith)


class IStartsWith(PatternLookup):
    lookup_name = 'istartswith'

    def process_rhs(self, qn, connection):
        rhs, params = super(IStartsWith, self).process_rhs(qn, connection)
        if params and not self.bilateral_transforms:
            params[0] = "%s%%" % connection.ops.prep_for_like_query(params[0])
        return rhs, params
Field.register_lookup(IStartsWith)


class EndsWith(PatternLookup):
    lookup_name = 'endswith'

    def process_rhs(self, qn, connection):
        rhs, params = super(EndsWith, self).process_rhs(qn, connection)
        if params and not self.bilateral_transforms:
            params[0] = "%%%s" % connection.ops.prep_for_like_query(params[0])
        return rhs, params
Field.register_lookup(EndsWith)


class IEndsWith(PatternLookup):
    lookup_name = 'iendswith'

    def process_rhs(self, qn, connection):
        rhs, params = super(IEndsWith, self).process_rhs(qn, connection)
        if params and not self.bilateral_transforms:
            params[0] = "%%%s" % connection.ops.prep_for_like_query(params[0])
        return rhs, params
Field.register_lookup(IEndsWith)


class Between(BuiltinLookup):
    def get_rhs_op(self, connection, rhs):
        return "BETWEEN %s AND %s" % (rhs, rhs)


class Range(BuiltinLookup):
    lookup_name = 'range'

    def get_rhs_op(self, connection, rhs):
        return "BETWEEN %s AND %s" % (rhs[0], rhs[1])

    def process_rhs(self, compiler, connection):
        if self.rhs_is_direct_value():
            # rhs should be an iterable of 2 values, we use batch_process_rhs
            # to prepare/transform those values
            return self.batch_process_rhs(compiler, connection)
        else:
            return super(Range, self).process_rhs(compiler, connection)
Field.register_lookup(Range)


class IsNull(BuiltinLookup):
    lookup_name = 'isnull'

    def as_sql(self, compiler, connection):
        sql, params = compiler.compile(self.lhs)
        if self.rhs:
            return "%s IS NULL" % sql, params
        else:
            return "%s IS NOT NULL" % sql, params
Field.register_lookup(IsNull)


class Search(BuiltinLookup):
    lookup_name = 'search'

    def as_sql(self, compiler, connection):
        lhs, lhs_params = self.process_lhs(compiler, connection)
        rhs, rhs_params = self.process_rhs(compiler, connection)
        sql_template = connection.ops.fulltext_search_sql(field_name=lhs)
        return sql_template, lhs_params + rhs_params
Field.register_lookup(Search)


class Regex(BuiltinLookup):
    lookup_name = 'regex'

    def as_sql(self, compiler, connection):
        if self.lookup_name in connection.operators:
            return super(Regex, self).as_sql(compiler, connection)
        else:
            lhs, lhs_params = self.process_lhs(compiler, connection)
            rhs, rhs_params = self.process_rhs(compiler, connection)
            sql_template = connection.ops.regex_lookup(self.lookup_name)
            return sql_template % (lhs, rhs), lhs_params + rhs_params
Field.register_lookup(Regex)


class IRegex(Regex):
    lookup_name = 'iregex'
Field.register_lookup(IRegex)


class DateTimeDateTransform(Transform):
    lookup_name = 'date'

    @cached_property
    def output_field(self):
        return DateField()

    def as_sql(self, compiler, connection):
        lhs, lhs_params = compiler.compile(self.lhs)
        tzname = timezone.get_current_timezone_name() if settings.USE_TZ else None
        sql, tz_params = connection.ops.datetime_cast_date_sql(lhs, tzname)
        lhs_params.extend(tz_params)
        return sql, lhs_params


class DateTransform(Transform):
    def as_sql(self, compiler, connection):
        sql, params = compiler.compile(self.lhs)
        lhs_output_field = self.lhs.output_field
        if isinstance(lhs_output_field, DateTimeField):
            tzname = timezone.get_current_timezone_name() if settings.USE_TZ else None
            sql, tz_params = connection.ops.datetime_extract_sql(self.lookup_name, sql, tzname)
            params.extend(tz_params)
        elif isinstance(lhs_output_field, DateField):
            sql = connection.ops.date_extract_sql(self.lookup_name, sql)
        elif isinstance(lhs_output_field, TimeField):
            sql = connection.ops.time_extract_sql(self.lookup_name, sql)
        else:
            raise ValueError('DateTransform only valid on Date/Time/DateTimeFields')
        return sql, params

    @cached_property
    def output_field(self):
        return IntegerField()


class YearTransform(DateTransform):
    lookup_name = 'year'


class YearLookup(Lookup):
    def year_lookup_bounds(self, connection, year):
        output_field = self.lhs.lhs.output_field
        if isinstance(output_field, DateTimeField):
            bounds = connection.ops.year_lookup_bounds_for_datetime_field(year)
        else:
            bounds = connection.ops.year_lookup_bounds_for_date_field(year)
        return bounds


@YearTransform.register_lookup
class YearExact(YearLookup):
    lookup_name = 'exact'

    def as_sql(self, compiler, connection):
        # We will need to skip the extract part and instead go
        # directly with the originating field, that is self.lhs.lhs.
        lhs_sql, params = self.process_lhs(compiler, connection, self.lhs.lhs)
        rhs_sql, rhs_params = self.process_rhs(compiler, connection)
        bounds = self.year_lookup_bounds(connection, rhs_params[0])
        params.extend(bounds)
        return '%s BETWEEN %%s AND %%s' % lhs_sql, params


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


@YearTransform.register_lookup
class YearGt(YearComparisonLookup):
    lookup_name = 'gt'

    def get_bound(self, start, finish):
        return finish


@YearTransform.register_lookup
class YearGte(YearComparisonLookup):
    lookup_name = 'gte'

    def get_bound(self, start, finish):
        return start


@YearTransform.register_lookup
class YearLt(YearComparisonLookup):
    lookup_name = 'lt'

    def get_bound(self, start, finish):
        return start


@YearTransform.register_lookup
class YearLte(YearComparisonLookup):
    lookup_name = 'lte'

    def get_bound(self, start, finish):
        return finish


class MonthTransform(DateTransform):
    lookup_name = 'month'


class DayTransform(DateTransform):
    lookup_name = 'day'


class WeekDayTransform(DateTransform):
    lookup_name = 'week_day'


class HourTransform(DateTransform):
    lookup_name = 'hour'


class MinuteTransform(DateTransform):
    lookup_name = 'minute'


class SecondTransform(DateTransform):
    lookup_name = 'second'


DateField.register_lookup(YearTransform)
DateField.register_lookup(MonthTransform)
DateField.register_lookup(DayTransform)
DateField.register_lookup(WeekDayTransform)

TimeField.register_lookup(HourTransform)
TimeField.register_lookup(MinuteTransform)
TimeField.register_lookup(SecondTransform)

DateTimeField.register_lookup(DateTimeDateTransform)
DateTimeField.register_lookup(YearTransform)
DateTimeField.register_lookup(MonthTransform)
DateTimeField.register_lookup(DayTransform)
DateTimeField.register_lookup(WeekDayTransform)
DateTimeField.register_lookup(HourTransform)
DateTimeField.register_lookup(MinuteTransform)
DateTimeField.register_lookup(SecondTransform)
