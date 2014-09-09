from copy import copy
from itertools import repeat
import inspect

from django.conf import settings
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.six.moves import xrange


class RegisterLookupMixin(object):
    def _get_lookup(self, lookup_name):
        try:
            return self.class_lookups[lookup_name]
        except KeyError:
            # To allow for inheritance, check parent class' class_lookups.
            for parent in inspect.getmro(self.__class__):
                if 'class_lookups' not in parent.__dict__:
                    continue
                if lookup_name in parent.class_lookups:
                    return parent.class_lookups[lookup_name]
        except AttributeError:
            # This class didn't have any class_lookups
            pass
        return None

    def get_lookup(self, lookup_name):
        found = self._get_lookup(lookup_name)
        if found is None and hasattr(self, 'output_field'):
            return self.output_field.get_lookup(lookup_name)
        if found is not None and not issubclass(found, Lookup):
            return None
        return found

    def get_transform(self, lookup_name):
        found = self._get_lookup(lookup_name)
        if found is None and hasattr(self, 'output_field'):
            return self.output_field.get_transform(lookup_name)
        if found is not None and not issubclass(found, Transform):
            return None
        return found

    @classmethod
    def register_lookup(cls, lookup):
        if 'class_lookups' not in cls.__dict__:
            cls.class_lookups = {}
        cls.class_lookups[lookup.lookup_name] = lookup

    @classmethod
    def _unregister_lookup(cls, lookup):
        """
        Removes given lookup from cls lookups. Meant to be used in
        tests only.
        """
        del cls.class_lookups[lookup.lookup_name]


class Transform(RegisterLookupMixin):
    def __init__(self, lhs, lookups):
        self.lhs = lhs
        self.init_lookups = lookups[:]

    def as_sql(self, qn, connection):
        raise NotImplementedError

    @cached_property
    def output_field(self):
        return self.lhs.output_field

    def relabeled_clone(self, relabels):
        return self.__class__(self.lhs.relabeled_clone(relabels))

    def get_group_by_cols(self):
        return self.lhs.get_group_by_cols()


class Lookup(RegisterLookupMixin):
    lookup_name = None

    def __init__(self, lhs, rhs):
        self.lhs, self.rhs = lhs, rhs
        self.rhs = self.get_prep_lookup()

    def get_prep_lookup(self):
        return self.lhs.output_field.get_prep_lookup(self.lookup_name, self.rhs)

    def get_db_prep_lookup(self, value, connection):
        return (
            '%s', self.lhs.output_field.get_db_prep_lookup(
                self.lookup_name, value, connection, prepared=True))

    def process_lhs(self, qn, connection, lhs=None):
        lhs = lhs or self.lhs
        return qn.compile(lhs)

    def process_rhs(self, qn, connection):
        value = self.rhs
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

    def as_sql(self, qn, connection):
        raise NotImplementedError


class BuiltinLookup(Lookup):
    def process_lhs(self, qn, connection, lhs=None):
        lhs_sql, params = super(BuiltinLookup, self).process_lhs(
            qn, connection, lhs)
        field_internal_type = self.lhs.output_field.get_internal_type()
        db_type = self.lhs.output_field.db_type(connection=connection)
        lhs_sql = connection.ops.field_cast_sql(
            db_type, field_internal_type) % lhs_sql
        lhs_sql = connection.ops.lookup_cast(self.lookup_name) % lhs_sql
        return lhs_sql, params

    def as_sql(self, qn, connection):
        lhs_sql, params = self.process_lhs(qn, connection)
        rhs_sql, rhs_params = self.process_rhs(qn, connection)
        params.extend(rhs_params)
        rhs_sql = self.get_rhs_op(connection, rhs_sql)
        return '%s %s' % (lhs_sql, rhs_sql), params

    def get_rhs_op(self, connection, rhs):
        return connection.operators[self.lookup_name] % rhs


default_lookups = {}


class Exact(BuiltinLookup):
    lookup_name = 'exact'
default_lookups['exact'] = Exact


class IExact(BuiltinLookup):
    lookup_name = 'iexact'
default_lookups['iexact'] = IExact


class Contains(BuiltinLookup):
    lookup_name = 'contains'
default_lookups['contains'] = Contains


class IContains(BuiltinLookup):
    lookup_name = 'icontains'
default_lookups['icontains'] = IContains


class GreaterThan(BuiltinLookup):
    lookup_name = 'gt'
default_lookups['gt'] = GreaterThan


class GreaterThanOrEqual(BuiltinLookup):
    lookup_name = 'gte'
default_lookups['gte'] = GreaterThanOrEqual


class LessThan(BuiltinLookup):
    lookup_name = 'lt'
default_lookups['lt'] = LessThan


class LessThanOrEqual(BuiltinLookup):
    lookup_name = 'lte'
default_lookups['lte'] = LessThanOrEqual


class In(BuiltinLookup):
    lookup_name = 'in'

    def get_db_prep_lookup(self, value, connection):
        params = self.lhs.output_field.get_db_prep_lookup(
            self.lookup_name, value, connection, prepared=True)
        if not params:
            # TODO: check why this leads to circular import
            from django.db.models.sql.datastructures import EmptyResultSet
            raise EmptyResultSet
        placeholder = '(' + ', '.join('%s' for p in params) + ')'
        return (placeholder, params)

    def get_rhs_op(self, connection, rhs):
        return 'IN %s' % rhs

    def as_sql(self, qn, connection):
        max_in_list_size = connection.ops.max_in_list_size()
        if self.rhs_is_direct_value() and (max_in_list_size and
                                           len(self.rhs) > max_in_list_size):
            rhs, rhs_params = self.process_rhs(qn, connection)
            lhs, lhs_params = self.process_lhs(qn, connection)
            in_clause_elements = ['(']
            params = []
            for offset in xrange(0, len(rhs_params), max_in_list_size):
                if offset > 0:
                    in_clause_elements.append(' OR ')
                in_clause_elements.append('%s IN (' % lhs)
                params.extend(lhs_params)
                group_size = min(len(rhs_params) - offset, max_in_list_size)
                param_group = ', '.join(repeat('%s', group_size))
                in_clause_elements.append(param_group)
                in_clause_elements.append(')')
                params.extend(rhs_params[offset: offset + max_in_list_size])
            in_clause_elements.append(')')
            return ''.join(in_clause_elements), params
        else:
            return super(In, self).as_sql(qn, connection)


default_lookups['in'] = In


class PatternLookup(BuiltinLookup):
    def get_rhs_op(self, connection, rhs):
        # Assume we are in startswith. We need to produce SQL like:
        #     col LIKE %s, ['thevalue%']
        # For python values we can (and should) do that directly in Python,
        # but if the value is for example reference to other column, then
        # we need to add the % pattern match to the lookup by something like
        #     col LIKE othercol || '%%'
        # So, for Python values we don't need any special pattern, but for
        # SQL reference values we need the correct pattern added.
        value = self.rhs
        if (hasattr(value, 'get_compiler') or hasattr(value, 'as_sql')
                or hasattr(value, '_as_sql')):
            return connection.pattern_ops[self.lookup_name] % rhs
        else:
            return super(PatternLookup, self).get_rhs_op(connection, rhs)


class StartsWith(PatternLookup):
    lookup_name = 'startswith'
default_lookups['startswith'] = StartsWith


class IStartsWith(PatternLookup):
    lookup_name = 'istartswith'
default_lookups['istartswith'] = IStartsWith


class EndsWith(BuiltinLookup):
    lookup_name = 'endswith'
default_lookups['endswith'] = EndsWith


class IEndsWith(BuiltinLookup):
    lookup_name = 'iendswith'
default_lookups['iendswith'] = IEndsWith


class Between(BuiltinLookup):
    def get_rhs_op(self, connection, rhs):
        return "BETWEEN %s AND %s" % (rhs, rhs)


class Year(Between):
    lookup_name = 'year'
default_lookups['year'] = Year


class Range(Between):
    lookup_name = 'range'
default_lookups['range'] = Range


class DateLookup(BuiltinLookup):
    def process_lhs(self, qn, connection, lhs=None):
        from django.db.models import DateTimeField
        lhs, params = super(DateLookup, self).process_lhs(qn, connection, lhs)
        if isinstance(self.lhs.output_field, DateTimeField):
            tzname = timezone.get_current_timezone_name() if settings.USE_TZ else None
            sql, tz_params = connection.ops.datetime_extract_sql(self.extract_type, lhs, tzname)
            return connection.ops.lookup_cast(self.lookup_name) % sql, tz_params
        else:
            return connection.ops.date_extract_sql(self.lookup_name, lhs), []

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


class IsNull(BuiltinLookup):
    lookup_name = 'isnull'

    def as_sql(self, qn, connection):
        sql, params = qn.compile(self.lhs)
        if self.rhs:
            return "%s IS NULL" % sql, params
        else:
            return "%s IS NOT NULL" % sql, params
default_lookups['isnull'] = IsNull


class Search(BuiltinLookup):
    lookup_name = 'search'

    def as_sql(self, qn, connection):
        lhs, lhs_params = self.process_lhs(qn, connection)
        rhs, rhs_params = self.process_rhs(qn, connection)
        sql_template = connection.ops.fulltext_search_sql(field_name=lhs)
        return sql_template, lhs_params + rhs_params

default_lookups['search'] = Search


class Regex(BuiltinLookup):
    lookup_name = 'regex'

    def as_sql(self, qn, connection):
        if self.lookup_name in connection.operators:
            return super(Regex, self).as_sql(qn, connection)
        else:
            lhs, lhs_params = self.process_lhs(qn, connection)
            rhs, rhs_params = self.process_rhs(qn, connection)
            sql_template = connection.ops.regex_lookup(self.lookup_name)
            return sql_template % (lhs, rhs), lhs_params + rhs_params
default_lookups['regex'] = Regex


class IRegex(Regex):
    lookup_name = 'iregex'
default_lookups['iregex'] = IRegex
