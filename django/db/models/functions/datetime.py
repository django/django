from datetime import datetime

from django.conf import settings
from django.db.models import (
    DateField, DateTimeField, IntegerField, TimeField, Transform,
)
from django.db.models.lookups import (
    YearExact, YearGt, YearGte, YearLt, YearLte,
)
from django.utils import timezone
from django.utils.functional import cached_property


class TimezoneMixin:
    tzinfo = None

    def get_tzname(self):
        # Timezone conversions must happen to the input datetime *before*
        # applying a function. 2015-12-31 23:00:00 -02:00 is stored in the
        # database as 2016-01-01 01:00:00 +00:00. Any results should be
        # based on the input datetime not the stored datetime.
        tzname = None
        if settings.USE_TZ:
            if self.tzinfo is None:
                tzname = timezone.get_current_timezone_name()
            else:
                tzname = timezone._get_timezone_name(self.tzinfo)
        return tzname


class Extract(TimezoneMixin, Transform):
    lookup_name = None

    def __init__(self, expression, lookup_name=None, tzinfo=None, **extra):
        if self.lookup_name is None:
            self.lookup_name = lookup_name
        if self.lookup_name is None:
            raise ValueError('lookup_name must be provided')
        self.tzinfo = tzinfo
        super(Extract, self).__init__(expression, **extra)

    def as_sql(self, compiler, connection):
        sql, params = compiler.compile(self.lhs)
        lhs_output_field = self.lhs.output_field
        if isinstance(lhs_output_field, DateTimeField):
            tzname = self.get_tzname()
            sql, tz_params = connection.ops.datetime_extract_sql(self.lookup_name, sql, tzname)
            params.extend(tz_params)
        elif isinstance(lhs_output_field, DateField):
            sql = connection.ops.date_extract_sql(self.lookup_name, sql)
        elif isinstance(lhs_output_field, TimeField):
            sql = connection.ops.time_extract_sql(self.lookup_name, sql)
        else:
            # resolve_expression has already validated the output_field so this
            # assert should never be hit.
            assert False, "Tried to Extract from an invalid type."
        return sql, params

    def resolve_expression(self, query=None, allow_joins=True, reuse=None, summarize=False, for_save=False):
        copy = super(Extract, self).resolve_expression(query, allow_joins, reuse, summarize, for_save)
        field = copy.lhs.output_field
        if not isinstance(field, (DateField, DateTimeField, TimeField)):
            raise ValueError('Extract input expression must be DateField, DateTimeField, or TimeField.')
        # Passing dates to functions expecting datetimes is most likely a mistake.
        if type(field) == DateField and copy.lookup_name in ('hour', 'minute', 'second'):
            raise ValueError(
                "Cannot extract time component '%s' from DateField '%s'. " % (copy.lookup_name, field.name)
            )
        return copy

    @cached_property
    def output_field(self):
        return IntegerField()


class ExtractYear(Extract):
    lookup_name = 'year'


class ExtractMonth(Extract):
    lookup_name = 'month'


class ExtractDay(Extract):
    lookup_name = 'day'


class ExtractWeek(Extract):
    """
    Return 1-52 or 53, based on ISO-8601, i.e., Monday is the first of the
    week.
    """
    lookup_name = 'week'


class ExtractWeekDay(Extract):
    """
    Return Sunday=1 through Saturday=7.

    To replicate this in Python: (mydatetime.isoweekday() % 7) + 1
    """
    lookup_name = 'week_day'


class ExtractHour(Extract):
    lookup_name = 'hour'


class ExtractMinute(Extract):
    lookup_name = 'minute'


class ExtractSecond(Extract):
    lookup_name = 'second'


DateField.register_lookup(ExtractYear)
DateField.register_lookup(ExtractMonth)
DateField.register_lookup(ExtractDay)
DateField.register_lookup(ExtractWeekDay)
DateField.register_lookup(ExtractWeek)

TimeField.register_lookup(ExtractHour)
TimeField.register_lookup(ExtractMinute)
TimeField.register_lookup(ExtractSecond)

DateTimeField.register_lookup(ExtractHour)
DateTimeField.register_lookup(ExtractMinute)
DateTimeField.register_lookup(ExtractSecond)

ExtractYear.register_lookup(YearExact)
ExtractYear.register_lookup(YearGt)
ExtractYear.register_lookup(YearGte)
ExtractYear.register_lookup(YearLt)
ExtractYear.register_lookup(YearLte)


class TruncBase(TimezoneMixin, Transform):
    arity = 1
    kind = None
    tzinfo = None

    def __init__(self, expression, output_field=None, tzinfo=None, **extra):
        self.tzinfo = tzinfo
        super(TruncBase, self).__init__(expression, output_field=output_field, **extra)

    def as_sql(self, compiler, connection):
        inner_sql, inner_params = compiler.compile(self.lhs)
        # Escape any params because trunc_sql will format the string.
        inner_sql = inner_sql.replace('%s', '%%s')
        if isinstance(self.output_field, DateTimeField):
            tzname = self.get_tzname()
            sql, params = connection.ops.datetime_trunc_sql(self.kind, inner_sql, tzname)
        elif isinstance(self.output_field, DateField):
            sql = connection.ops.date_trunc_sql(self.kind, inner_sql)
            params = []
        elif isinstance(self.output_field, TimeField):
            sql = connection.ops.time_trunc_sql(self.kind, inner_sql)
            params = []
        else:
            raise ValueError('Trunc only valid on DateField, TimeField, or DateTimeField.')
        return sql, inner_params + params

    def resolve_expression(self, query=None, allow_joins=True, reuse=None, summarize=False, for_save=False):
        copy = super(TruncBase, self).resolve_expression(query, allow_joins, reuse, summarize, for_save)
        field = copy.lhs.output_field
        # DateTimeField is a subclass of DateField so this works for both.
        assert isinstance(field, (DateField, TimeField)), (
            "%r isn't a DateField, TimeField, or DateTimeField." % field.name
        )
        # If self.output_field was None, then accessing the field will trigger
        # the resolver to assign it to self.lhs.output_field.
        if not isinstance(copy.output_field, (DateField, DateTimeField, TimeField)):
            raise ValueError('output_field must be either DateField, TimeField, or DateTimeField')
        # Passing dates or times to functions expecting datetimes is most
        # likely a mistake.
        output_field = copy.output_field
        explicit_output_field = field.__class__ != copy.output_field.__class__
        if type(field) == DateField and (
                isinstance(output_field, DateTimeField) or copy.kind in ('hour', 'minute', 'second', 'time')):
            raise ValueError("Cannot truncate DateField '%s' to %s. " % (
                field.name, output_field.__class__.__name__ if explicit_output_field else 'DateTimeField'
            ))
        elif isinstance(field, TimeField) and (
                isinstance(output_field, DateTimeField) or copy.kind in ('year', 'month', 'day', 'date')):
            raise ValueError("Cannot truncate TimeField '%s' to %s. " % (
                field.name, output_field.__class__.__name__ if explicit_output_field else 'DateTimeField'
            ))
        return copy

    def convert_value(self, value, expression, connection, context):
        if isinstance(self.output_field, DateTimeField):
            if settings.USE_TZ:
                if value is None:
                    raise ValueError(
                        "Database returned an invalid datetime value. "
                        "Are time zone definitions for your database installed?"
                    )
                value = value.replace(tzinfo=None)
                value = timezone.make_aware(value, self.tzinfo)
        elif isinstance(value, datetime):
            if isinstance(self.output_field, DateField):
                value = value.date()
            elif isinstance(self.output_field, TimeField):
                value = value.time()
        return value


class Trunc(TruncBase):

    def __init__(self, expression, kind, output_field=None, tzinfo=None, **extra):
        self.kind = kind
        super(Trunc, self).__init__(expression, output_field=output_field, tzinfo=tzinfo, **extra)


class TruncYear(TruncBase):
    kind = 'year'


class TruncMonth(TruncBase):
    kind = 'month'


class TruncDay(TruncBase):
    kind = 'day'


class TruncDate(TruncBase):
    kind = 'date'
    lookup_name = 'date'

    @cached_property
    def output_field(self):
        return DateField()

    def as_sql(self, compiler, connection):
        # Cast to date rather than truncate to date.
        lhs, lhs_params = compiler.compile(self.lhs)
        tzname = timezone.get_current_timezone_name() if settings.USE_TZ else None
        sql, tz_params = connection.ops.datetime_cast_date_sql(lhs, tzname)
        lhs_params.extend(tz_params)
        return sql, lhs_params


class TruncTime(TruncBase):
    kind = 'time'
    lookup_name = 'time'

    @cached_property
    def output_field(self):
        return TimeField()

    def as_sql(self, compiler, connection):
        # Cast to date rather than truncate to date.
        lhs, lhs_params = compiler.compile(self.lhs)
        tzname = timezone.get_current_timezone_name() if settings.USE_TZ else None
        sql, tz_params = connection.ops.datetime_cast_time_sql(lhs, tzname)
        lhs_params.extend(tz_params)
        return sql, lhs_params


class TruncHour(TruncBase):
    kind = 'hour'


class TruncMinute(TruncBase):
    kind = 'minute'


class TruncSecond(TruncBase):
    kind = 'second'


DateTimeField.register_lookup(TruncDate)
DateTimeField.register_lookup(TruncTime)
