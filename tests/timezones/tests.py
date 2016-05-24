from __future__ import unicode_literals

import datetime
import re
import sys
import warnings
from contextlib import contextmanager
from unittest import SkipTest, skipIf
from xml.dom.minidom import parseString

from django.contrib.auth.models import User
from django.core import serializers
from django.core.exceptions import ImproperlyConfigured
from django.db import connection, connections
from django.db.models import Max, Min
from django.http import HttpRequest
from django.template import (
    Context, RequestContext, Template, TemplateSyntaxError, context_processors,
)
from django.test import (
    SimpleTestCase, TestCase, TransactionTestCase, override_settings,
    skipIfDBFeature, skipUnlessDBFeature,
)
from django.test.utils import requires_tz_support
from django.urls import reverse
from django.utils import six, timezone

from .forms import (
    EventForm, EventLocalizedForm, EventLocalizedModelForm, EventModelForm,
    EventSplitForm,
)
from .models import (
    AllDayEvent, Event, MaybeEvent, Session, SessionEvent, Timestamp,
)

try:
    import pytz
except ImportError:
    pytz = None

requires_pytz = skipIf(pytz is None, "this test requires pytz")

# These tests use the EAT (Eastern Africa Time) and ICT (Indochina Time)
# who don't have Daylight Saving Time, so we can represent them easily
# with FixedOffset, and use them directly as tzinfo in the constructors.

# settings.TIME_ZONE is forced to EAT. Most tests use a variant of
# datetime.datetime(2011, 9, 1, 13, 20, 30), which translates to
# 10:20:30 in UTC and 17:20:30 in ICT.

UTC = timezone.utc
EAT = timezone.get_fixed_timezone(180)      # Africa/Nairobi
ICT = timezone.get_fixed_timezone(420)      # Asia/Bangkok


@override_settings(TIME_ZONE='Africa/Nairobi', USE_TZ=False)
class LegacyDatabaseTests(TestCase):

    def test_naive_datetime(self):
        dt = datetime.datetime(2011, 9, 1, 13, 20, 30)
        Event.objects.create(dt=dt)
        event = Event.objects.get()
        self.assertEqual(event.dt, dt)

    @skipUnlessDBFeature('supports_microsecond_precision')
    def test_naive_datetime_with_microsecond(self):
        dt = datetime.datetime(2011, 9, 1, 13, 20, 30, 405060)
        Event.objects.create(dt=dt)
        event = Event.objects.get()
        self.assertEqual(event.dt, dt)

    @skipIfDBFeature('supports_microsecond_precision')
    def test_naive_datetime_with_microsecond_unsupported(self):
        dt = datetime.datetime(2011, 9, 1, 13, 20, 30, 405060)
        Event.objects.create(dt=dt)
        event = Event.objects.get()
        # microseconds are lost during a round-trip in the database
        self.assertEqual(event.dt, dt.replace(microsecond=0))

    @skipUnlessDBFeature('supports_timezones')
    def test_aware_datetime_in_local_timezone(self):
        dt = datetime.datetime(2011, 9, 1, 13, 20, 30, tzinfo=EAT)
        Event.objects.create(dt=dt)
        event = Event.objects.get()
        self.assertIsNone(event.dt.tzinfo)
        # interpret the naive datetime in local time to get the correct value
        self.assertEqual(event.dt.replace(tzinfo=EAT), dt)

    @skipUnlessDBFeature('supports_timezones')
    @skipUnlessDBFeature('supports_microsecond_precision')
    def test_aware_datetime_in_local_timezone_with_microsecond(self):
        dt = datetime.datetime(2011, 9, 1, 13, 20, 30, 405060, tzinfo=EAT)
        Event.objects.create(dt=dt)
        event = Event.objects.get()
        self.assertIsNone(event.dt.tzinfo)
        # interpret the naive datetime in local time to get the correct value
        self.assertEqual(event.dt.replace(tzinfo=EAT), dt)

    # This combination actually never happens.
    @skipUnlessDBFeature('supports_timezones')
    @skipIfDBFeature('supports_microsecond_precision')
    def test_aware_datetime_in_local_timezone_with_microsecond_unsupported(self):
        dt = datetime.datetime(2011, 9, 1, 13, 20, 30, 405060, tzinfo=EAT)
        Event.objects.create(dt=dt)
        event = Event.objects.get()
        self.assertIsNone(event.dt.tzinfo)
        # interpret the naive datetime in local time to get the correct value
        # microseconds are lost during a round-trip in the database
        self.assertEqual(event.dt.replace(tzinfo=EAT), dt.replace(microsecond=0))

    @skipUnlessDBFeature('supports_timezones')
    def test_aware_datetime_in_utc(self):
        dt = datetime.datetime(2011, 9, 1, 10, 20, 30, tzinfo=UTC)
        Event.objects.create(dt=dt)
        event = Event.objects.get()
        self.assertIsNone(event.dt.tzinfo)
        # interpret the naive datetime in local time to get the correct value
        self.assertEqual(event.dt.replace(tzinfo=EAT), dt)

    @skipUnlessDBFeature('supports_timezones')
    def test_aware_datetime_in_other_timezone(self):
        dt = datetime.datetime(2011, 9, 1, 17, 20, 30, tzinfo=ICT)
        Event.objects.create(dt=dt)
        event = Event.objects.get()
        self.assertIsNone(event.dt.tzinfo)
        # interpret the naive datetime in local time to get the correct value
        self.assertEqual(event.dt.replace(tzinfo=EAT), dt)

    @skipIfDBFeature('supports_timezones')
    def test_aware_datetime_unsupported(self):
        dt = datetime.datetime(2011, 9, 1, 13, 20, 30, tzinfo=EAT)
        with self.assertRaises(ValueError):
            Event.objects.create(dt=dt)

    def test_auto_now_and_auto_now_add(self):
        now = datetime.datetime.now()
        past = now - datetime.timedelta(seconds=2)
        future = now + datetime.timedelta(seconds=2)
        Timestamp.objects.create()
        ts = Timestamp.objects.get()
        self.assertLess(past, ts.created)
        self.assertLess(past, ts.updated)
        self.assertGreater(future, ts.updated)
        self.assertGreater(future, ts.updated)

    def test_query_filter(self):
        dt1 = datetime.datetime(2011, 9, 1, 12, 20, 30)
        dt2 = datetime.datetime(2011, 9, 1, 14, 20, 30)
        Event.objects.create(dt=dt1)
        Event.objects.create(dt=dt2)
        self.assertEqual(Event.objects.filter(dt__gte=dt1).count(), 2)
        self.assertEqual(Event.objects.filter(dt__gt=dt1).count(), 1)
        self.assertEqual(Event.objects.filter(dt__gte=dt2).count(), 1)
        self.assertEqual(Event.objects.filter(dt__gt=dt2).count(), 0)

    def test_query_datetime_lookups(self):
        Event.objects.create(dt=datetime.datetime(2011, 1, 1, 1, 30, 0))
        Event.objects.create(dt=datetime.datetime(2011, 1, 1, 4, 30, 0))
        self.assertEqual(Event.objects.filter(dt__year=2011).count(), 2)
        self.assertEqual(Event.objects.filter(dt__month=1).count(), 2)
        self.assertEqual(Event.objects.filter(dt__day=1).count(), 2)
        self.assertEqual(Event.objects.filter(dt__week_day=7).count(), 2)
        self.assertEqual(Event.objects.filter(dt__hour=1).count(), 1)
        self.assertEqual(Event.objects.filter(dt__minute=30).count(), 2)
        self.assertEqual(Event.objects.filter(dt__second=0).count(), 2)

    def test_query_aggregation(self):
        # Only min and max make sense for datetimes.
        Event.objects.create(dt=datetime.datetime(2011, 9, 1, 23, 20, 20))
        Event.objects.create(dt=datetime.datetime(2011, 9, 1, 13, 20, 30))
        Event.objects.create(dt=datetime.datetime(2011, 9, 1, 3, 20, 40))
        result = Event.objects.all().aggregate(Min('dt'), Max('dt'))
        self.assertEqual(result, {
            'dt__min': datetime.datetime(2011, 9, 1, 3, 20, 40),
            'dt__max': datetime.datetime(2011, 9, 1, 23, 20, 20),
        })

    def test_query_annotation(self):
        # Only min and max make sense for datetimes.
        morning = Session.objects.create(name='morning')
        afternoon = Session.objects.create(name='afternoon')
        SessionEvent.objects.create(dt=datetime.datetime(2011, 9, 1, 23, 20, 20), session=afternoon)
        SessionEvent.objects.create(dt=datetime.datetime(2011, 9, 1, 13, 20, 30), session=afternoon)
        SessionEvent.objects.create(dt=datetime.datetime(2011, 9, 1, 3, 20, 40), session=morning)
        morning_min_dt = datetime.datetime(2011, 9, 1, 3, 20, 40)
        afternoon_min_dt = datetime.datetime(2011, 9, 1, 13, 20, 30)
        self.assertQuerysetEqual(
            Session.objects.annotate(dt=Min('events__dt')).order_by('dt'),
            [morning_min_dt, afternoon_min_dt],
            transform=lambda d: d.dt)
        self.assertQuerysetEqual(
            Session.objects.annotate(dt=Min('events__dt')).filter(dt__lt=afternoon_min_dt),
            [morning_min_dt],
            transform=lambda d: d.dt)
        self.assertQuerysetEqual(
            Session.objects.annotate(dt=Min('events__dt')).filter(dt__gte=afternoon_min_dt),
            [afternoon_min_dt],
            transform=lambda d: d.dt)

    def test_query_datetimes(self):
        Event.objects.create(dt=datetime.datetime(2011, 1, 1, 1, 30, 0))
        Event.objects.create(dt=datetime.datetime(2011, 1, 1, 4, 30, 0))
        self.assertQuerysetEqual(
            Event.objects.datetimes('dt', 'year'),
            [datetime.datetime(2011, 1, 1, 0, 0, 0)],
            transform=lambda d: d)
        self.assertQuerysetEqual(
            Event.objects.datetimes('dt', 'month'),
            [datetime.datetime(2011, 1, 1, 0, 0, 0)],
            transform=lambda d: d)
        self.assertQuerysetEqual(
            Event.objects.datetimes('dt', 'day'),
            [datetime.datetime(2011, 1, 1, 0, 0, 0)],
            transform=lambda d: d)
        self.assertQuerysetEqual(
            Event.objects.datetimes('dt', 'hour'),
            [datetime.datetime(2011, 1, 1, 1, 0, 0),
             datetime.datetime(2011, 1, 1, 4, 0, 0)],
            transform=lambda d: d)
        self.assertQuerysetEqual(
            Event.objects.datetimes('dt', 'minute'),
            [datetime.datetime(2011, 1, 1, 1, 30, 0),
             datetime.datetime(2011, 1, 1, 4, 30, 0)],
            transform=lambda d: d)
        self.assertQuerysetEqual(
            Event.objects.datetimes('dt', 'second'),
            [datetime.datetime(2011, 1, 1, 1, 30, 0),
             datetime.datetime(2011, 1, 1, 4, 30, 0)],
            transform=lambda d: d)

    def test_raw_sql(self):
        # Regression test for #17755
        dt = datetime.datetime(2011, 9, 1, 13, 20, 30)
        event = Event.objects.create(dt=dt)
        self.assertQuerysetEqual(
            Event.objects.raw('SELECT * FROM timezones_event WHERE dt = %s', [dt]),
            [event],
            transform=lambda d: d)

    def test_cursor_execute_accepts_naive_datetime(self):
        dt = datetime.datetime(2011, 9, 1, 13, 20, 30)
        with connection.cursor() as cursor:
            cursor.execute('INSERT INTO timezones_event (dt) VALUES (%s)', [dt])
        event = Event.objects.get()
        self.assertEqual(event.dt, dt)

    def test_cursor_execute_returns_naive_datetime(self):
        dt = datetime.datetime(2011, 9, 1, 13, 20, 30)
        Event.objects.create(dt=dt)
        with connection.cursor() as cursor:
            cursor.execute('SELECT dt FROM timezones_event WHERE dt = %s', [dt])
            self.assertEqual(cursor.fetchall()[0][0], dt)

    def test_filter_date_field_with_aware_datetime(self):
        # Regression test for #17742
        day = datetime.date(2011, 9, 1)
        AllDayEvent.objects.create(day=day)
        # This is 2011-09-02T01:30:00+03:00 in EAT
        dt = datetime.datetime(2011, 9, 1, 22, 30, 0, tzinfo=UTC)
        self.assertTrue(AllDayEvent.objects.filter(day__gte=dt).exists())


@override_settings(TIME_ZONE='Africa/Nairobi', USE_TZ=True)
class NewDatabaseTests(TestCase):

    @requires_tz_support
    def test_naive_datetime(self):
        dt = datetime.datetime(2011, 9, 1, 13, 20, 30)
        with warnings.catch_warnings(record=True) as recorded:
            warnings.simplefilter('always')
            Event.objects.create(dt=dt)
            self.assertEqual(len(recorded), 1)
            msg = str(recorded[0].message)
            self.assertTrue(msg.startswith("DateTimeField Event.dt received "
                                           "a naive datetime"))
        event = Event.objects.get()
        # naive datetimes are interpreted in local time
        self.assertEqual(event.dt, dt.replace(tzinfo=EAT))

    @requires_tz_support
    def test_datetime_from_date(self):
        dt = datetime.date(2011, 9, 1)
        with warnings.catch_warnings(record=True) as recorded:
            warnings.simplefilter('always')
            Event.objects.create(dt=dt)
            self.assertEqual(len(recorded), 1)
            msg = str(recorded[0].message)
            self.assertTrue(msg.startswith("DateTimeField Event.dt received "
                                           "a naive datetime"))
        event = Event.objects.get()
        self.assertEqual(event.dt, datetime.datetime(2011, 9, 1, tzinfo=EAT))

    @requires_tz_support
    @skipUnlessDBFeature('supports_microsecond_precision')
    def test_naive_datetime_with_microsecond(self):
        dt = datetime.datetime(2011, 9, 1, 13, 20, 30, 405060)
        with warnings.catch_warnings(record=True) as recorded:
            warnings.simplefilter('always')
            Event.objects.create(dt=dt)
            self.assertEqual(len(recorded), 1)
            msg = str(recorded[0].message)
            self.assertTrue(msg.startswith("DateTimeField Event.dt received "
                                           "a naive datetime"))
        event = Event.objects.get()
        # naive datetimes are interpreted in local time
        self.assertEqual(event.dt, dt.replace(tzinfo=EAT))

    @requires_tz_support
    @skipIfDBFeature('supports_microsecond_precision')
    def test_naive_datetime_with_microsecond_unsupported(self):
        dt = datetime.datetime(2011, 9, 1, 13, 20, 30, 405060)
        with warnings.catch_warnings(record=True) as recorded:
            warnings.simplefilter('always')
            Event.objects.create(dt=dt)
            self.assertEqual(len(recorded), 1)
            msg = str(recorded[0].message)
            self.assertTrue(msg.startswith("DateTimeField Event.dt received "
                                           "a naive datetime"))
        event = Event.objects.get()
        # microseconds are lost during a round-trip in the database
        # naive datetimes are interpreted in local time
        self.assertEqual(event.dt, dt.replace(microsecond=0, tzinfo=EAT))

    def test_aware_datetime_in_local_timezone(self):
        dt = datetime.datetime(2011, 9, 1, 13, 20, 30, tzinfo=EAT)
        Event.objects.create(dt=dt)
        event = Event.objects.get()
        self.assertEqual(event.dt, dt)

    @skipUnlessDBFeature('supports_microsecond_precision')
    def test_aware_datetime_in_local_timezone_with_microsecond(self):
        dt = datetime.datetime(2011, 9, 1, 13, 20, 30, 405060, tzinfo=EAT)
        Event.objects.create(dt=dt)
        event = Event.objects.get()
        self.assertEqual(event.dt, dt)

    @skipIfDBFeature('supports_microsecond_precision')
    def test_aware_datetime_in_local_timezone_with_microsecond_unsupported(self):
        dt = datetime.datetime(2011, 9, 1, 13, 20, 30, 405060, tzinfo=EAT)
        Event.objects.create(dt=dt)
        event = Event.objects.get()
        # microseconds are lost during a round-trip in the database
        self.assertEqual(event.dt, dt.replace(microsecond=0))

    def test_aware_datetime_in_utc(self):
        dt = datetime.datetime(2011, 9, 1, 10, 20, 30, tzinfo=UTC)
        Event.objects.create(dt=dt)
        event = Event.objects.get()
        self.assertEqual(event.dt, dt)

    def test_aware_datetime_in_other_timezone(self):
        dt = datetime.datetime(2011, 9, 1, 17, 20, 30, tzinfo=ICT)
        Event.objects.create(dt=dt)
        event = Event.objects.get()
        self.assertEqual(event.dt, dt)

    def test_auto_now_and_auto_now_add(self):
        now = timezone.now()
        past = now - datetime.timedelta(seconds=2)
        future = now + datetime.timedelta(seconds=2)
        Timestamp.objects.create()
        ts = Timestamp.objects.get()
        self.assertLess(past, ts.created)
        self.assertLess(past, ts.updated)
        self.assertGreater(future, ts.updated)
        self.assertGreater(future, ts.updated)

    def test_query_filter(self):
        dt1 = datetime.datetime(2011, 9, 1, 12, 20, 30, tzinfo=EAT)
        dt2 = datetime.datetime(2011, 9, 1, 14, 20, 30, tzinfo=EAT)
        Event.objects.create(dt=dt1)
        Event.objects.create(dt=dt2)
        self.assertEqual(Event.objects.filter(dt__gte=dt1).count(), 2)
        self.assertEqual(Event.objects.filter(dt__gt=dt1).count(), 1)
        self.assertEqual(Event.objects.filter(dt__gte=dt2).count(), 1)
        self.assertEqual(Event.objects.filter(dt__gt=dt2).count(), 0)

    @requires_pytz
    def test_query_filter_with_pytz_timezones(self):
        tz = pytz.timezone('Europe/Paris')
        dt = datetime.datetime(2011, 9, 1, 12, 20, 30, tzinfo=tz)
        Event.objects.create(dt=dt)
        next = dt + datetime.timedelta(seconds=3)
        prev = dt - datetime.timedelta(seconds=3)
        self.assertEqual(Event.objects.filter(dt__exact=dt).count(), 1)
        self.assertEqual(Event.objects.filter(dt__exact=next).count(), 0)
        self.assertEqual(Event.objects.filter(dt__in=(prev, next)).count(), 0)
        self.assertEqual(Event.objects.filter(dt__in=(prev, dt, next)).count(), 1)
        self.assertEqual(Event.objects.filter(dt__range=(prev, next)).count(), 1)

    @requires_tz_support
    def test_query_filter_with_naive_datetime(self):
        dt = datetime.datetime(2011, 9, 1, 12, 20, 30, tzinfo=EAT)
        Event.objects.create(dt=dt)
        dt = dt.replace(tzinfo=None)
        with warnings.catch_warnings(record=True) as recorded:
            warnings.simplefilter('always')
            # naive datetimes are interpreted in local time
            self.assertEqual(Event.objects.filter(dt__exact=dt).count(), 1)
            self.assertEqual(Event.objects.filter(dt__lte=dt).count(), 1)
            self.assertEqual(Event.objects.filter(dt__gt=dt).count(), 0)
            self.assertEqual(len(recorded), 3)
            for warning in recorded:
                msg = str(warning.message)
                self.assertTrue(msg.startswith("DateTimeField Event.dt "
                                               "received a naive datetime"))

    @skipUnlessDBFeature('has_zoneinfo_database')
    def test_query_datetime_lookups(self):
        Event.objects.create(dt=datetime.datetime(2011, 1, 1, 1, 30, 0, tzinfo=EAT))
        Event.objects.create(dt=datetime.datetime(2011, 1, 1, 4, 30, 0, tzinfo=EAT))
        self.assertEqual(Event.objects.filter(dt__year=2011).count(), 2)
        self.assertEqual(Event.objects.filter(dt__month=1).count(), 2)
        self.assertEqual(Event.objects.filter(dt__day=1).count(), 2)
        self.assertEqual(Event.objects.filter(dt__week_day=7).count(), 2)
        self.assertEqual(Event.objects.filter(dt__hour=1).count(), 1)
        self.assertEqual(Event.objects.filter(dt__minute=30).count(), 2)
        self.assertEqual(Event.objects.filter(dt__second=0).count(), 2)

    @skipUnlessDBFeature('has_zoneinfo_database')
    def test_query_datetime_lookups_in_other_timezone(self):
        Event.objects.create(dt=datetime.datetime(2011, 1, 1, 1, 30, 0, tzinfo=EAT))
        Event.objects.create(dt=datetime.datetime(2011, 1, 1, 4, 30, 0, tzinfo=EAT))
        with timezone.override(UTC):
            # These two dates fall in the same day in EAT, but in different days,
            # years and months in UTC.
            self.assertEqual(Event.objects.filter(dt__year=2011).count(), 1)
            self.assertEqual(Event.objects.filter(dt__month=1).count(), 1)
            self.assertEqual(Event.objects.filter(dt__day=1).count(), 1)
            self.assertEqual(Event.objects.filter(dt__week_day=7).count(), 1)
            self.assertEqual(Event.objects.filter(dt__hour=22).count(), 1)
            self.assertEqual(Event.objects.filter(dt__minute=30).count(), 2)
            self.assertEqual(Event.objects.filter(dt__second=0).count(), 2)

    def test_query_aggregation(self):
        # Only min and max make sense for datetimes.
        Event.objects.create(dt=datetime.datetime(2011, 9, 1, 23, 20, 20, tzinfo=EAT))
        Event.objects.create(dt=datetime.datetime(2011, 9, 1, 13, 20, 30, tzinfo=EAT))
        Event.objects.create(dt=datetime.datetime(2011, 9, 1, 3, 20, 40, tzinfo=EAT))
        result = Event.objects.all().aggregate(Min('dt'), Max('dt'))
        self.assertEqual(result, {
            'dt__min': datetime.datetime(2011, 9, 1, 3, 20, 40, tzinfo=EAT),
            'dt__max': datetime.datetime(2011, 9, 1, 23, 20, 20, tzinfo=EAT),
        })

    def test_query_annotation(self):
        # Only min and max make sense for datetimes.
        morning = Session.objects.create(name='morning')
        afternoon = Session.objects.create(name='afternoon')
        SessionEvent.objects.create(dt=datetime.datetime(2011, 9, 1, 23, 20, 20, tzinfo=EAT), session=afternoon)
        SessionEvent.objects.create(dt=datetime.datetime(2011, 9, 1, 13, 20, 30, tzinfo=EAT), session=afternoon)
        SessionEvent.objects.create(dt=datetime.datetime(2011, 9, 1, 3, 20, 40, tzinfo=EAT), session=morning)
        morning_min_dt = datetime.datetime(2011, 9, 1, 3, 20, 40, tzinfo=EAT)
        afternoon_min_dt = datetime.datetime(2011, 9, 1, 13, 20, 30, tzinfo=EAT)
        self.assertQuerysetEqual(
            Session.objects.annotate(dt=Min('events__dt')).order_by('dt'),
            [morning_min_dt, afternoon_min_dt],
            transform=lambda d: d.dt)
        self.assertQuerysetEqual(
            Session.objects.annotate(dt=Min('events__dt')).filter(dt__lt=afternoon_min_dt),
            [morning_min_dt],
            transform=lambda d: d.dt)
        self.assertQuerysetEqual(
            Session.objects.annotate(dt=Min('events__dt')).filter(dt__gte=afternoon_min_dt),
            [afternoon_min_dt],
            transform=lambda d: d.dt)

    @skipUnlessDBFeature('has_zoneinfo_database')
    def test_query_datetimes(self):
        Event.objects.create(dt=datetime.datetime(2011, 1, 1, 1, 30, 0, tzinfo=EAT))
        Event.objects.create(dt=datetime.datetime(2011, 1, 1, 4, 30, 0, tzinfo=EAT))
        self.assertQuerysetEqual(
            Event.objects.datetimes('dt', 'year'),
            [datetime.datetime(2011, 1, 1, 0, 0, 0, tzinfo=EAT)],
            transform=lambda d: d)
        self.assertQuerysetEqual(
            Event.objects.datetimes('dt', 'month'),
            [datetime.datetime(2011, 1, 1, 0, 0, 0, tzinfo=EAT)],
            transform=lambda d: d)
        self.assertQuerysetEqual(
            Event.objects.datetimes('dt', 'day'),
            [datetime.datetime(2011, 1, 1, 0, 0, 0, tzinfo=EAT)],
            transform=lambda d: d)
        self.assertQuerysetEqual(
            Event.objects.datetimes('dt', 'hour'),
            [datetime.datetime(2011, 1, 1, 1, 0, 0, tzinfo=EAT),
             datetime.datetime(2011, 1, 1, 4, 0, 0, tzinfo=EAT)],
            transform=lambda d: d)
        self.assertQuerysetEqual(
            Event.objects.datetimes('dt', 'minute'),
            [datetime.datetime(2011, 1, 1, 1, 30, 0, tzinfo=EAT),
             datetime.datetime(2011, 1, 1, 4, 30, 0, tzinfo=EAT)],
            transform=lambda d: d)
        self.assertQuerysetEqual(
            Event.objects.datetimes('dt', 'second'),
            [datetime.datetime(2011, 1, 1, 1, 30, 0, tzinfo=EAT),
             datetime.datetime(2011, 1, 1, 4, 30, 0, tzinfo=EAT)],
            transform=lambda d: d)

    @skipUnlessDBFeature('has_zoneinfo_database')
    def test_query_datetimes_in_other_timezone(self):
        Event.objects.create(dt=datetime.datetime(2011, 1, 1, 1, 30, 0, tzinfo=EAT))
        Event.objects.create(dt=datetime.datetime(2011, 1, 1, 4, 30, 0, tzinfo=EAT))
        with timezone.override(UTC):
            self.assertQuerysetEqual(
                Event.objects.datetimes('dt', 'year'),
                [datetime.datetime(2010, 1, 1, 0, 0, 0, tzinfo=UTC),
                 datetime.datetime(2011, 1, 1, 0, 0, 0, tzinfo=UTC)],
                transform=lambda d: d)
            self.assertQuerysetEqual(
                Event.objects.datetimes('dt', 'month'),
                [datetime.datetime(2010, 12, 1, 0, 0, 0, tzinfo=UTC),
                 datetime.datetime(2011, 1, 1, 0, 0, 0, tzinfo=UTC)],
                transform=lambda d: d)
            self.assertQuerysetEqual(
                Event.objects.datetimes('dt', 'day'),
                [datetime.datetime(2010, 12, 31, 0, 0, 0, tzinfo=UTC),
                 datetime.datetime(2011, 1, 1, 0, 0, 0, tzinfo=UTC)],
                transform=lambda d: d)
            self.assertQuerysetEqual(
                Event.objects.datetimes('dt', 'hour'),
                [datetime.datetime(2010, 12, 31, 22, 0, 0, tzinfo=UTC),
                 datetime.datetime(2011, 1, 1, 1, 0, 0, tzinfo=UTC)],
                transform=lambda d: d)
            self.assertQuerysetEqual(
                Event.objects.datetimes('dt', 'minute'),
                [datetime.datetime(2010, 12, 31, 22, 30, 0, tzinfo=UTC),
                 datetime.datetime(2011, 1, 1, 1, 30, 0, tzinfo=UTC)],
                transform=lambda d: d)
            self.assertQuerysetEqual(
                Event.objects.datetimes('dt', 'second'),
                [datetime.datetime(2010, 12, 31, 22, 30, 0, tzinfo=UTC),
                 datetime.datetime(2011, 1, 1, 1, 30, 0, tzinfo=UTC)],
                transform=lambda d: d)

    def test_raw_sql(self):
        # Regression test for #17755
        dt = datetime.datetime(2011, 9, 1, 13, 20, 30, tzinfo=EAT)
        event = Event.objects.create(dt=dt)
        self.assertQuerysetEqual(
            Event.objects.raw('SELECT * FROM timezones_event WHERE dt = %s', [dt]),
            [event],
            transform=lambda d: d)

    @skipUnlessDBFeature('supports_timezones')
    def test_cursor_execute_accepts_aware_datetime(self):
        dt = datetime.datetime(2011, 9, 1, 13, 20, 30, tzinfo=EAT)
        with connection.cursor() as cursor:
            cursor.execute('INSERT INTO timezones_event (dt) VALUES (%s)', [dt])
        event = Event.objects.get()
        self.assertEqual(event.dt, dt)

    @skipIfDBFeature('supports_timezones')
    def test_cursor_execute_accepts_naive_datetime(self):
        dt = datetime.datetime(2011, 9, 1, 13, 20, 30, tzinfo=EAT)
        utc_naive_dt = timezone.make_naive(dt, timezone.utc)
        with connection.cursor() as cursor:
            cursor.execute('INSERT INTO timezones_event (dt) VALUES (%s)', [utc_naive_dt])
        event = Event.objects.get()
        self.assertEqual(event.dt, dt)

    @skipUnlessDBFeature('supports_timezones')
    def test_cursor_execute_returns_aware_datetime(self):
        dt = datetime.datetime(2011, 9, 1, 13, 20, 30, tzinfo=EAT)
        Event.objects.create(dt=dt)
        with connection.cursor() as cursor:
            cursor.execute('SELECT dt FROM timezones_event WHERE dt = %s', [dt])
            self.assertEqual(cursor.fetchall()[0][0], dt)

    @skipIfDBFeature('supports_timezones')
    def test_cursor_execute_returns_naive_datetime(self):
        dt = datetime.datetime(2011, 9, 1, 13, 20, 30, tzinfo=EAT)
        utc_naive_dt = timezone.make_naive(dt, timezone.utc)
        Event.objects.create(dt=dt)
        with connection.cursor() as cursor:
            cursor.execute('SELECT dt FROM timezones_event WHERE dt = %s', [utc_naive_dt])
            self.assertEqual(cursor.fetchall()[0][0], utc_naive_dt)

    @requires_tz_support
    def test_filter_date_field_with_aware_datetime(self):
        # Regression test for #17742
        day = datetime.date(2011, 9, 1)
        AllDayEvent.objects.create(day=day)
        # This is 2011-09-02T01:30:00+03:00 in EAT
        dt = datetime.datetime(2011, 9, 1, 22, 30, 0, tzinfo=UTC)
        self.assertFalse(AllDayEvent.objects.filter(day__gte=dt).exists())

    def test_null_datetime(self):
        # Regression test for #17294
        e = MaybeEvent.objects.create()
        self.assertEqual(e.dt, None)


@override_settings(TIME_ZONE='Africa/Nairobi', USE_TZ=True)
class ForcedTimeZoneDatabaseTests(TransactionTestCase):
    """
    Test the TIME_ZONE database configuration parameter.

    Since this involves reading and writing to the same database through two
    connections, this is a TransactionTestCase.
    """

    available_apps = ['timezones']

    @classmethod
    def setUpClass(cls):
        # @skipIfDBFeature and @skipUnlessDBFeature cannot be chained. The
        # outermost takes precedence. Handle skipping manually instead.
        if connection.features.supports_timezones:
            raise SkipTest("Database has feature(s) supports_timezones")
        if not connection.features.test_db_allows_multiple_connections:
            raise SkipTest("Database doesn't support feature(s): test_db_allows_multiple_connections")

        super(ForcedTimeZoneDatabaseTests, cls).setUpClass()

    @contextmanager
    def override_database_connection_timezone(self, timezone):
        try:
            orig_timezone = connection.settings_dict['TIME_ZONE']
            connection.settings_dict['TIME_ZONE'] = timezone
            # Clear cached properties, after first accessing them to ensure they exist.
            connection.timezone
            del connection.timezone
            connection.timezone_name
            del connection.timezone_name

            yield

        finally:
            connection.settings_dict['TIME_ZONE'] = orig_timezone
            # Clear cached properties, after first accessing them to ensure they exist.
            connection.timezone
            del connection.timezone
            connection.timezone_name
            del connection.timezone_name

    def test_read_datetime(self):
        fake_dt = datetime.datetime(2011, 9, 1, 17, 20, 30, tzinfo=UTC)
        Event.objects.create(dt=fake_dt)

        with self.override_database_connection_timezone('Asia/Bangkok'):
            event = Event.objects.get()
            dt = datetime.datetime(2011, 9, 1, 10, 20, 30, tzinfo=UTC)
        self.assertEqual(event.dt, dt)

    def test_write_datetime(self):
        dt = datetime.datetime(2011, 9, 1, 10, 20, 30, tzinfo=UTC)
        with self.override_database_connection_timezone('Asia/Bangkok'):
            Event.objects.create(dt=dt)

        event = Event.objects.get()
        fake_dt = datetime.datetime(2011, 9, 1, 17, 20, 30, tzinfo=UTC)
        self.assertEqual(event.dt, fake_dt)


@skipUnlessDBFeature('supports_timezones')
@override_settings(TIME_ZONE='Africa/Nairobi', USE_TZ=True)
class UnsupportedTimeZoneDatabaseTests(TestCase):

    def test_time_zone_parameter_not_supported_if_database_supports_timezone(self):
        connections.databases['tz'] = connections.databases['default'].copy()
        connections.databases['tz']['TIME_ZONE'] = 'Asia/Bangkok'
        tz_conn = connections['tz']
        try:
            with self.assertRaises(ImproperlyConfigured):
                tz_conn.cursor()
        finally:
            connections['tz'].close()       # in case the test fails
            del connections['tz']
            del connections.databases['tz']


@override_settings(TIME_ZONE='Africa/Nairobi')
class SerializationTests(SimpleTestCase):

    # Backend-specific notes:
    # - JSON supports only milliseconds, microseconds will be truncated.
    # - PyYAML dumps the UTC offset correctly for timezone-aware datetimes,
    #   but when it loads this representation, it subtracts the offset and
    #   returns a naive datetime object in UTC (http://pyyaml.org/ticket/202).
    # Tests are adapted to take these quirks into account.

    def assert_python_contains_datetime(self, objects, dt):
        self.assertEqual(objects[0]['fields']['dt'], dt)

    def assert_json_contains_datetime(self, json, dt):
        self.assertIn('"fields": {"dt": "%s"}' % dt, json)

    def assert_xml_contains_datetime(self, xml, dt):
        field = parseString(xml).getElementsByTagName('field')[0]
        self.assertXMLEqual(field.childNodes[0].wholeText, dt)

    def assert_yaml_contains_datetime(self, yaml, dt):
        # Depending on the yaml dumper, '!timestamp' might be absent
        six.assertRegex(self, yaml, r"\n  fields: {dt: !(!timestamp)? '%s'}" % re.escape(dt))

    def test_naive_datetime(self):
        dt = datetime.datetime(2011, 9, 1, 13, 20, 30)

        data = serializers.serialize('python', [Event(dt=dt)])
        self.assert_python_contains_datetime(data, dt)
        obj = next(serializers.deserialize('python', data)).object
        self.assertEqual(obj.dt, dt)

        data = serializers.serialize('json', [Event(dt=dt)])
        self.assert_json_contains_datetime(data, "2011-09-01T13:20:30")
        obj = next(serializers.deserialize('json', data)).object
        self.assertEqual(obj.dt, dt)

        data = serializers.serialize('xml', [Event(dt=dt)])
        self.assert_xml_contains_datetime(data, "2011-09-01T13:20:30")
        obj = next(serializers.deserialize('xml', data)).object
        self.assertEqual(obj.dt, dt)

        if not isinstance(serializers.get_serializer('yaml'), serializers.BadSerializer):
            data = serializers.serialize('yaml', [Event(dt=dt)])
            self.assert_yaml_contains_datetime(data, "2011-09-01 13:20:30")
            obj = next(serializers.deserialize('yaml', data)).object
            self.assertEqual(obj.dt, dt)

    def test_naive_datetime_with_microsecond(self):
        dt = datetime.datetime(2011, 9, 1, 13, 20, 30, 405060)

        data = serializers.serialize('python', [Event(dt=dt)])
        self.assert_python_contains_datetime(data, dt)
        obj = next(serializers.deserialize('python', data)).object
        self.assertEqual(obj.dt, dt)

        data = serializers.serialize('json', [Event(dt=dt)])
        self.assert_json_contains_datetime(data, "2011-09-01T13:20:30.405")
        obj = next(serializers.deserialize('json', data)).object
        self.assertEqual(obj.dt, dt.replace(microsecond=405000))

        data = serializers.serialize('xml', [Event(dt=dt)])
        self.assert_xml_contains_datetime(data, "2011-09-01T13:20:30.405060")
        obj = next(serializers.deserialize('xml', data)).object
        self.assertEqual(obj.dt, dt)

        if not isinstance(serializers.get_serializer('yaml'), serializers.BadSerializer):
            data = serializers.serialize('yaml', [Event(dt=dt)])
            self.assert_yaml_contains_datetime(data, "2011-09-01 13:20:30.405060")
            obj = next(serializers.deserialize('yaml', data)).object
            self.assertEqual(obj.dt, dt)

    def test_aware_datetime_with_microsecond(self):
        dt = datetime.datetime(2011, 9, 1, 17, 20, 30, 405060, tzinfo=ICT)

        data = serializers.serialize('python', [Event(dt=dt)])
        self.assert_python_contains_datetime(data, dt)
        obj = next(serializers.deserialize('python', data)).object
        self.assertEqual(obj.dt, dt)

        data = serializers.serialize('json', [Event(dt=dt)])
        self.assert_json_contains_datetime(data, "2011-09-01T17:20:30.405+07:00")
        obj = next(serializers.deserialize('json', data)).object
        self.assertEqual(obj.dt, dt.replace(microsecond=405000))

        data = serializers.serialize('xml', [Event(dt=dt)])
        self.assert_xml_contains_datetime(data, "2011-09-01T17:20:30.405060+07:00")
        obj = next(serializers.deserialize('xml', data)).object
        self.assertEqual(obj.dt, dt)

        if not isinstance(serializers.get_serializer('yaml'), serializers.BadSerializer):
            data = serializers.serialize('yaml', [Event(dt=dt)])
            self.assert_yaml_contains_datetime(data, "2011-09-01 17:20:30.405060+07:00")
            obj = next(serializers.deserialize('yaml', data)).object
            self.assertEqual(obj.dt.replace(tzinfo=UTC), dt)

    def test_aware_datetime_in_utc(self):
        dt = datetime.datetime(2011, 9, 1, 10, 20, 30, tzinfo=UTC)

        data = serializers.serialize('python', [Event(dt=dt)])
        self.assert_python_contains_datetime(data, dt)
        obj = next(serializers.deserialize('python', data)).object
        self.assertEqual(obj.dt, dt)

        data = serializers.serialize('json', [Event(dt=dt)])
        self.assert_json_contains_datetime(data, "2011-09-01T10:20:30Z")
        obj = next(serializers.deserialize('json', data)).object
        self.assertEqual(obj.dt, dt)

        data = serializers.serialize('xml', [Event(dt=dt)])
        self.assert_xml_contains_datetime(data, "2011-09-01T10:20:30+00:00")
        obj = next(serializers.deserialize('xml', data)).object
        self.assertEqual(obj.dt, dt)

        if not isinstance(serializers.get_serializer('yaml'), serializers.BadSerializer):
            data = serializers.serialize('yaml', [Event(dt=dt)])
            self.assert_yaml_contains_datetime(data, "2011-09-01 10:20:30+00:00")
            obj = next(serializers.deserialize('yaml', data)).object
            self.assertEqual(obj.dt.replace(tzinfo=UTC), dt)

    def test_aware_datetime_in_local_timezone(self):
        dt = datetime.datetime(2011, 9, 1, 13, 20, 30, tzinfo=EAT)

        data = serializers.serialize('python', [Event(dt=dt)])
        self.assert_python_contains_datetime(data, dt)
        obj = next(serializers.deserialize('python', data)).object
        self.assertEqual(obj.dt, dt)

        data = serializers.serialize('json', [Event(dt=dt)])
        self.assert_json_contains_datetime(data, "2011-09-01T13:20:30+03:00")
        obj = next(serializers.deserialize('json', data)).object
        self.assertEqual(obj.dt, dt)

        data = serializers.serialize('xml', [Event(dt=dt)])
        self.assert_xml_contains_datetime(data, "2011-09-01T13:20:30+03:00")
        obj = next(serializers.deserialize('xml', data)).object
        self.assertEqual(obj.dt, dt)

        if not isinstance(serializers.get_serializer('yaml'), serializers.BadSerializer):
            data = serializers.serialize('yaml', [Event(dt=dt)])
            self.assert_yaml_contains_datetime(data, "2011-09-01 13:20:30+03:00")
            obj = next(serializers.deserialize('yaml', data)).object
            self.assertEqual(obj.dt.replace(tzinfo=UTC), dt)

    def test_aware_datetime_in_other_timezone(self):
        dt = datetime.datetime(2011, 9, 1, 17, 20, 30, tzinfo=ICT)

        data = serializers.serialize('python', [Event(dt=dt)])
        self.assert_python_contains_datetime(data, dt)
        obj = next(serializers.deserialize('python', data)).object
        self.assertEqual(obj.dt, dt)

        data = serializers.serialize('json', [Event(dt=dt)])
        self.assert_json_contains_datetime(data, "2011-09-01T17:20:30+07:00")
        obj = next(serializers.deserialize('json', data)).object
        self.assertEqual(obj.dt, dt)

        data = serializers.serialize('xml', [Event(dt=dt)])
        self.assert_xml_contains_datetime(data, "2011-09-01T17:20:30+07:00")
        obj = next(serializers.deserialize('xml', data)).object
        self.assertEqual(obj.dt, dt)

        if not isinstance(serializers.get_serializer('yaml'), serializers.BadSerializer):
            data = serializers.serialize('yaml', [Event(dt=dt)])
            self.assert_yaml_contains_datetime(data, "2011-09-01 17:20:30+07:00")
            obj = next(serializers.deserialize('yaml', data)).object
            self.assertEqual(obj.dt.replace(tzinfo=UTC), dt)


@override_settings(DATETIME_FORMAT='c', TIME_ZONE='Africa/Nairobi', USE_L10N=False, USE_TZ=True)
class TemplateTests(TestCase):

    @requires_tz_support
    def test_localtime_templatetag_and_filters(self):
        """
        Test the {% localtime %} templatetag and related filters.
        """
        datetimes = {
            'utc': datetime.datetime(2011, 9, 1, 10, 20, 30, tzinfo=UTC),
            'eat': datetime.datetime(2011, 9, 1, 13, 20, 30, tzinfo=EAT),
            'ict': datetime.datetime(2011, 9, 1, 17, 20, 30, tzinfo=ICT),
            'naive': datetime.datetime(2011, 9, 1, 13, 20, 30),
        }
        templates = {
            'notag': Template("{% load tz %}{{ dt }}|{{ dt|localtime }}|{{ dt|utc }}|{{ dt|timezone:ICT }}"),
            'noarg': Template(
                "{% load tz %}{% localtime %}{{ dt }}|{{ dt|localtime }}|"
                "{{ dt|utc }}|{{ dt|timezone:ICT }}{% endlocaltime %}"
            ),
            'on': Template(
                "{% load tz %}{% localtime on %}{{ dt }}|{{ dt|localtime }}|"
                "{{ dt|utc }}|{{ dt|timezone:ICT }}{% endlocaltime %}"
            ),
            'off': Template(
                "{% load tz %}{% localtime off %}{{ dt }}|{{ dt|localtime }}|"
                "{{ dt|utc }}|{{ dt|timezone:ICT }}{% endlocaltime %}"
            ),
        }

        # Transform a list of keys in 'datetimes' to the expected template
        # output. This makes the definition of 'results' more readable.
        def t(*result):
            return '|'.join(datetimes[key].isoformat() for key in result)

        # Results for USE_TZ = True

        results = {
            'utc': {
                'notag': t('eat', 'eat', 'utc', 'ict'),
                'noarg': t('eat', 'eat', 'utc', 'ict'),
                'on': t('eat', 'eat', 'utc', 'ict'),
                'off': t('utc', 'eat', 'utc', 'ict'),
            },
            'eat': {
                'notag': t('eat', 'eat', 'utc', 'ict'),
                'noarg': t('eat', 'eat', 'utc', 'ict'),
                'on': t('eat', 'eat', 'utc', 'ict'),
                'off': t('eat', 'eat', 'utc', 'ict'),
            },
            'ict': {
                'notag': t('eat', 'eat', 'utc', 'ict'),
                'noarg': t('eat', 'eat', 'utc', 'ict'),
                'on': t('eat', 'eat', 'utc', 'ict'),
                'off': t('ict', 'eat', 'utc', 'ict'),
            },
            'naive': {
                'notag': t('naive', 'eat', 'utc', 'ict'),
                'noarg': t('naive', 'eat', 'utc', 'ict'),
                'on': t('naive', 'eat', 'utc', 'ict'),
                'off': t('naive', 'eat', 'utc', 'ict'),
            }
        }

        for k1, dt in six.iteritems(datetimes):
            for k2, tpl in six.iteritems(templates):
                ctx = Context({'dt': dt, 'ICT': ICT})
                actual = tpl.render(ctx)
                expected = results[k1][k2]
                self.assertEqual(actual, expected, '%s / %s: %r != %r' % (k1, k2, actual, expected))

        # Changes for USE_TZ = False

        results['utc']['notag'] = t('utc', 'eat', 'utc', 'ict')
        results['ict']['notag'] = t('ict', 'eat', 'utc', 'ict')

        with self.settings(USE_TZ=False):
            for k1, dt in six.iteritems(datetimes):
                for k2, tpl in six.iteritems(templates):
                    ctx = Context({'dt': dt, 'ICT': ICT})
                    actual = tpl.render(ctx)
                    expected = results[k1][k2]
                    self.assertEqual(actual, expected, '%s / %s: %r != %r' % (k1, k2, actual, expected))

    @requires_pytz
    def test_localtime_filters_with_pytz(self):
        """
        Test the |localtime, |utc, and |timezone filters with pytz.
        """
        # Use a pytz timezone as local time
        tpl = Template("{% load tz %}{{ dt|localtime }}|{{ dt|utc }}")
        ctx = Context({'dt': datetime.datetime(2011, 9, 1, 12, 20, 30)})

        with self.settings(TIME_ZONE='Europe/Paris'):
            self.assertEqual(tpl.render(ctx), "2011-09-01T12:20:30+02:00|2011-09-01T10:20:30+00:00")

        # Use a pytz timezone as argument
        tpl = Template("{% load tz %}{{ dt|timezone:tz }}")
        ctx = Context({'dt': datetime.datetime(2011, 9, 1, 13, 20, 30),
                       'tz': pytz.timezone('Europe/Paris')})
        self.assertEqual(tpl.render(ctx), "2011-09-01T12:20:30+02:00")

        # Use a pytz timezone name as argument
        tpl = Template("{% load tz %}{{ dt|timezone:'Europe/Paris' }}")
        ctx = Context({'dt': datetime.datetime(2011, 9, 1, 13, 20, 30),
                       'tz': pytz.timezone('Europe/Paris')})
        self.assertEqual(tpl.render(ctx), "2011-09-01T12:20:30+02:00")

    def test_localtime_templatetag_invalid_argument(self):
        with self.assertRaises(TemplateSyntaxError):
            Template("{% load tz %}{% localtime foo %}{% endlocaltime %}").render()

    def test_localtime_filters_do_not_raise_exceptions(self):
        """
        Test the |localtime, |utc, and |timezone filters on bad inputs.
        """
        tpl = Template("{% load tz %}{{ dt }}|{{ dt|localtime }}|{{ dt|utc }}|{{ dt|timezone:tz }}")
        with self.settings(USE_TZ=True):
            # bad datetime value
            ctx = Context({'dt': None, 'tz': ICT})
            self.assertEqual(tpl.render(ctx), "None|||")
            ctx = Context({'dt': 'not a date', 'tz': ICT})
            self.assertEqual(tpl.render(ctx), "not a date|||")
            # bad timezone value
            tpl = Template("{% load tz %}{{ dt|timezone:tz }}")
            ctx = Context({'dt': datetime.datetime(2011, 9, 1, 13, 20, 30), 'tz': None})
            self.assertEqual(tpl.render(ctx), "")
            ctx = Context({'dt': datetime.datetime(2011, 9, 1, 13, 20, 30), 'tz': 'not a tz'})
            self.assertEqual(tpl.render(ctx), "")

    @requires_tz_support
    def test_timezone_templatetag(self):
        """
        Test the {% timezone %} templatetag.
        """
        tpl = Template(
            "{% load tz %}"
            "{{ dt }}|"
            "{% timezone tz1 %}"
            "{{ dt }}|"
            "{% timezone tz2 %}"
            "{{ dt }}"
            "{% endtimezone %}"
            "{% endtimezone %}"
        )
        ctx = Context({'dt': datetime.datetime(2011, 9, 1, 10, 20, 30, tzinfo=UTC),
                       'tz1': ICT, 'tz2': None})
        self.assertEqual(
            tpl.render(ctx),
            "2011-09-01T13:20:30+03:00|2011-09-01T17:20:30+07:00|2011-09-01T13:20:30+03:00"
        )

    @requires_pytz
    def test_timezone_templatetag_with_pytz(self):
        """
        Test the {% timezone %} templatetag with pytz.
        """
        tpl = Template("{% load tz %}{% timezone tz %}{{ dt }}{% endtimezone %}")

        # Use a pytz timezone as argument
        ctx = Context({'dt': datetime.datetime(2011, 9, 1, 13, 20, 30, tzinfo=EAT),
                       'tz': pytz.timezone('Europe/Paris')})
        self.assertEqual(tpl.render(ctx), "2011-09-01T12:20:30+02:00")

        # Use a pytz timezone name as argument
        ctx = Context({'dt': datetime.datetime(2011, 9, 1, 13, 20, 30, tzinfo=EAT),
                       'tz': 'Europe/Paris'})
        self.assertEqual(tpl.render(ctx), "2011-09-01T12:20:30+02:00")

    def test_timezone_templatetag_invalid_argument(self):
        with self.assertRaises(TemplateSyntaxError):
            Template("{% load tz %}{% timezone %}{% endtimezone %}").render()
        with self.assertRaises(ValueError if pytz is None else pytz.UnknownTimeZoneError):
            Template("{% load tz %}{% timezone tz %}{% endtimezone %}").render(Context({'tz': 'foobar'}))

    @skipIf(sys.platform.startswith('win'), "Windows uses non-standard time zone names")
    def test_get_current_timezone_templatetag(self):
        """
        Test the {% get_current_timezone %} templatetag.
        """
        tpl = Template("{% load tz %}{% get_current_timezone as time_zone %}{{ time_zone }}")

        self.assertEqual(tpl.render(Context()), "Africa/Nairobi" if pytz else "EAT")
        with timezone.override(UTC):
            self.assertEqual(tpl.render(Context()), "UTC")

        tpl = Template(
            "{% load tz %}{% timezone tz %}{% get_current_timezone as time_zone %}"
            "{% endtimezone %}{{ time_zone }}"
        )

        self.assertEqual(tpl.render(Context({'tz': ICT})), "+0700")
        with timezone.override(UTC):
            self.assertEqual(tpl.render(Context({'tz': ICT})), "+0700")

    @requires_pytz
    def test_get_current_timezone_templatetag_with_pytz(self):
        """
        Test the {% get_current_timezone %} templatetag with pytz.
        """
        tpl = Template("{% load tz %}{% get_current_timezone as time_zone %}{{ time_zone }}")
        with timezone.override(pytz.timezone('Europe/Paris')):
            self.assertEqual(tpl.render(Context()), "Europe/Paris")

        tpl = Template(
            "{% load tz %}{% timezone 'Europe/Paris' %}"
            "{% get_current_timezone as time_zone %}{% endtimezone %}"
            "{{ time_zone }}"
        )
        self.assertEqual(tpl.render(Context()), "Europe/Paris")

    def test_get_current_timezone_templatetag_invalid_argument(self):
        with self.assertRaises(TemplateSyntaxError):
            Template("{% load tz %}{% get_current_timezone %}").render()

    @skipIf(sys.platform.startswith('win'), "Windows uses non-standard time zone names")
    def test_tz_template_context_processor(self):
        """
        Test the django.template.context_processors.tz template context processor.
        """
        tpl = Template("{{ TIME_ZONE }}")
        context = Context()
        self.assertEqual(tpl.render(context), "")
        request_context = RequestContext(HttpRequest(), processors=[context_processors.tz])
        self.assertEqual(tpl.render(request_context), "Africa/Nairobi" if pytz else "EAT")

    @requires_tz_support
    def test_date_and_time_template_filters(self):
        tpl = Template("{{ dt|date:'Y-m-d' }} at {{ dt|time:'H:i:s' }}")
        ctx = Context({'dt': datetime.datetime(2011, 9, 1, 20, 20, 20, tzinfo=UTC)})
        self.assertEqual(tpl.render(ctx), "2011-09-01 at 23:20:20")
        with timezone.override(ICT):
            self.assertEqual(tpl.render(ctx), "2011-09-02 at 03:20:20")

    def test_date_and_time_template_filters_honor_localtime(self):
        tpl = Template(
            "{% load tz %}{% localtime off %}{{ dt|date:'Y-m-d' }} at "
            "{{ dt|time:'H:i:s' }}{% endlocaltime %}"
        )
        ctx = Context({'dt': datetime.datetime(2011, 9, 1, 20, 20, 20, tzinfo=UTC)})
        self.assertEqual(tpl.render(ctx), "2011-09-01 at 20:20:20")
        with timezone.override(ICT):
            self.assertEqual(tpl.render(ctx), "2011-09-01 at 20:20:20")

    def test_localtime_with_time_zone_setting_set_to_none(self):
        # Regression for #17274
        tpl = Template("{% load tz %}{{ dt }}")
        ctx = Context({'dt': datetime.datetime(2011, 9, 1, 12, 20, 30, tzinfo=EAT)})

        with self.settings(TIME_ZONE=None):
            # the actual value depends on the system time zone of the host
            self.assertTrue(tpl.render(ctx).startswith("2011"))

    @requires_tz_support
    def test_now_template_tag_uses_current_time_zone(self):
        # Regression for #17343
        tpl = Template("{% now \"O\" %}")
        self.assertEqual(tpl.render(Context({})), "+0300")
        with timezone.override(ICT):
            self.assertEqual(tpl.render(Context({})), "+0700")


@override_settings(DATETIME_FORMAT='c', TIME_ZONE='Africa/Nairobi', USE_L10N=False, USE_TZ=False)
class LegacyFormsTests(TestCase):

    def test_form(self):
        form = EventForm({'dt': '2011-09-01 13:20:30'})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['dt'], datetime.datetime(2011, 9, 1, 13, 20, 30))

    @requires_pytz
    def test_form_with_non_existent_time(self):
        form = EventForm({'dt': '2011-03-27 02:30:00'})
        with timezone.override(pytz.timezone('Europe/Paris')):
            # this is obviously a bug
            self.assertTrue(form.is_valid())
            self.assertEqual(form.cleaned_data['dt'], datetime.datetime(2011, 3, 27, 2, 30, 0))

    @requires_pytz
    def test_form_with_ambiguous_time(self):
        form = EventForm({'dt': '2011-10-30 02:30:00'})
        with timezone.override(pytz.timezone('Europe/Paris')):
            # this is obviously a bug
            self.assertTrue(form.is_valid())
            self.assertEqual(form.cleaned_data['dt'], datetime.datetime(2011, 10, 30, 2, 30, 0))

    def test_split_form(self):
        form = EventSplitForm({'dt_0': '2011-09-01', 'dt_1': '13:20:30'})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['dt'], datetime.datetime(2011, 9, 1, 13, 20, 30))

    def test_model_form(self):
        EventModelForm({'dt': '2011-09-01 13:20:30'}).save()
        e = Event.objects.get()
        self.assertEqual(e.dt, datetime.datetime(2011, 9, 1, 13, 20, 30))


@override_settings(DATETIME_FORMAT='c', TIME_ZONE='Africa/Nairobi', USE_L10N=False, USE_TZ=True)
class NewFormsTests(TestCase):

    @requires_tz_support
    def test_form(self):
        form = EventForm({'dt': '2011-09-01 13:20:30'})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['dt'], datetime.datetime(2011, 9, 1, 10, 20, 30, tzinfo=UTC))

    def test_form_with_other_timezone(self):
        form = EventForm({'dt': '2011-09-01 17:20:30'})
        with timezone.override(ICT):
            self.assertTrue(form.is_valid())
            self.assertEqual(form.cleaned_data['dt'], datetime.datetime(2011, 9, 1, 10, 20, 30, tzinfo=UTC))

    def test_form_with_explicit_timezone(self):
        form = EventForm({'dt': '2011-09-01 17:20:30+07:00'})
        # Datetime inputs formats don't allow providing a time zone.
        self.assertFalse(form.is_valid())

    @requires_pytz
    def test_form_with_non_existent_time(self):
        with timezone.override(pytz.timezone('Europe/Paris')):
            form = EventForm({'dt': '2011-03-27 02:30:00'})
            self.assertFalse(form.is_valid())
            self.assertEqual(
                form.errors['dt'], [
                    "2011-03-27 02:30:00 couldn't be interpreted in time zone "
                    "Europe/Paris; it may be ambiguous or it may not exist."
                ]
            )

    @requires_pytz
    def test_form_with_ambiguous_time(self):
        with timezone.override(pytz.timezone('Europe/Paris')):
            form = EventForm({'dt': '2011-10-30 02:30:00'})
            self.assertFalse(form.is_valid())
            self.assertEqual(
                form.errors['dt'], [
                    "2011-10-30 02:30:00 couldn't be interpreted in time zone "
                    "Europe/Paris; it may be ambiguous or it may not exist."
                ]
            )

    @requires_tz_support
    def test_split_form(self):
        form = EventSplitForm({'dt_0': '2011-09-01', 'dt_1': '13:20:30'})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['dt'], datetime.datetime(2011, 9, 1, 10, 20, 30, tzinfo=UTC))

    @requires_tz_support
    def test_localized_form(self):
        form = EventLocalizedForm(initial={'dt': datetime.datetime(2011, 9, 1, 13, 20, 30, tzinfo=EAT)})
        with timezone.override(ICT):
            self.assertIn("2011-09-01 17:20:30", str(form))

    @requires_tz_support
    def test_model_form(self):
        EventModelForm({'dt': '2011-09-01 13:20:30'}).save()
        e = Event.objects.get()
        self.assertEqual(e.dt, datetime.datetime(2011, 9, 1, 10, 20, 30, tzinfo=UTC))

    @requires_tz_support
    def test_localized_model_form(self):
        form = EventLocalizedModelForm(instance=Event(dt=datetime.datetime(2011, 9, 1, 13, 20, 30, tzinfo=EAT)))
        with timezone.override(ICT):
            self.assertIn("2011-09-01 17:20:30", str(form))


@override_settings(
    DATETIME_FORMAT='c',
    TIME_ZONE='Africa/Nairobi',
    USE_L10N=False,
    USE_TZ=True,
    ROOT_URLCONF='timezones.urls',
)
class AdminTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.u1 = User.objects.create_user(
            password='secret',
            last_login=datetime.datetime(2007, 5, 30, 13, 20, 10, tzinfo=UTC),
            is_superuser=True, username='super', first_name='Super', last_name='User',
            email='super@example.com', is_staff=True, is_active=True,
            date_joined=datetime.datetime(2007, 5, 30, 13, 20, 10, tzinfo=UTC),
        )

    def setUp(self):
        self.client.force_login(self.u1)

    @requires_tz_support
    def test_changelist(self):
        e = Event.objects.create(dt=datetime.datetime(2011, 9, 1, 10, 20, 30, tzinfo=UTC))
        response = self.client.get(reverse('admin_tz:timezones_event_changelist'))
        self.assertContains(response, e.dt.astimezone(EAT).isoformat())

    def test_changelist_in_other_timezone(self):
        e = Event.objects.create(dt=datetime.datetime(2011, 9, 1, 10, 20, 30, tzinfo=UTC))
        with timezone.override(ICT):
            response = self.client.get(reverse('admin_tz:timezones_event_changelist'))
        self.assertContains(response, e.dt.astimezone(ICT).isoformat())

    @requires_tz_support
    def test_change_editable(self):
        e = Event.objects.create(dt=datetime.datetime(2011, 9, 1, 10, 20, 30, tzinfo=UTC))
        response = self.client.get(reverse('admin_tz:timezones_event_change', args=(e.pk,)))
        self.assertContains(response, e.dt.astimezone(EAT).date().isoformat())
        self.assertContains(response, e.dt.astimezone(EAT).time().isoformat())

    def test_change_editable_in_other_timezone(self):
        e = Event.objects.create(dt=datetime.datetime(2011, 9, 1, 10, 20, 30, tzinfo=UTC))
        with timezone.override(ICT):
            response = self.client.get(reverse('admin_tz:timezones_event_change', args=(e.pk,)))
        self.assertContains(response, e.dt.astimezone(ICT).date().isoformat())
        self.assertContains(response, e.dt.astimezone(ICT).time().isoformat())

    @requires_tz_support
    def test_change_readonly(self):
        Timestamp.objects.create()
        # re-fetch the object for backends that lose microseconds (MySQL)
        t = Timestamp.objects.get()
        response = self.client.get(reverse('admin_tz:timezones_timestamp_change', args=(t.pk,)))
        self.assertContains(response, t.created.astimezone(EAT).isoformat())

    def test_change_readonly_in_other_timezone(self):
        Timestamp.objects.create()
        # re-fetch the object for backends that lose microseconds (MySQL)
        t = Timestamp.objects.get()
        with timezone.override(ICT):
            response = self.client.get(reverse('admin_tz:timezones_timestamp_change', args=(t.pk,)))
        self.assertContains(response, t.created.astimezone(ICT).isoformat())
