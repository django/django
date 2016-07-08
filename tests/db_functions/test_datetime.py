from __future__ import unicode_literals

from datetime import datetime
from unittest import skipIf

from django.conf import settings
from django.db import connection
from django.db.models import DateField, DateTimeField, IntegerField
from django.db.models.functions import (
    Extract, ExtractDay, ExtractHour, ExtractMinute, ExtractMonth,
    ExtractSecond, ExtractWeekDay, ExtractYear, Trunc, TruncDate, TruncDay,
    TruncHour, TruncMinute, TruncMonth, TruncSecond, TruncYear,
)
from django.test import TestCase, override_settings
from django.utils import timezone

from .models import DTModel

try:
    import pytz
except ImportError:
    pytz = None


def microsecond_support(value):
    return value if connection.features.supports_microsecond_precision else value.replace(microsecond=0)


def truncate_to(value, kind, tzinfo=None):
    # Convert to target timezone before truncation
    if tzinfo is not None:
        value = value.astimezone(tzinfo)

    def truncate(value, kind):
        if kind == 'second':
            return value.replace(microsecond=0)
        if kind == 'minute':
            return value.replace(second=0, microsecond=0)
        if kind == 'hour':
            return value.replace(minute=0, second=0, microsecond=0)
        if kind == 'day':
            if isinstance(value, datetime):
                return value.replace(hour=0, minute=0, second=0, microsecond=0)
            return value
        if kind == 'month':
            if isinstance(value, datetime):
                return value.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            return value.replace(day=1)
        # otherwise, truncate to year
        if isinstance(value, datetime):
            return value.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        return value.replace(month=1, day=1)

    value = truncate(value, kind)
    if tzinfo is not None:
        # If there was a daylight saving transition, then reset the timezone.
        value = timezone.make_aware(value.replace(tzinfo=None), tzinfo)
    return value


@override_settings(USE_TZ=False)
class DateFunctionTests(TestCase):

    def create_model(self, start_datetime, end_datetime):
        return DTModel.objects.create(
            name=start_datetime.isoformat(),
            start_datetime=start_datetime, end_datetime=end_datetime,
            start_date=start_datetime.date(), end_date=end_datetime.date(),
            start_time=start_datetime.time(), end_time=end_datetime.time(),
            duration=(end_datetime - start_datetime),
        )

    def test_extract_year_exact_lookup(self):
        """
        Extract year uses a BETWEEN filter to compare the year to allow indexes
        to be used.
        """
        start_datetime = datetime(2015, 6, 15, 14, 10)
        end_datetime = datetime(2016, 6, 15, 14, 10)
        if settings.USE_TZ:
            start_datetime = timezone.make_aware(start_datetime, is_dst=False)
            end_datetime = timezone.make_aware(end_datetime, is_dst=False)
        self.create_model(start_datetime, end_datetime)
        self.create_model(end_datetime, start_datetime)

        qs = DTModel.objects.filter(start_datetime__year__exact=2015)
        self.assertEqual(qs.count(), 1)
        query_string = str(qs.query).lower()
        self.assertEqual(query_string.count(' between '), 1)
        self.assertEqual(query_string.count('extract'), 0)

        # exact is implied and should be the same
        qs = DTModel.objects.filter(start_datetime__year=2015)
        self.assertEqual(qs.count(), 1)
        query_string = str(qs.query).lower()
        self.assertEqual(query_string.count(' between '), 1)
        self.assertEqual(query_string.count('extract'), 0)

        # date and datetime fields should behave the same
        qs = DTModel.objects.filter(start_date__year=2015)
        self.assertEqual(qs.count(), 1)
        query_string = str(qs.query).lower()
        self.assertEqual(query_string.count(' between '), 1)
        self.assertEqual(query_string.count('extract'), 0)

    def test_extract_year_greaterthan_lookup(self):
        start_datetime = datetime(2015, 6, 15, 14, 10)
        end_datetime = datetime(2016, 6, 15, 14, 10)
        if settings.USE_TZ:
            start_datetime = timezone.make_aware(start_datetime, is_dst=False)
            end_datetime = timezone.make_aware(end_datetime, is_dst=False)
        self.create_model(start_datetime, end_datetime)
        self.create_model(end_datetime, start_datetime)

        qs = DTModel.objects.filter(start_datetime__year__gt=2015)
        self.assertEqual(qs.count(), 1)
        self.assertEqual(str(qs.query).lower().count('extract'), 0)
        qs = DTModel.objects.filter(start_datetime__year__gte=2015)
        self.assertEqual(qs.count(), 2)
        self.assertEqual(str(qs.query).lower().count('extract'), 0)

    def test_extract_year_lessthan_lookup(self):
        start_datetime = datetime(2015, 6, 15, 14, 10)
        end_datetime = datetime(2016, 6, 15, 14, 10)
        if settings.USE_TZ:
            start_datetime = timezone.make_aware(start_datetime, is_dst=False)
            end_datetime = timezone.make_aware(end_datetime, is_dst=False)
        self.create_model(start_datetime, end_datetime)
        self.create_model(end_datetime, start_datetime)

        qs = DTModel.objects.filter(start_datetime__year__lt=2016)
        self.assertEqual(qs.count(), 1)
        self.assertEqual(str(qs.query).count('extract'), 0)
        qs = DTModel.objects.filter(start_datetime__year__lte=2016)
        self.assertEqual(qs.count(), 2)
        self.assertEqual(str(qs.query).count('extract'), 0)

    def test_extract_func(self):
        start_datetime = microsecond_support(datetime(2015, 6, 15, 14, 30, 50, 321))
        end_datetime = microsecond_support(datetime(2016, 6, 15, 14, 10, 50, 123))
        if settings.USE_TZ:
            start_datetime = timezone.make_aware(start_datetime, is_dst=False)
            end_datetime = timezone.make_aware(end_datetime, is_dst=False)
        self.create_model(start_datetime, end_datetime)
        self.create_model(end_datetime, start_datetime)

        with self.assertRaisesMessage(ValueError, 'lookup_name must be provided'):
            Extract('start_datetime')

        msg = 'Extract input expression must be DateField, DateTimeField, or TimeField.'
        with self.assertRaisesMessage(ValueError, msg):
            list(DTModel.objects.annotate(extracted=Extract('name', 'hour')))

        with self.assertRaisesMessage(
                ValueError, "Cannot extract time component 'second' from DateField 'start_date'."):
            list(DTModel.objects.annotate(extracted=Extract('start_date', 'second')))

        self.assertQuerysetEqual(
            DTModel.objects.annotate(extracted=Extract('start_datetime', 'year')).order_by('start_datetime'),
            [(start_datetime, start_datetime.year), (end_datetime, end_datetime.year)],
            lambda m: (m.start_datetime, m.extracted)
        )
        self.assertQuerysetEqual(
            DTModel.objects.annotate(extracted=Extract('start_datetime', 'month')).order_by('start_datetime'),
            [(start_datetime, start_datetime.month), (end_datetime, end_datetime.month)],
            lambda m: (m.start_datetime, m.extracted)
        )
        self.assertQuerysetEqual(
            DTModel.objects.annotate(extracted=Extract('start_datetime', 'day')).order_by('start_datetime'),
            [(start_datetime, start_datetime.day), (end_datetime, end_datetime.day)],
            lambda m: (m.start_datetime, m.extracted)
        )
        self.assertQuerysetEqual(
            DTModel.objects.annotate(extracted=Extract('start_datetime', 'week_day')).order_by('start_datetime'),
            [
                (start_datetime, (start_datetime.isoweekday() % 7) + 1),
                (end_datetime, (end_datetime.isoweekday() % 7) + 1)
            ],
            lambda m: (m.start_datetime, m.extracted)
        )
        self.assertQuerysetEqual(
            DTModel.objects.annotate(extracted=Extract('start_datetime', 'hour')).order_by('start_datetime'),
            [(start_datetime, start_datetime.hour), (end_datetime, end_datetime.hour)],
            lambda m: (m.start_datetime, m.extracted)
        )
        self.assertQuerysetEqual(
            DTModel.objects.annotate(extracted=Extract('start_datetime', 'minute')).order_by('start_datetime'),
            [(start_datetime, start_datetime.minute), (end_datetime, end_datetime.minute)],
            lambda m: (m.start_datetime, m.extracted)
        )
        self.assertQuerysetEqual(
            DTModel.objects.annotate(extracted=Extract('start_datetime', 'second')).order_by('start_datetime'),
            [(start_datetime, start_datetime.second), (end_datetime, end_datetime.second)],
            lambda m: (m.start_datetime, m.extracted)
        )
        self.assertEqual(DTModel.objects.filter(start_datetime__year=Extract('start_datetime', 'year')).count(), 2)
        self.assertEqual(DTModel.objects.filter(start_datetime__hour=Extract('start_datetime', 'hour')).count(), 2)
        self.assertEqual(DTModel.objects.filter(start_date__month=Extract('start_date', 'month')).count(), 2)
        self.assertEqual(DTModel.objects.filter(start_time__hour=Extract('start_time', 'hour')).count(), 2)

    def test_extract_year_func(self):
        start_datetime = microsecond_support(datetime(2015, 6, 15, 14, 30, 50, 321))
        end_datetime = microsecond_support(datetime(2016, 6, 15, 14, 10, 50, 123))
        if settings.USE_TZ:
            start_datetime = timezone.make_aware(start_datetime, is_dst=False)
            end_datetime = timezone.make_aware(end_datetime, is_dst=False)
        self.create_model(start_datetime, end_datetime)
        self.create_model(end_datetime, start_datetime)
        self.assertQuerysetEqual(
            DTModel.objects.annotate(extracted=ExtractYear('start_datetime')).order_by('start_datetime'),
            [(start_datetime, start_datetime.year), (end_datetime, end_datetime.year)],
            lambda m: (m.start_datetime, m.extracted)
        )
        self.assertQuerysetEqual(
            DTModel.objects.annotate(extracted=ExtractYear('start_date')).order_by('start_datetime'),
            [(start_datetime, start_datetime.year), (end_datetime, end_datetime.year)],
            lambda m: (m.start_datetime, m.extracted)
        )
        self.assertEqual(DTModel.objects.filter(start_datetime__year=ExtractYear('start_datetime')).count(), 2)

    def test_extract_month_func(self):
        start_datetime = microsecond_support(datetime(2015, 6, 15, 14, 30, 50, 321))
        end_datetime = microsecond_support(datetime(2016, 6, 15, 14, 10, 50, 123))
        if settings.USE_TZ:
            start_datetime = timezone.make_aware(start_datetime, is_dst=False)
            end_datetime = timezone.make_aware(end_datetime, is_dst=False)
        self.create_model(start_datetime, end_datetime)
        self.create_model(end_datetime, start_datetime)
        self.assertQuerysetEqual(
            DTModel.objects.annotate(extracted=ExtractMonth('start_datetime')).order_by('start_datetime'),
            [(start_datetime, start_datetime.month), (end_datetime, end_datetime.month)],
            lambda m: (m.start_datetime, m.extracted)
        )
        self.assertQuerysetEqual(
            DTModel.objects.annotate(extracted=ExtractMonth('start_date')).order_by('start_datetime'),
            [(start_datetime, start_datetime.month), (end_datetime, end_datetime.month)],
            lambda m: (m.start_datetime, m.extracted)
        )
        self.assertEqual(DTModel.objects.filter(start_datetime__month=ExtractMonth('start_datetime')).count(), 2)

    def test_extract_day_func(self):
        start_datetime = microsecond_support(datetime(2015, 6, 15, 14, 30, 50, 321))
        end_datetime = microsecond_support(datetime(2016, 6, 15, 14, 10, 50, 123))
        if settings.USE_TZ:
            start_datetime = timezone.make_aware(start_datetime, is_dst=False)
            end_datetime = timezone.make_aware(end_datetime, is_dst=False)
        self.create_model(start_datetime, end_datetime)
        self.create_model(end_datetime, start_datetime)
        self.assertQuerysetEqual(
            DTModel.objects.annotate(extracted=ExtractDay('start_datetime')).order_by('start_datetime'),
            [(start_datetime, start_datetime.day), (end_datetime, end_datetime.day)],
            lambda m: (m.start_datetime, m.extracted)
        )
        self.assertQuerysetEqual(
            DTModel.objects.annotate(extracted=ExtractDay('start_date')).order_by('start_datetime'),
            [(start_datetime, start_datetime.day), (end_datetime, end_datetime.day)],
            lambda m: (m.start_datetime, m.extracted)
        )
        self.assertEqual(DTModel.objects.filter(start_datetime__day=ExtractDay('start_datetime')).count(), 2)

    def test_extract_weekday_func(self):
        start_datetime = microsecond_support(datetime(2015, 6, 15, 14, 30, 50, 321))
        end_datetime = microsecond_support(datetime(2016, 6, 15, 14, 10, 50, 123))
        if settings.USE_TZ:
            start_datetime = timezone.make_aware(start_datetime, is_dst=False)
            end_datetime = timezone.make_aware(end_datetime, is_dst=False)
        self.create_model(start_datetime, end_datetime)
        self.create_model(end_datetime, start_datetime)
        self.assertQuerysetEqual(
            DTModel.objects.annotate(extracted=ExtractWeekDay('start_datetime')).order_by('start_datetime'),
            [
                (start_datetime, (start_datetime.isoweekday() % 7) + 1),
                (end_datetime, (end_datetime.isoweekday() % 7) + 1),
            ],
            lambda m: (m.start_datetime, m.extracted)
        )
        self.assertQuerysetEqual(
            DTModel.objects.annotate(extracted=ExtractWeekDay('start_date')).order_by('start_datetime'),
            [
                (start_datetime, (start_datetime.isoweekday() % 7) + 1),
                (end_datetime, (end_datetime.isoweekday() % 7) + 1),
            ],
            lambda m: (m.start_datetime, m.extracted)
        )
        self.assertEqual(DTModel.objects.filter(start_datetime__week_day=ExtractWeekDay('start_datetime')).count(), 2)

    def test_extract_hour_func(self):
        start_datetime = microsecond_support(datetime(2015, 6, 15, 14, 30, 50, 321))
        end_datetime = microsecond_support(datetime(2016, 6, 15, 14, 10, 50, 123))
        if settings.USE_TZ:
            start_datetime = timezone.make_aware(start_datetime, is_dst=False)
            end_datetime = timezone.make_aware(end_datetime, is_dst=False)
        self.create_model(start_datetime, end_datetime)
        self.create_model(end_datetime, start_datetime)
        self.assertQuerysetEqual(
            DTModel.objects.annotate(extracted=ExtractHour('start_datetime')).order_by('start_datetime'),
            [(start_datetime, start_datetime.hour), (end_datetime, end_datetime.hour)],
            lambda m: (m.start_datetime, m.extracted)
        )
        self.assertQuerysetEqual(
            DTModel.objects.annotate(extracted=ExtractHour('start_time')).order_by('start_datetime'),
            [(start_datetime, start_datetime.hour), (end_datetime, end_datetime.hour)],
            lambda m: (m.start_datetime, m.extracted)
        )
        self.assertEqual(DTModel.objects.filter(start_datetime__hour=ExtractHour('start_datetime')).count(), 2)

    def test_extract_minute_func(self):
        start_datetime = microsecond_support(datetime(2015, 6, 15, 14, 30, 50, 321))
        end_datetime = microsecond_support(datetime(2016, 6, 15, 14, 10, 50, 123))
        if settings.USE_TZ:
            start_datetime = timezone.make_aware(start_datetime, is_dst=False)
            end_datetime = timezone.make_aware(end_datetime, is_dst=False)
        self.create_model(start_datetime, end_datetime)
        self.create_model(end_datetime, start_datetime)
        self.assertQuerysetEqual(
            DTModel.objects.annotate(extracted=ExtractMinute('start_datetime')).order_by('start_datetime'),
            [(start_datetime, start_datetime.minute), (end_datetime, end_datetime.minute)],
            lambda m: (m.start_datetime, m.extracted)
        )
        self.assertQuerysetEqual(
            DTModel.objects.annotate(extracted=ExtractMinute('start_time')).order_by('start_datetime'),
            [(start_datetime, start_datetime.minute), (end_datetime, end_datetime.minute)],
            lambda m: (m.start_datetime, m.extracted)
        )
        self.assertEqual(DTModel.objects.filter(start_datetime__minute=ExtractMinute('start_datetime')).count(), 2)

    def test_extract_second_func(self):
        start_datetime = microsecond_support(datetime(2015, 6, 15, 14, 30, 50, 321))
        end_datetime = microsecond_support(datetime(2016, 6, 15, 14, 10, 50, 123))
        if settings.USE_TZ:
            start_datetime = timezone.make_aware(start_datetime, is_dst=False)
            end_datetime = timezone.make_aware(end_datetime, is_dst=False)
        self.create_model(start_datetime, end_datetime)
        self.create_model(end_datetime, start_datetime)
        self.assertQuerysetEqual(
            DTModel.objects.annotate(extracted=ExtractSecond('start_datetime')).order_by('start_datetime'),
            [(start_datetime, start_datetime.second), (end_datetime, end_datetime.second)],
            lambda m: (m.start_datetime, m.extracted)
        )
        self.assertQuerysetEqual(
            DTModel.objects.annotate(extracted=ExtractSecond('start_time')).order_by('start_datetime'),
            [(start_datetime, start_datetime.second), (end_datetime, end_datetime.second)],
            lambda m: (m.start_datetime, m.extracted)
        )
        self.assertEqual(DTModel.objects.filter(start_datetime__second=ExtractSecond('start_datetime')).count(), 2)

    def test_trunc_func(self):
        start_datetime = microsecond_support(datetime(2015, 6, 15, 14, 30, 50, 321))
        end_datetime = microsecond_support(datetime(2016, 6, 15, 14, 10, 50, 123))
        if settings.USE_TZ:
            start_datetime = timezone.make_aware(start_datetime, is_dst=False)
            end_datetime = timezone.make_aware(end_datetime, is_dst=False)
        self.create_model(start_datetime, end_datetime)
        self.create_model(end_datetime, start_datetime)

        with self.assertRaisesMessage(ValueError, 'output_field must be either DateField or DateTimeField'):
            list(DTModel.objects.annotate(truncated=Trunc('start_datetime', 'year', output_field=IntegerField())))

        with self.assertRaisesMessage(AssertionError, "'name' isn't a DateField or DateTimeField."):
            list(DTModel.objects.annotate(truncated=Trunc('name', 'year', output_field=DateTimeField())))

        with self.assertRaisesMessage(ValueError, "Cannot truncate DateField 'start_date' to DateTimeField"):
            list(DTModel.objects.annotate(truncated=Trunc('start_date', 'second')))

        with self.assertRaisesMessage(ValueError, "Cannot truncate DateField 'start_date' to DateTimeField"):
            list(DTModel.objects.annotate(truncated=Trunc('start_date', 'month', output_field=DateTimeField())))

        def test_datetime_kind(kind):
            self.assertQuerysetEqual(
                DTModel.objects.annotate(
                    truncated=Trunc('start_datetime', kind, output_field=DateTimeField())
                ).order_by('start_datetime'),
                [
                    (start_datetime, truncate_to(start_datetime, kind)),
                    (end_datetime, truncate_to(end_datetime, kind))
                ],
                lambda m: (m.start_datetime, m.truncated)
            )

        def test_date_kind(kind):
            self.assertQuerysetEqual(
                DTModel.objects.annotate(
                    truncated=Trunc('start_date', kind, output_field=DateField())
                ).order_by('start_datetime'),
                [
                    (start_datetime, truncate_to(start_datetime.date(), kind)),
                    (end_datetime, truncate_to(end_datetime.date(), kind))
                ],
                lambda m: (m.start_datetime, m.truncated)
            )

        test_date_kind('year')
        test_date_kind('month')
        test_date_kind('day')
        test_datetime_kind('year')
        test_datetime_kind('month')
        test_datetime_kind('day')
        test_datetime_kind('hour')
        test_datetime_kind('minute')
        test_datetime_kind('second')

        qs = DTModel.objects.filter(start_datetime__date=Trunc('start_datetime', 'day', output_field=DateField()))
        self.assertEqual(qs.count(), 2)

    def test_trunc_year_func(self):
        start_datetime = microsecond_support(datetime(2015, 6, 15, 14, 30, 50, 321))
        end_datetime = truncate_to(microsecond_support(datetime(2016, 6, 15, 14, 10, 50, 123)), 'year')
        if settings.USE_TZ:
            start_datetime = timezone.make_aware(start_datetime, is_dst=False)
            end_datetime = timezone.make_aware(end_datetime, is_dst=False)
        self.create_model(start_datetime, end_datetime)
        self.create_model(end_datetime, start_datetime)
        self.assertQuerysetEqual(
            DTModel.objects.annotate(extracted=TruncYear('start_datetime')).order_by('start_datetime'),
            [
                (start_datetime, truncate_to(start_datetime, 'year')),
                (end_datetime, truncate_to(end_datetime, 'year')),
            ],
            lambda m: (m.start_datetime, m.extracted)
        )
        self.assertQuerysetEqual(
            DTModel.objects.annotate(extracted=TruncYear('start_date')).order_by('start_datetime'),
            [
                (start_datetime, truncate_to(start_datetime.date(), 'year')),
                (end_datetime, truncate_to(end_datetime.date(), 'year')),
            ],
            lambda m: (m.start_datetime, m.extracted)
        )
        self.assertEqual(DTModel.objects.filter(start_datetime=TruncYear('start_datetime')).count(), 1)

    def test_trunc_month_func(self):
        start_datetime = microsecond_support(datetime(2015, 6, 15, 14, 30, 50, 321))
        end_datetime = truncate_to(microsecond_support(datetime(2016, 6, 15, 14, 10, 50, 123)), 'month')
        if settings.USE_TZ:
            start_datetime = timezone.make_aware(start_datetime, is_dst=False)
            end_datetime = timezone.make_aware(end_datetime, is_dst=False)
        self.create_model(start_datetime, end_datetime)
        self.create_model(end_datetime, start_datetime)
        self.assertQuerysetEqual(
            DTModel.objects.annotate(extracted=TruncMonth('start_datetime')).order_by('start_datetime'),
            [
                (start_datetime, truncate_to(start_datetime, 'month')),
                (end_datetime, truncate_to(end_datetime, 'month')),
            ],
            lambda m: (m.start_datetime, m.extracted)
        )
        self.assertQuerysetEqual(
            DTModel.objects.annotate(extracted=TruncMonth('start_date')).order_by('start_datetime'),
            [
                (start_datetime, truncate_to(start_datetime.date(), 'month')),
                (end_datetime, truncate_to(end_datetime.date(), 'month')),
            ],
            lambda m: (m.start_datetime, m.extracted)
        )
        self.assertEqual(DTModel.objects.filter(start_datetime=TruncMonth('start_datetime')).count(), 1)

    def test_trunc_date_func(self):
        start_datetime = microsecond_support(datetime(2015, 6, 15, 14, 30, 50, 321))
        end_datetime = microsecond_support(datetime(2016, 6, 15, 14, 10, 50, 123))
        if settings.USE_TZ:
            start_datetime = timezone.make_aware(start_datetime, is_dst=False)
            end_datetime = timezone.make_aware(end_datetime, is_dst=False)
        self.create_model(start_datetime, end_datetime)
        self.create_model(end_datetime, start_datetime)
        self.assertQuerysetEqual(
            DTModel.objects.annotate(extracted=TruncDate('start_datetime')).order_by('start_datetime'),
            [
                (start_datetime, start_datetime.date()),
                (end_datetime, end_datetime.date()),
            ],
            lambda m: (m.start_datetime, m.extracted)
        )
        self.assertEqual(DTModel.objects.filter(start_datetime__date=TruncDate('start_datetime')).count(), 2)

    def test_trunc_day_func(self):
        start_datetime = microsecond_support(datetime(2015, 6, 15, 14, 30, 50, 321))
        end_datetime = truncate_to(microsecond_support(datetime(2016, 6, 15, 14, 10, 50, 123)), 'day')
        if settings.USE_TZ:
            start_datetime = timezone.make_aware(start_datetime, is_dst=False)
            end_datetime = timezone.make_aware(end_datetime, is_dst=False)
        self.create_model(start_datetime, end_datetime)
        self.create_model(end_datetime, start_datetime)
        self.assertQuerysetEqual(
            DTModel.objects.annotate(extracted=TruncDay('start_datetime')).order_by('start_datetime'),
            [
                (start_datetime, truncate_to(start_datetime, 'day')),
                (end_datetime, truncate_to(end_datetime, 'day')),
            ],
            lambda m: (m.start_datetime, m.extracted)
        )
        self.assertEqual(DTModel.objects.filter(start_datetime=TruncDay('start_datetime')).count(), 1)

    def test_trunc_hour_func(self):
        start_datetime = microsecond_support(datetime(2015, 6, 15, 14, 30, 50, 321))
        end_datetime = truncate_to(microsecond_support(datetime(2016, 6, 15, 14, 10, 50, 123)), 'hour')
        if settings.USE_TZ:
            start_datetime = timezone.make_aware(start_datetime, is_dst=False)
            end_datetime = timezone.make_aware(end_datetime, is_dst=False)
        self.create_model(start_datetime, end_datetime)
        self.create_model(end_datetime, start_datetime)
        self.assertQuerysetEqual(
            DTModel.objects.annotate(extracted=TruncHour('start_datetime')).order_by('start_datetime'),
            [
                (start_datetime, truncate_to(start_datetime, 'hour')),
                (end_datetime, truncate_to(end_datetime, 'hour')),
            ],
            lambda m: (m.start_datetime, m.extracted)
        )
        self.assertEqual(DTModel.objects.filter(start_datetime=TruncHour('start_datetime')).count(), 1)

        with self.assertRaisesMessage(ValueError, "Cannot truncate DateField 'start_date' to DateTimeField"):
            list(DTModel.objects.annotate(truncated=TruncHour('start_date')))

        with self.assertRaisesMessage(ValueError, "Cannot truncate DateField 'start_date' to DateTimeField"):
            list(DTModel.objects.annotate(truncated=TruncHour('start_date', output_field=DateField())))

    def test_trunc_minute_func(self):
        start_datetime = microsecond_support(datetime(2015, 6, 15, 14, 30, 50, 321))
        end_datetime = truncate_to(microsecond_support(datetime(2016, 6, 15, 14, 10, 50, 123)), 'minute')
        if settings.USE_TZ:
            start_datetime = timezone.make_aware(start_datetime, is_dst=False)
            end_datetime = timezone.make_aware(end_datetime, is_dst=False)
        self.create_model(start_datetime, end_datetime)
        self.create_model(end_datetime, start_datetime)
        self.assertQuerysetEqual(
            DTModel.objects.annotate(extracted=TruncMinute('start_datetime')).order_by('start_datetime'),
            [
                (start_datetime, truncate_to(start_datetime, 'minute')),
                (end_datetime, truncate_to(end_datetime, 'minute')),
            ],
            lambda m: (m.start_datetime, m.extracted)
        )
        self.assertEqual(DTModel.objects.filter(start_datetime=TruncMinute('start_datetime')).count(), 1)

        with self.assertRaisesMessage(ValueError, "Cannot truncate DateField 'start_date' to DateTimeField"):
            list(DTModel.objects.annotate(truncated=TruncMinute('start_date')))

        with self.assertRaisesMessage(ValueError, "Cannot truncate DateField 'start_date' to DateTimeField"):
            list(DTModel.objects.annotate(truncated=TruncMinute('start_date', output_field=DateField())))

    def test_trunc_second_func(self):
        start_datetime = microsecond_support(datetime(2015, 6, 15, 14, 30, 50, 321))
        end_datetime = truncate_to(microsecond_support(datetime(2016, 6, 15, 14, 10, 50, 123)), 'second')
        if settings.USE_TZ:
            start_datetime = timezone.make_aware(start_datetime, is_dst=False)
            end_datetime = timezone.make_aware(end_datetime, is_dst=False)
        self.create_model(start_datetime, end_datetime)
        self.create_model(end_datetime, start_datetime)
        self.assertQuerysetEqual(
            DTModel.objects.annotate(extracted=TruncSecond('start_datetime')).order_by('start_datetime'),
            [
                (start_datetime, truncate_to(start_datetime, 'second')),
                (end_datetime, truncate_to(end_datetime, 'second'))
            ],
            lambda m: (m.start_datetime, m.extracted)
        )

        result = 1 if connection.features.supports_microsecond_precision else 2
        self.assertEqual(DTModel.objects.filter(start_datetime=TruncSecond('start_datetime')).count(), result)

        with self.assertRaisesMessage(ValueError, "Cannot truncate DateField 'start_date' to DateTimeField"):
            list(DTModel.objects.annotate(truncated=TruncSecond('start_date')))

        with self.assertRaisesMessage(ValueError, "Cannot truncate DateField 'start_date' to DateTimeField"):
            list(DTModel.objects.annotate(truncated=TruncSecond('start_date', output_field=DateField())))


@skipIf(pytz is None, "this test requires pytz")
@override_settings(USE_TZ=True, TIME_ZONE='UTC')
class DateFunctionWithTimeZoneTests(DateFunctionTests):

    def test_extract_func_with_timezone(self):
        start_datetime = microsecond_support(datetime(2015, 6, 15, 23, 30, 1, 321))
        end_datetime = microsecond_support(datetime(2015, 6, 16, 13, 11, 27, 123))
        start_datetime = timezone.make_aware(start_datetime, is_dst=False)
        end_datetime = timezone.make_aware(end_datetime, is_dst=False)
        self.create_model(start_datetime, end_datetime)
        melb = pytz.timezone('Australia/Melbourne')

        qs = DTModel.objects.annotate(
            day=Extract('start_datetime', 'day'),
            day_melb=Extract('start_datetime', 'day', tzinfo=melb),
            weekday=ExtractWeekDay('start_datetime'),
            weekday_melb=ExtractWeekDay('start_datetime', tzinfo=melb),
            hour=ExtractHour('start_datetime'),
            hour_melb=ExtractHour('start_datetime', tzinfo=melb),
        ).order_by('start_datetime')

        utc_model = qs.get()
        self.assertEqual(utc_model.day, 15)
        self.assertEqual(utc_model.day_melb, 16)
        self.assertEqual(utc_model.weekday, 2)
        self.assertEqual(utc_model.weekday_melb, 3)
        self.assertEqual(utc_model.hour, 23)
        self.assertEqual(utc_model.hour_melb, 9)

        with timezone.override(melb):
            melb_model = qs.get()

        self.assertEqual(melb_model.day, 16)
        self.assertEqual(melb_model.day_melb, 16)
        self.assertEqual(melb_model.weekday, 3)
        self.assertEqual(melb_model.weekday_melb, 3)
        self.assertEqual(melb_model.hour, 9)
        self.assertEqual(melb_model.hour_melb, 9)

    def test_extract_func_explicit_timezone_priority(self):
        start_datetime = microsecond_support(datetime(2015, 6, 15, 23, 30, 1, 321))
        end_datetime = microsecond_support(datetime(2015, 6, 16, 13, 11, 27, 123))
        start_datetime = timezone.make_aware(start_datetime, is_dst=False)
        end_datetime = timezone.make_aware(end_datetime, is_dst=False)
        self.create_model(start_datetime, end_datetime)
        melb = pytz.timezone('Australia/Melbourne')

        with timezone.override(melb):
            model = DTModel.objects.annotate(
                day_melb=Extract('start_datetime', 'day'),
                day_utc=Extract('start_datetime', 'day', tzinfo=timezone.utc),
            ).order_by('start_datetime').get()
            self.assertEqual(model.day_melb, 16)
            self.assertEqual(model.day_utc, 15)

    def test_trunc_timezone_applied_before_truncation(self):
        start_datetime = microsecond_support(datetime(2016, 1, 1, 1, 30, 50, 321))
        end_datetime = microsecond_support(datetime(2016, 6, 15, 14, 10, 50, 123))
        start_datetime = timezone.make_aware(start_datetime, is_dst=False)
        end_datetime = timezone.make_aware(end_datetime, is_dst=False)
        self.create_model(start_datetime, end_datetime)

        melb = pytz.timezone('Australia/Melbourne')
        pacific = pytz.timezone('US/Pacific')

        model = DTModel.objects.annotate(
            melb_year=TruncYear('start_datetime', tzinfo=melb),
            pacific_year=TruncYear('start_datetime', tzinfo=pacific),
        ).order_by('start_datetime').get()

        self.assertEqual(model.start_datetime, start_datetime)
        self.assertEqual(model.melb_year, truncate_to(start_datetime, 'year', melb))
        self.assertEqual(model.pacific_year, truncate_to(start_datetime, 'year', pacific))
        self.assertEqual(model.start_datetime.year, 2016)
        self.assertEqual(model.melb_year.year, 2016)
        self.assertEqual(model.pacific_year.year, 2015)

    def test_trunc_func_with_timezone(self):
        """
        If the truncated datetime transitions to a different offset (daylight
        saving) then the returned value will have that new timezone/offset.
        """
        start_datetime = microsecond_support(datetime(2015, 6, 15, 14, 30, 50, 321))
        end_datetime = microsecond_support(datetime(2016, 6, 15, 14, 10, 50, 123))
        start_datetime = timezone.make_aware(start_datetime, is_dst=False)
        end_datetime = timezone.make_aware(end_datetime, is_dst=False)
        self.create_model(start_datetime, end_datetime)
        self.create_model(end_datetime, start_datetime)

        melb = pytz.timezone('Australia/Melbourne')

        def test_datetime_kind(kind, tzinfo=melb):
            self.assertQuerysetEqual(
                DTModel.objects.annotate(
                    truncated=Trunc('start_datetime', kind, output_field=DateTimeField(), tzinfo=melb)
                ).order_by('start_datetime'),
                [
                    (start_datetime, truncate_to(start_datetime.astimezone(melb), kind, melb)),
                    (end_datetime, truncate_to(end_datetime.astimezone(melb), kind, melb))
                ],
                lambda m: (m.start_datetime, m.truncated)
            )

        def test_date_kind(kind, tzinfo=melb):
            self.assertQuerysetEqual(
                DTModel.objects.annotate(
                    truncated=Trunc('start_date', kind, output_field=DateField(), tzinfo=melb)
                ).order_by('start_datetime'),
                [
                    (start_datetime, truncate_to(start_datetime.date(), kind)),
                    (end_datetime, truncate_to(end_datetime.date(), kind))
                ],
                lambda m: (m.start_datetime, m.truncated)
            )

        test_date_kind('year')
        test_date_kind('month')
        test_date_kind('day')
        test_datetime_kind('year')
        test_datetime_kind('month')
        test_datetime_kind('day')
        test_datetime_kind('hour')
        test_datetime_kind('minute')
        test_datetime_kind('second')

        qs = DTModel.objects.filter(start_datetime__date=Trunc('start_datetime', 'day', output_field=DateField()))
        self.assertEqual(qs.count(), 2)
