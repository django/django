from copy import copy

from django.conf import settings
from django.utils import timezone
from django.utils.functional import cached_property


class Extract(object):
    def __init__(self, lhs):
        self.lhs = lhs

    def get_lookup(self, lookup):
        return self.output_type.get_lookup(lookup)

    def as_sql(self, qn, connection):
        raise NotImplementedError

    @cached_property
    def output_type(self):
        return self.lhs.output_type

    def relabeled_clone(self, relabels):
        return self.__class__(self.lhs.relabeled_clone(relabels))

    def get_cols(self):
        return self.lhs.get_cols()


class Lookup(object):
    lookup_name = None

    def __init__(self, lhs, rhs):
        self.lhs, self.rhs = lhs, rhs
        self.rhs = self.get_prep_lookup()

    def get_prep_lookup(self):
        return self.lhs.output_type.get_prep_lookup(self.lookup_name, self.rhs)

    def get_db_prep_lookup(self, value, connection):
        return (
            '%s', self.lhs.output_type.get_db_prep_lookup(
                self.lookup_name, value, connection, prepared=True))

    def process_lhs(self, qn, connection, lhs=None):
        lhs = lhs or self.lhs
        return qn.compile(lhs)

    def process_rhs(self, qn, connection, rhs=None):
        value = rhs or self.rhs
        # Due to historical reasons there are a couple of different
        # ways to produce sql here. get_compiler is likely a Query
        # instance, _as_sql QuerySet and as_sql just something with
        # as_sql. Finally the value can of course be just plain
        # Python value.
        if hasattr(value, 'get_compiler'):
            value = value.get_compiler(connection=connection)
        if hasattr(value, 'as_sql'):
            sql, params = qn.compile(value)
            return '(' + sql + ')', params
        if hasattr(value, '_as_sql'):
            sql, params = value._as_sql(connection=connection)
            return '(' + sql + ')', params
        else:
            return self.get_db_prep_lookup(value, connection)

    def relabeled_clone(self, relabels):
        new = copy(self)
        new.lhs = new.lhs.relabeled_clone(relabels)
        if hasattr(new.rhs, 'relabeled_clone'):
            new.rhs = new.rhs.relabeled_clone(relabels)
        return new

    def get_cols(self):
        cols = self.lhs.get_cols()
        if hasattr(self.rhs, 'get_cols'):
            cols.extend(self.rhs.get_cols())
        return cols

    def as_sql(self, qn, connection):
        raise NotImplementedError


class DjangoLookup(Lookup):
    def as_sql(self, qn, connection):
        lhs_sql, params = self.process_lhs(qn, connection)
        field_internal_type = self.lhs.output_type.get_internal_type()
        db_type = self.lhs.output_type
        lhs_sql = connection.ops.field_cast_sql(db_type, field_internal_type) % lhs_sql
        lhs_sql = connection.ops.lookup_cast(self.lookup_name) % lhs_sql
        rhs_sql, rhs_params = self.process_rhs(qn, connection)
        params.extend(rhs_params)
        operator_plus_rhs = self.get_rhs_op(connection, rhs_sql)
        return '%s %s' % (lhs_sql, operator_plus_rhs), params

    def get_rhs_op(self, connection, rhs):
        return connection.operators[self.lookup_name] % rhs


default_lookups = {}


class Exact(DjangoLookup):
    lookup_name = 'exact'
default_lookups['exact'] = Exact


class IExact(DjangoLookup):
    lookup_name = 'iexact'
default_lookups['iexact'] = IExact


class Contains(DjangoLookup):
    lookup_name = 'contains'
default_lookups['contains'] = Contains


class IContains(DjangoLookup):
    lookup_name = 'icontains'
default_lookups['icontains'] = IContains


class GreaterThan(DjangoLookup):
    lookup_name = 'gt'
default_lookups['gt'] = GreaterThan


class GreaterThanOrEqual(DjangoLookup):
    lookup_name = 'gte'
default_lookups['gte'] = GreaterThanOrEqual


class LessThan(DjangoLookup):
    lookup_name = 'lt'
default_lookups['lt'] = LessThan


class LessThanOrEqual(DjangoLookup):
    lookup_name = 'lte'
default_lookups['lte'] = LessThanOrEqual


class In(DjangoLookup):
    lookup_name = 'in'

    def get_db_prep_lookup(self, value, connection):
        params = self.lhs.output_type.get_db_prep_lookup(
            self.lookup_name, value, connection, prepared=True)
        if not params:
            # TODO: check why this leads to circular import
            from django.db.models.sql.datastructures import EmptyResultSet
            raise EmptyResultSet
        placeholder = '(' + ', '.join('%s' for p in params) + ')'
        return (placeholder, params)

    def get_rhs_op(self, connection, rhs):
        return 'IN %s' % rhs
default_lookups['in'] = In


class StartsWith(DjangoLookup):
    lookup_name = 'startswith'
default_lookups['startswith'] = StartsWith


class IStartsWith(DjangoLookup):
    lookup_name = 'istartswith'
default_lookups['istartswith'] = IStartsWith


class EndsWith(DjangoLookup):
    lookup_name = 'endswith'
default_lookups['endswith'] = EndsWith


class IEndsWith(DjangoLookup):
    lookup_name = 'iendswith'
default_lookups['iendswith'] = IEndsWith


class Between(DjangoLookup):
    def get_rhs_op(self, connection, rhs):
        return "BETWEEN %s AND %s" % (rhs, rhs)


class Year(Between):
    lookup_name = 'year'
default_lookups['year'] = Year


class Range(Between):
    lookup_name = 'range'
default_lookups['range'] = Range


class DateLookup(DjangoLookup):

    def process_lhs(self, qn, connection):
        lhs, params = super(DateLookup, self).process_lhs(qn, connection)
        tzname = timezone.get_current_timezone_name() if settings.USE_TZ else None
        sql, tz_params = connection.ops.datetime_extract_sql(self.extract_type, lhs, tzname)
        return connection.ops.lookup_cast(self.lookup_name) % sql, tz_params

    def get_rhs_op(self, connection, rhs):
        return '= %s' % rhs


class Month(DateLookup):
    lookup_name = 'month'
    extract_type = 'month'
default_lookups['month'] = Month


class Day(DateLookup):
    lookup_name = 'day'
    extract_type = 'day'
default_lookups['day'] = Day


class WeekDay(DateLookup):
    lookup_name = 'week_day'
    extract_type = 'week_day'
default_lookups['week_day'] = WeekDay


class Hour(DateLookup):
    lookup_name = 'hour'
    extract_type = 'hour'
default_lookups['hour'] = Hour


class Minute(DateLookup):
    lookup_name = 'minute'
    extract_type = 'minute'
default_lookups['minute'] = Minute


class Second(DateLookup):
    lookup_name = 'second'
    extract_type = 'second'
default_lookups['second'] = Second


class IsNull(DjangoLookup):
    lookup_name = 'isnull'

    def as_sql(self, qn, connection):
        sql, params = qn.compile(self.lhs)
        if self.rhs:
            return "%s IS NULL" % sql, params
        else:
            return "%s IS NOT NULL" % sql, params
default_lookups['isnull'] = IsNull


class Search(DjangoLookup):
    lookup_name = 'search'
default_lookups['search'] = Search


class Regex(DjangoLookup):
    lookup_name = 'regex'
default_lookups['regex'] = Regex


class IRegex(DjangoLookup):
    lookup_name = 'iregex'
default_lookups['iregex'] = IRegex
