import inspect
from copy import copy

from django.conf import settings
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.six.moves import range

from .query_utils import QueryWrapper


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
        return lookup

    @classmethod
    def _unregister_lookup(cls, lookup):
        """
        Removes given lookup from cls lookups. Meant to be used in
        tests only.
        """
        del cls.class_lookups[lookup.lookup_name]


class Transform(RegisterLookupMixin):

    bilateral = False

    def __init__(self, lhs, lookups):
        self.lhs = lhs
        self.init_lookups = lookups[:]

    def as_sql(self, compiler, connection):
        raise NotImplementedError

    @cached_property
    def output_field(self):
        return self.lhs.output_field

    def relabeled_clone(self, relabels):
        return self.__class__(self.lhs.relabeled_clone(relabels))

    def get_group_by_cols(self):
        return self.lhs.get_group_by_cols()

    def get_bilateral_transforms(self):
        if hasattr(self.lhs, 'get_bilateral_transforms'):
            bilateral_transforms = self.lhs.get_bilateral_transforms()
        else:
            bilateral_transforms = []
        if self.bilateral:
            bilateral_transforms.append((self.__class__, self.init_lookups))
        return bilateral_transforms


class Lookup(RegisterLookupMixin):
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
        for transform, lookups in self.bilateral_transforms:
            value = transform(value, lookups)
        return value

    def batch_process_rhs(self, compiler, connection, rhs=None):
        if rhs is None:
            rhs = self.rhs
        if self.bilateral_transforms:
            sqls, sqls_params = [], []
            for p in rhs:
                value = QueryWrapper('%s',
                    [self.lhs.output_field.get_db_prep_value(p, connection)])
                value = self.apply_bilateral_transforms(value)
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
                value = QueryWrapper("%s",
                    [self.lhs.output_field.get_db_prep_value(value, connection)])
            value = self.apply_bilateral_transforms(value)
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


class BuiltinLookup(Lookup):
    def process_lhs(self, compiler, connection, lhs=None):
        lhs_sql, params = super(BuiltinLookup, self).process_lhs(
            compiler, connection, lhs)
        field_internal_type = self.lhs.output_field.get_internal_type()
        db_type = self.lhs.output_field.db_type(connection=connection)
        lhs_sql = connection.ops.field_cast_sql(
            db_type, field_internal_type) % lhs_sql
        lhs_sql = connection.ops.lookup_cast(self.lookup_name, field_internal_type) % lhs_sql
        return lhs_sql, params

    def as_sql(self, compiler, connection):
        lhs_sql, params = self.process_lhs(compiler, connection)
        rhs_sql, rhs_params = self.process_rhs(compiler, connection)
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

    def process_rhs(self, qn, connection):
        rhs, params = super(IExact, self).process_rhs(qn, connection)
        if params:
            params[0] = connection.ops.prep_for_iexact_query(params[0])
        return rhs, params


default_lookups['iexact'] = IExact


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
        if self.rhs_is_direct_value() and (max_in_list_size and
                                           len(self.rhs) > max_in_list_size):
            # This is a special case for Oracle which limits the number of elements
            # which can appear in an 'IN' clause.
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
        else:
            return super(In, self).as_sql(compiler, connection)


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


default_lookups['contains'] = Contains


class IContains(Contains):
    lookup_name = 'icontains'


default_lookups['icontains'] = IContains


class StartsWith(PatternLookup):
    lookup_name = 'startswith'

    def process_rhs(self, qn, connection):
        rhs, params = super(StartsWith, self).process_rhs(qn, connection)
        if params and not self.bilateral_transforms:
            params[0] = "%s%%" % connection.ops.prep_for_like_query(params[0])
        return rhs, params


default_lookups['startswith'] = StartsWith


class IStartsWith(PatternLookup):
    lookup_name = 'istartswith'

    def process_rhs(self, qn, connection):
        rhs, params = super(IStartsWith, self).process_rhs(qn, connection)
        if params and not self.bilateral_transforms:
            params[0] = "%s%%" % connection.ops.prep_for_like_query(params[0])
        return rhs, params


default_lookups['istartswith'] = IStartsWith


class EndsWith(PatternLookup):
    lookup_name = 'endswith'

    def process_rhs(self, qn, connection):
        rhs, params = super(EndsWith, self).process_rhs(qn, connection)
        if params and not self.bilateral_transforms:
            params[0] = "%%%s" % connection.ops.prep_for_like_query(params[0])
        return rhs, params


default_lookups['endswith'] = EndsWith


class IEndsWith(PatternLookup):
    lookup_name = 'iendswith'

    def process_rhs(self, qn, connection):
        rhs, params = super(IEndsWith, self).process_rhs(qn, connection)
        if params and not self.bilateral_transforms:
            params[0] = "%%%s" % connection.ops.prep_for_like_query(params[0])
        return rhs, params


default_lookups['iendswith'] = IEndsWith


class Between(BuiltinLookup):
    def get_rhs_op(self, connection, rhs):
        return "BETWEEN %s AND %s" % (rhs, rhs)


class Year(Between):
    lookup_name = 'year'
default_lookups['year'] = Year


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

default_lookups['range'] = Range


class DateLookup(BuiltinLookup):
    def process_lhs(self, compiler, connection, lhs=None):
        from django.db.models import DateTimeField
        lhs, params = super(DateLookup, self).process_lhs(compiler, connection, lhs)
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

    def as_sql(self, compiler, connection):
        sql, params = compiler.compile(self.lhs)
        if self.rhs:
            return "%s IS NULL" % sql, params
        else:
            return "%s IS NOT NULL" % sql, params
default_lookups['isnull'] = IsNull


class Search(BuiltinLookup):
    lookup_name = 'search'

    def as_sql(self, compiler, connection):
        lhs, lhs_params = self.process_lhs(compiler, connection)
        rhs, rhs_params = self.process_rhs(compiler, connection)
        sql_template = connection.ops.fulltext_search_sql(field_name=lhs)
        return sql_template, lhs_params + rhs_params

default_lookups['search'] = Search


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
default_lookups['regex'] = Regex


class IRegex(Regex):
    lookup_name = 'iregex'
default_lookups['iregex'] = IRegex
