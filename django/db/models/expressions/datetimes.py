from django.conf import settings
from django.db.models.expressions import Func
from django.db.models.fields import (
    DateField, DateTimeField, IntegerField, TimeField,
)
from django.db.models.query_utils import RegisterLookupMixin
from django.utils import timezone
from django.utils.functional import cached_property


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


class DateExtract(Transform):
    def __init__(self, *expressions, **extra):
        if not hasattr(self, 'lookup_name'):
            self.lookup_name = extra.pop('lookup_name')

        super(DateExtract, self).__init__(*expressions, **extra)

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


class DateExtractFactory(object):
    _cache = {}

    def extract(self, lookup_name):
        class_name = '%sExtract' % lookup_name.title().replace('_', '')
        if not self._cache.has_key(class_name):
            self._cache[class_name] = type(class_name, (DateExtract,), {'lookup_name': lookup_name})

        return self._cache[class_name]


class DateTimeDateExtract(Transform):
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


extract_factory = DateExtractFactory()

YearExtract = extract_factory.extract('year')
MonthExtract = extract_factory.extract('month')
DayExtract = extract_factory.extract('day')
WeekDayExtract = extract_factory.extract('week_day')
HourExtract = extract_factory.extract('hour')
MinuteExtract = extract_factory.extract('minute')
SecondExtract = extract_factory.extract('second')
