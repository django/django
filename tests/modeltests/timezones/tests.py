from __future__ import with_statement

import datetime
import os
import sys
import time
import warnings

try:
    import pytz
except ImportError:
    pytz = None

from django.conf import settings
from django.core import serializers
from django.core.urlresolvers import reverse
from django.db import connection
from django.db.models import Min, Max
from django.http import HttpRequest
from django.template import Context, RequestContext, Template, TemplateSyntaxError
from django.test import TestCase, skipIfDBFeature, skipUnlessDBFeature
from django.test.utils import override_settings
from django.utils import timezone
from django.utils.tzinfo import FixedOffset
from django.utils.unittest import skipIf, skipUnless

from .forms import EventForm, EventSplitForm, EventModelForm
from .models import Event, MaybeEvent, Session, SessionEvent, Timestamp


# These tests use the EAT (Eastern Africa Time) and ICT (Indochina Time)
# who don't have Daylight Saving Time, so we can represent them easily
# with FixedOffset, and use them directly as tzinfo in the constructors.

# settings.TIME_ZONE is forced to EAT. Most tests use a variant of
# datetime.datetime(2011, 9, 1, 13, 20, 30), which translates to
# 10:20:30 in UTC and 17:20:30 in ICT.

UTC = timezone.utc
EAT = FixedOffset(180)      # Africa/Nairobi
ICT = FixedOffset(420)      # Asia/Bangkok

TZ_SUPPORT = hasattr(time, 'tzset')

# On OSes that don't provide tzset (Windows), we can't set the timezone
# in which the program runs. As a consequence, we must skip tests that
# don't enforce a specific timezone (with timezone.override or equivalent),
# or attempt to interpret naive datetimes in the default timezone.

requires_tz_support = skipUnless(TZ_SUPPORT,
        "This test relies on the ability to run a program in an arbitrary "
        "time zone, but your operating system isn't able to do that.")


class BaseDateTimeTests(TestCase):

    @classmethod
    def setUpClass(self):
        self._old_time_zone = settings.TIME_ZONE
        settings.TIME_ZONE = connection.settings_dict['TIME_ZONE'] = 'Africa/Nairobi'
        timezone._localtime = None
        if TZ_SUPPORT:
            self._old_tz = os.environ.get('TZ')
            os.environ['TZ'] = 'Africa/Nairobi'
            time.tzset()

    @classmethod
    def tearDownClass(self):
        settings.TIME_ZONE = connection.settings_dict['TIME_ZONE'] = self._old_time_zone
        timezone._localtime = None
        if TZ_SUPPORT:
            if self._old_tz is None:
                del os.environ['TZ']
            else:
                os.environ['TZ'] = self._old_tz
            time.tzset()


#@override_settings(USE_TZ=False)
class LegacyDatabaseTests(BaseDateTimeTests):

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
    @skipIfDBFeature('needs_datetime_string_cast')
    def test_aware_datetime_in_utc(self):
        dt = datetime.datetime(2011, 9, 1, 10, 20, 30, tzinfo=UTC)
        Event.objects.create(dt=dt)
        event = Event.objects.get()
        self.assertIsNone(event.dt.tzinfo)
        # interpret the naive datetime in local time to get the correct value
        self.assertEqual(event.dt.replace(tzinfo=EAT), dt)

    # This combination is no longer possible since timezone support
    # was removed from the SQLite backend -- it didn't work.
    @skipUnlessDBFeature('supports_timezones')
    @skipUnlessDBFeature('needs_datetime_string_cast')
    def test_aware_datetime_in_utc_unsupported(self):
        dt = datetime.datetime(2011, 9, 1, 10, 20, 30, tzinfo=UTC)
        Event.objects.create(dt=dt)
        event = Event.objects.get()
        self.assertIsNone(event.dt.tzinfo)
        # django.db.backend.utils.typecast_dt will just drop the
        # timezone, so a round-trip in the database alters the data (!)
        # interpret the naive datetime in local time and you get a wrong value
        self.assertNotEqual(event.dt.replace(tzinfo=EAT), dt)
        # interpret the naive datetime in original time to get the correct value
        self.assertEqual(event.dt.replace(tzinfo=UTC), dt)

    @skipUnlessDBFeature('supports_timezones')
    @skipIfDBFeature('needs_datetime_string_cast')
    def test_aware_datetime_in_other_timezone(self):
        dt = datetime.datetime(2011, 9, 1, 17, 20, 30, tzinfo=ICT)
        Event.objects.create(dt=dt)
        event = Event.objects.get()
        self.assertIsNone(event.dt.tzinfo)
        # interpret the naive datetime in local time to get the correct value
        self.assertEqual(event.dt.replace(tzinfo=EAT), dt)

    # This combination is no longer possible since timezone support
    # was removed from the SQLite backend -- it didn't work.
    @skipUnlessDBFeature('supports_timezones')
    @skipUnlessDBFeature('needs_datetime_string_cast')
    def test_aware_datetime_in_other_timezone_unsupported(self):
        dt = datetime.datetime(2011, 9, 1, 17, 20, 30, tzinfo=ICT)
        Event.objects.create(dt=dt)
        event = Event.objects.get()
        self.assertIsNone(event.dt.tzinfo)
        # django.db.backend.utils.typecast_dt will just drop the
        # timezone, so a round-trip in the database alters the data (!)
        # interpret the naive datetime in local time and you get a wrong value
        self.assertNotEqual(event.dt.replace(tzinfo=EAT), dt)
        # interpret the naive datetime in original time to get the correct value
        self.assertEqual(event.dt.replace(tzinfo=ICT), dt)

    @skipIfDBFeature('supports_timezones')
    def test_aware_datetime_unspported(self):
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

    def test_query_date_related_filters(self):
        Event.objects.create(dt=datetime.datetime(2011, 1, 1, 1, 30, 0))
        Event.objects.create(dt=datetime.datetime(2011, 1, 1, 4, 30, 0))
        self.assertEqual(Event.objects.filter(dt__year=2011).count(), 2)
        self.assertEqual(Event.objects.filter(dt__month=1).count(), 2)
        self.assertEqual(Event.objects.filter(dt__day=1).count(), 2)
        self.assertEqual(Event.objects.filter(dt__week_day=7).count(), 2)

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

    def test_query_dates(self):
        Event.objects.create(dt=datetime.datetime(2011, 1, 1, 1, 30, 0))
        Event.objects.create(dt=datetime.datetime(2011, 1, 1, 4, 30, 0))
        self.assertQuerysetEqual(Event.objects.dates('dt', 'year'),
                [datetime.datetime(2011, 1, 1)], transform=lambda d: d)
        self.assertQuerysetEqual(Event.objects.dates('dt', 'month'),
                [datetime.datetime(2011, 1, 1)], transform=lambda d: d)
        self.assertQuerysetEqual(Event.objects.dates('dt', 'day'),
                [datetime.datetime(2011, 1, 1)], transform=lambda d: d)

    def test_raw_sql(self):
        # Regression test for #17755
        dt = datetime.datetime(2011, 9, 1, 13, 20, 30)
        event = Event.objects.create(dt=dt)
        self.assertQuerysetEqual(
                Event.objects.raw('SELECT * FROM timezones_event WHERE dt = %s', [dt]),
                [event],
                transform=lambda d: d)

LegacyDatabaseTests = override_settings(USE_TZ=False)(LegacyDatabaseTests)


#@override_settings(USE_TZ=True)
class NewDatabaseTests(BaseDateTimeTests):

    @requires_tz_support
    @skipIf(sys.version_info < (2, 6), "this test requires Python >= 2.6")
    def test_naive_datetime(self):
        dt = datetime.datetime(2011, 9, 1, 13, 20, 30)
        with warnings.catch_warnings(record=True) as recorded:
            warnings.simplefilter('always')
            Event.objects.create(dt=dt)
            self.assertEqual(len(recorded), 1)
            msg = str(recorded[0].message)
            self.assertTrue(msg.startswith("DateTimeField received a naive datetime"))
        event = Event.objects.get()
        # naive datetimes are interpreted in local time
        self.assertEqual(event.dt, dt.replace(tzinfo=EAT))

    @requires_tz_support
    @skipIf(sys.version_info < (2, 6), "this test requires Python >= 2.6")
    def test_datetime_from_date(self):
        dt = datetime.date(2011, 9, 1)
        with warnings.catch_warnings(record=True) as recorded:
            warnings.simplefilter('always')
            Event.objects.create(dt=dt)
            self.assertEqual(len(recorded), 1)
            msg = str(recorded[0].message)
            self.assertTrue(msg.startswith("DateTimeField received a naive datetime"))
        event = Event.objects.get()
        self.assertEqual(event.dt, datetime.datetime(2011, 9, 1, tzinfo=EAT))

    @requires_tz_support
    @skipIf(sys.version_info < (2, 6), "this test requires Python >= 2.6")
    @skipUnlessDBFeature('supports_microsecond_precision')
    def test_naive_datetime_with_microsecond(self):
        dt = datetime.datetime(2011, 9, 1, 13, 20, 30, 405060)
        with warnings.catch_warnings(record=True) as recorded:
            warnings.simplefilter('always')
            Event.objects.create(dt=dt)
            self.assertEqual(len(recorded), 1)
            msg = str(recorded[0].message)
            self.assertTrue(msg.startswith("DateTimeField received a naive datetime"))
        event = Event.objects.get()
        # naive datetimes are interpreted in local time
        self.assertEqual(event.dt, dt.replace(tzinfo=EAT))

    @requires_tz_support
    @skipIf(sys.version_info < (2, 6), "this test requires Python >= 2.6")
    @skipIfDBFeature('supports_microsecond_precision')
    def test_naive_datetime_with_microsecond_unsupported(self):
        dt = datetime.datetime(2011, 9, 1, 13, 20, 30, 405060)
        with warnings.catch_warnings(record=True) as recorded:
            warnings.simplefilter('always')
            Event.objects.create(dt=dt)
            self.assertEqual(len(recorded), 1)
            msg = str(recorded[0].message)
            self.assertTrue(msg.startswith("DateTimeField received a naive datetime"))
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

    @skipIf(pytz is None, "this test requires pytz")
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
    @skipIf(sys.version_info < (2, 6), "this test requires Python >= 2.6")
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
                self.assertTrue(msg.startswith("DateTimeField received a naive datetime"))

    def test_query_date_related_filters(self):
        # These two dates fall in the same day in EAT, but in different days,
        # years and months in UTC, and aggregation is performed in UTC when
        # time zone support is enabled. This test could be changed if the
        # implementation is changed to perform the aggregation is local time.
        Event.objects.create(dt=datetime.datetime(2011, 1, 1, 1, 30, 0, tzinfo=EAT))
        Event.objects.create(dt=datetime.datetime(2011, 1, 1, 4, 30, 0, tzinfo=EAT))
        self.assertEqual(Event.objects.filter(dt__year=2011).count(), 1)
        self.assertEqual(Event.objects.filter(dt__month=1).count(), 1)
        self.assertEqual(Event.objects.filter(dt__day=1).count(), 1)
        self.assertEqual(Event.objects.filter(dt__week_day=7).count(), 1)

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

    def test_query_dates(self):
        # Same comment as in test_query_date_related_filters.
        Event.objects.create(dt=datetime.datetime(2011, 1, 1, 1, 30, 0, tzinfo=EAT))
        Event.objects.create(dt=datetime.datetime(2011, 1, 1, 4, 30, 0, tzinfo=EAT))
        self.assertQuerysetEqual(Event.objects.dates('dt', 'year'),
                [datetime.datetime(2010, 1, 1, tzinfo=UTC),
                 datetime.datetime(2011, 1, 1, tzinfo=UTC)],
                transform=lambda d: d)
        self.assertQuerysetEqual(Event.objects.dates('dt', 'month'),
                [datetime.datetime(2010, 12, 1, tzinfo=UTC),
                 datetime.datetime(2011, 1, 1, tzinfo=UTC)],
                transform=lambda d: d)
        self.assertQuerysetEqual(Event.objects.dates('dt', 'day'),
                [datetime.datetime(2010, 12, 31, tzinfo=UTC),
                 datetime.datetime(2011, 1, 1, tzinfo=UTC)],
                transform=lambda d: d)

    def test_raw_sql(self):
        # Regression test for #17755
        dt = datetime.datetime(2011, 9, 1, 13, 20, 30, tzinfo=EAT)
        event = Event.objects.create(dt=dt)
        self.assertQuerysetEqual(
                Event.objects.raw('SELECT * FROM timezones_event WHERE dt = %s', [dt]),
                [event],
                transform=lambda d: d)

    def test_null_datetime(self):
        # Regression for #17294
        e = MaybeEvent.objects.create()
        self.assertEqual(e.dt, None)

NewDatabaseTests = override_settings(USE_TZ=True)(NewDatabaseTests)


class SerializationTests(BaseDateTimeTests):

    # Backend-specific notes:
    # - JSON supports only milliseconds, microseconds will be truncated.
    # - PyYAML dumps the UTC offset correctly for timezone-aware datetimes,
    #   but when it loads this representation, it substracts the offset and
    #   returns a naive datetime object in UTC (http://pyyaml.org/ticket/202).
    # Tests are adapted to take these quirks into account.

    def test_naive_datetime(self):
        dt = datetime.datetime(2011, 9, 1, 13, 20, 30)

        data = serializers.serialize('python', [Event(dt=dt)])
        self.assertEqual(data[0]['fields']['dt'], dt)
        obj = serializers.deserialize('python', data).next().object
        self.assertEqual(obj.dt, dt)

        data = serializers.serialize('json', [Event(dt=dt)])
        self.assertIn('"fields": {"dt": "2011-09-01T13:20:30"}', data)
        obj = serializers.deserialize('json', data).next().object
        self.assertEqual(obj.dt, dt)

        data = serializers.serialize('xml', [Event(dt=dt)])
        self.assertIn('<field type="DateTimeField" name="dt">2011-09-01T13:20:30</field>', data)
        obj = serializers.deserialize('xml', data).next().object
        self.assertEqual(obj.dt, dt)

        if 'yaml' in serializers.get_serializer_formats():
            data = serializers.serialize('yaml', [Event(dt=dt)])
            self.assertIn("- fields: {dt: !!timestamp '2011-09-01 13:20:30'}", data)
            obj = serializers.deserialize('yaml', data).next().object
            self.assertEqual(obj.dt, dt)

    def test_naive_datetime_with_microsecond(self):
        dt = datetime.datetime(2011, 9, 1, 13, 20, 30, 405060)

        data = serializers.serialize('python', [Event(dt=dt)])
        self.assertEqual(data[0]['fields']['dt'], dt)
        obj = serializers.deserialize('python', data).next().object
        self.assertEqual(obj.dt, dt)

        data = serializers.serialize('json', [Event(dt=dt)])
        self.assertIn('"fields": {"dt": "2011-09-01T13:20:30.405"}', data)
        obj = serializers.deserialize('json', data).next().object
        self.assertEqual(obj.dt, dt.replace(microsecond=405000))

        data = serializers.serialize('xml', [Event(dt=dt)])
        self.assertIn('<field type="DateTimeField" name="dt">2011-09-01T13:20:30.405060</field>', data)
        obj = serializers.deserialize('xml', data).next().object
        self.assertEqual(obj.dt, dt)

        if 'yaml' in serializers.get_serializer_formats():
            data = serializers.serialize('yaml', [Event(dt=dt)])
            self.assertIn("- fields: {dt: !!timestamp '2011-09-01 13:20:30.405060'}", data)
            obj = serializers.deserialize('yaml', data).next().object
            self.assertEqual(obj.dt, dt)

    def test_aware_datetime_with_microsecond(self):
        dt = datetime.datetime(2011, 9, 1, 17, 20, 30, 405060, tzinfo=ICT)

        data = serializers.serialize('python', [Event(dt=dt)])
        self.assertEqual(data[0]['fields']['dt'], dt)
        obj = serializers.deserialize('python', data).next().object
        self.assertEqual(obj.dt, dt)

        data = serializers.serialize('json', [Event(dt=dt)])
        self.assertIn('"fields": {"dt": "2011-09-01T17:20:30.405+07:00"}', data)
        obj = serializers.deserialize('json', data).next().object
        self.assertEqual(obj.dt, dt.replace(microsecond=405000))

        data = serializers.serialize('xml', [Event(dt=dt)])
        self.assertIn('<field type="DateTimeField" name="dt">2011-09-01T17:20:30.405060+07:00</field>', data)
        obj = serializers.deserialize('xml', data).next().object
        self.assertEqual(obj.dt, dt)

        if 'yaml' in serializers.get_serializer_formats():
            data = serializers.serialize('yaml', [Event(dt=dt)])
            self.assertIn("- fields: {dt: !!timestamp '2011-09-01 17:20:30.405060+07:00'}", data)
            obj = serializers.deserialize('yaml', data).next().object
            self.assertEqual(obj.dt.replace(tzinfo=UTC), dt)

    def test_aware_datetime_in_utc(self):
        dt = datetime.datetime(2011, 9, 1, 10, 20, 30, tzinfo=UTC)

        data = serializers.serialize('python', [Event(dt=dt)])
        self.assertEqual(data[0]['fields']['dt'], dt)
        obj = serializers.deserialize('python', data).next().object
        self.assertEqual(obj.dt, dt)

        data = serializers.serialize('json', [Event(dt=dt)])
        self.assertIn('"fields": {"dt": "2011-09-01T10:20:30Z"}', data)
        obj = serializers.deserialize('json', data).next().object
        self.assertEqual(obj.dt, dt)

        data = serializers.serialize('xml', [Event(dt=dt)])
        self.assertIn('<field type="DateTimeField" name="dt">2011-09-01T10:20:30+00:00</field>', data)
        obj = serializers.deserialize('xml', data).next().object
        self.assertEqual(obj.dt, dt)

        if 'yaml' in serializers.get_serializer_formats():
            data = serializers.serialize('yaml', [Event(dt=dt)])
            self.assertIn("- fields: {dt: !!timestamp '2011-09-01 10:20:30+00:00'}", data)
            obj = serializers.deserialize('yaml', data).next().object
            self.assertEqual(obj.dt.replace(tzinfo=UTC), dt)

    def test_aware_datetime_in_local_timezone(self):
        dt = datetime.datetime(2011, 9, 1, 13, 20, 30, tzinfo=EAT)

        data = serializers.serialize('python', [Event(dt=dt)])
        self.assertEqual(data[0]['fields']['dt'], dt)
        obj = serializers.deserialize('python', data).next().object
        self.assertEqual(obj.dt, dt)

        data = serializers.serialize('json', [Event(dt=dt)])
        self.assertIn('"fields": {"dt": "2011-09-01T13:20:30+03:00"}', data)
        obj = serializers.deserialize('json', data).next().object
        self.assertEqual(obj.dt, dt)

        data = serializers.serialize('xml', [Event(dt=dt)])
        self.assertIn('<field type="DateTimeField" name="dt">2011-09-01T13:20:30+03:00</field>', data)
        obj = serializers.deserialize('xml', data).next().object
        self.assertEqual(obj.dt, dt)

        if 'yaml' in serializers.get_serializer_formats():
            data = serializers.serialize('yaml', [Event(dt=dt)])
            self.assertIn("- fields: {dt: !!timestamp '2011-09-01 13:20:30+03:00'}", data)
            obj = serializers.deserialize('yaml', data).next().object
            self.assertEqual(obj.dt.replace(tzinfo=UTC), dt)

    def test_aware_datetime_in_other_timezone(self):
        dt = datetime.datetime(2011, 9, 1, 17, 20, 30, tzinfo=ICT)

        data = serializers.serialize('python', [Event(dt=dt)])
        self.assertEqual(data[0]['fields']['dt'], dt)
        obj = serializers.deserialize('python', data).next().object
        self.assertEqual(obj.dt, dt)

        data = serializers.serialize('json', [Event(dt=dt)])
        self.assertIn('"fields": {"dt": "2011-09-01T17:20:30+07:00"}', data)
        obj = serializers.deserialize('json', data).next().object
        self.assertEqual(obj.dt, dt)

        data = serializers.serialize('xml', [Event(dt=dt)])
        self.assertIn('<field type="DateTimeField" name="dt">2011-09-01T17:20:30+07:00</field>', data)
        obj = serializers.deserialize('xml', data).next().object
        self.assertEqual(obj.dt, dt)

        if 'yaml' in serializers.get_serializer_formats():
            data = serializers.serialize('yaml', [Event(dt=dt)])
            self.assertIn("- fields: {dt: !!timestamp '2011-09-01 17:20:30+07:00'}", data)
            obj = serializers.deserialize('yaml', data).next().object
            self.assertEqual(obj.dt.replace(tzinfo=UTC), dt)

#@override_settings(DATETIME_FORMAT='c', USE_L10N=False, USE_TZ=True)
class TemplateTests(BaseDateTimeTests):

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
            'noarg': Template("{% load tz %}{% localtime %}{{ dt }}|{{ dt|localtime }}|{{ dt|utc }}|{{ dt|timezone:ICT }}{% endlocaltime %}"),
            'on':    Template("{% load tz %}{% localtime on %}{{ dt }}|{{ dt|localtime }}|{{ dt|utc }}|{{ dt|timezone:ICT }}{% endlocaltime %}"),
            'off':   Template("{% load tz %}{% localtime off %}{{ dt }}|{{ dt|localtime }}|{{ dt|utc }}|{{ dt|timezone:ICT }}{% endlocaltime %}"),
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
                'on':    t('eat', 'eat', 'utc', 'ict'),
                'off':   t('utc', 'eat', 'utc', 'ict'),
            },
            'eat': {
                'notag': t('eat', 'eat', 'utc', 'ict'),
                'noarg': t('eat', 'eat', 'utc', 'ict'),
                'on':    t('eat', 'eat', 'utc', 'ict'),
                'off':   t('eat', 'eat', 'utc', 'ict'),
            },
            'ict': {
                'notag': t('eat', 'eat', 'utc', 'ict'),
                'noarg': t('eat', 'eat', 'utc', 'ict'),
                'on':    t('eat', 'eat', 'utc', 'ict'),
                'off':   t('ict', 'eat', 'utc', 'ict'),
            },
            'naive': {
                'notag': t('naive', 'eat', 'utc', 'ict'),
                'noarg': t('naive', 'eat', 'utc', 'ict'),
                'on':    t('naive', 'eat', 'utc', 'ict'),
                'off':   t('naive', 'eat', 'utc', 'ict'),
            }
        }

        for k1, dt in datetimes.iteritems():
            for k2, tpl in templates.iteritems():
                ctx = Context({'dt': dt, 'ICT': ICT})
                actual = tpl.render(ctx)
                expected = results[k1][k2]
                self.assertEqual(actual, expected, '%s / %s: %r != %r' % (k1, k2, actual, expected))

        # Changes for USE_TZ = False

        results['utc']['notag'] = t('utc', 'eat', 'utc', 'ict')
        results['ict']['notag'] = t('ict', 'eat', 'utc', 'ict')

        with self.settings(USE_TZ=False):
            for k1, dt in datetimes.iteritems():
                for k2, tpl in templates.iteritems():
                    ctx = Context({'dt': dt, 'ICT': ICT})
                    actual = tpl.render(ctx)
                    expected = results[k1][k2]
                    self.assertEqual(actual, expected, '%s / %s: %r != %r' % (k1, k2, actual, expected))

    @skipIf(pytz is None, "this test requires pytz")
    def test_localtime_filters_with_pytz(self):
        """
        Test the |localtime, |utc, and |timezone filters with pytz.
        """
        # Use a pytz timezone as local time
        tpl = Template("{% load tz %}{{ dt|localtime }}|{{ dt|utc }}")
        ctx = Context({'dt': datetime.datetime(2011, 9, 1, 12, 20, 30)})

        timezone._localtime = None
        with self.settings(TIME_ZONE='Europe/Paris'):
            self.assertEqual(tpl.render(ctx), "2011-09-01T12:20:30+02:00|2011-09-01T10:20:30+00:00")
        timezone._localtime = None

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
        tpl = Template("{% load tz %}"
                "{{ dt }}|"
                "{% timezone tz1 %}"
                    "{{ dt }}|"
                    "{% timezone tz2 %}"
                        "{{ dt }}"
                    "{% endtimezone %}"
                "{% endtimezone %}")
        ctx = Context({'dt': datetime.datetime(2011, 9, 1, 10, 20, 30, tzinfo=UTC),
                       'tz1': ICT, 'tz2': None})
        self.assertEqual(tpl.render(ctx), "2011-09-01T13:20:30+03:00|2011-09-01T17:20:30+07:00|2011-09-01T13:20:30+03:00")

    @skipIf(pytz is None, "this test requires pytz")
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

        tpl = Template("{% load tz %}{% timezone tz %}{% get_current_timezone as time_zone %}{% endtimezone %}{{ time_zone }}")

        self.assertEqual(tpl.render(Context({'tz': ICT})), "+0700")
        with timezone.override(UTC):
            self.assertEqual(tpl.render(Context({'tz': ICT})), "+0700")

    @skipIf(pytz is None, "this test requires pytz")
    def test_get_current_timezone_templatetag_with_pytz(self):
        """
        Test the {% get_current_timezone %} templatetag with pytz.
        """
        tpl = Template("{% load tz %}{% get_current_timezone as time_zone %}{{ time_zone }}")
        with timezone.override(pytz.timezone('Europe/Paris')):
            self.assertEqual(tpl.render(Context()), "Europe/Paris")

        tpl = Template("{% load tz %}{% timezone 'Europe/Paris' %}{% get_current_timezone as time_zone %}{% endtimezone %}{{ time_zone }}")
        self.assertEqual(tpl.render(Context()), "Europe/Paris")

    def test_get_current_timezone_templatetag_invalid_argument(self):
        with self.assertRaises(TemplateSyntaxError):
            Template("{% load tz %}{% get_current_timezone %}").render()

    @skipIf(sys.platform.startswith('win'), "Windows uses non-standard time zone names")
    def test_tz_template_context_processor(self):
        """
        Test the django.core.context_processors.tz template context processor.
        """
        tpl = Template("{{ TIME_ZONE }}")
        self.assertEqual(tpl.render(Context()), "")
        self.assertEqual(tpl.render(RequestContext(HttpRequest())), "Africa/Nairobi" if pytz else "EAT")

    @requires_tz_support
    def test_date_and_time_template_filters(self):
        tpl = Template("{{ dt|date:'Y-m-d' }} at {{ dt|time:'H:i:s' }}")
        ctx = Context({'dt': datetime.datetime(2011, 9, 1, 20, 20, 20, tzinfo=UTC)})
        self.assertEqual(tpl.render(ctx), "2011-09-01 at 23:20:20")
        with timezone.override(ICT):
            self.assertEqual(tpl.render(ctx), "2011-09-02 at 03:20:20")

    def test_date_and_time_template_filters_honor_localtime(self):
        tpl = Template("{% load tz %}{% localtime off %}{{ dt|date:'Y-m-d' }} at {{ dt|time:'H:i:s' }}{% endlocaltime %}")
        ctx = Context({'dt': datetime.datetime(2011, 9, 1, 20, 20, 20, tzinfo=UTC)})
        self.assertEqual(tpl.render(ctx), "2011-09-01 at 20:20:20")
        with timezone.override(ICT):
            self.assertEqual(tpl.render(ctx), "2011-09-01 at 20:20:20")

    def test_localtime_with_time_zone_setting_set_to_none(self):
        # Regression for #17274
        tpl = Template("{% load tz %}{{ dt }}")
        ctx = Context({'dt': datetime.datetime(2011, 9, 1, 12, 20, 30, tzinfo=EAT)})

        timezone._localtime = None
        with self.settings(TIME_ZONE=None):
            # the actual value depends on the system time zone of the host
            self.assertTrue(tpl.render(ctx).startswith("2011"))
        timezone._localtime = None

    @requires_tz_support
    def test_now_template_tag_uses_current_time_zone(self):
        # Regression for #17343
        tpl = Template("{% now \"O\" %}")
        self.assertEqual(tpl.render(Context({})), "+0300")
        with timezone.override(ICT):
            self.assertEqual(tpl.render(Context({})), "+0700")

TemplateTests = override_settings(DATETIME_FORMAT='c', USE_L10N=False, USE_TZ=True)(TemplateTests)

#@override_settings(DATETIME_FORMAT='c', USE_L10N=False, USE_TZ=False)
class LegacyFormsTests(BaseDateTimeTests):

    def test_form(self):
        form = EventForm({'dt': u'2011-09-01 13:20:30'})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['dt'], datetime.datetime(2011, 9, 1, 13, 20, 30))

    @skipIf(pytz is None, "this test requires pytz")
    def test_form_with_non_existent_time(self):
        form = EventForm({'dt': u'2011-03-27 02:30:00'})
        with timezone.override(pytz.timezone('Europe/Paris')):
            # this is obviously a bug
            self.assertTrue(form.is_valid())
            self.assertEqual(form.cleaned_data['dt'], datetime.datetime(2011, 3, 27, 2, 30, 0))

    @skipIf(pytz is None, "this test requires pytz")
    def test_form_with_ambiguous_time(self):
        form = EventForm({'dt': u'2011-10-30 02:30:00'})
        with timezone.override(pytz.timezone('Europe/Paris')):
            # this is obviously a bug
            self.assertTrue(form.is_valid())
            self.assertEqual(form.cleaned_data['dt'], datetime.datetime(2011, 10, 30, 2, 30, 0))

    def test_split_form(self):
        form = EventSplitForm({'dt_0': u'2011-09-01', 'dt_1': u'13:20:30'})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['dt'], datetime.datetime(2011, 9, 1, 13, 20, 30))

    def test_model_form(self):
        EventModelForm({'dt': u'2011-09-01 13:20:30'}).save()
        e = Event.objects.get()
        self.assertEqual(e.dt, datetime.datetime(2011, 9, 1, 13, 20, 30))

LegacyFormsTests = override_settings(DATETIME_FORMAT='c', USE_L10N=False, USE_TZ=False)(LegacyFormsTests)

#@override_settings(DATETIME_FORMAT='c', USE_L10N=False, USE_TZ=True)
class NewFormsTests(BaseDateTimeTests):

    @requires_tz_support
    def test_form(self):
        form = EventForm({'dt': u'2011-09-01 13:20:30'})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['dt'], datetime.datetime(2011, 9, 1, 10, 20, 30, tzinfo=UTC))

    def test_form_with_other_timezone(self):
        form = EventForm({'dt': u'2011-09-01 17:20:30'})
        with timezone.override(ICT):
            self.assertTrue(form.is_valid())
            self.assertEqual(form.cleaned_data['dt'], datetime.datetime(2011, 9, 1, 10, 20, 30, tzinfo=UTC))

    @skipIf(pytz is None, "this test requires pytz")
    def test_form_with_non_existent_time(self):
        with timezone.override(pytz.timezone('Europe/Paris')):
            form = EventForm({'dt': u'2011-03-27 02:30:00'})
            self.assertFalse(form.is_valid())
            self.assertEqual(form.errors['dt'],
                [u"2011-03-27 02:30:00 couldn't be interpreted in time zone "
                 u"Europe/Paris; it may be ambiguous or it may not exist."])

    @skipIf(pytz is None, "this test requires pytz")
    def test_form_with_ambiguous_time(self):
        with timezone.override(pytz.timezone('Europe/Paris')):
            form = EventForm({'dt': u'2011-10-30 02:30:00'})
            self.assertFalse(form.is_valid())
            self.assertEqual(form.errors['dt'],
                [u"2011-10-30 02:30:00 couldn't be interpreted in time zone "
                 u"Europe/Paris; it may be ambiguous or it may not exist."])

    @requires_tz_support
    def test_split_form(self):
        form = EventSplitForm({'dt_0': u'2011-09-01', 'dt_1': u'13:20:30'})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['dt'], datetime.datetime(2011, 9, 1, 10, 20, 30, tzinfo=UTC))

    @requires_tz_support
    def test_model_form(self):
        EventModelForm({'dt': u'2011-09-01 13:20:30'}).save()
        e = Event.objects.get()
        self.assertEqual(e.dt, datetime.datetime(2011, 9, 1, 10, 20, 30, tzinfo=UTC))

NewFormsTests = override_settings(DATETIME_FORMAT='c', USE_L10N=False, USE_TZ=True)(NewFormsTests)

#@override_settings(DATETIME_FORMAT='c', USE_L10N=False, USE_TZ=True)
class AdminTests(BaseDateTimeTests):

    urls = 'modeltests.timezones.urls'
    fixtures = ['tz_users.xml']

    def setUp(self):
        self.client.login(username='super', password='secret')

    @requires_tz_support
    def test_changelist(self):
        e = Event.objects.create(dt=datetime.datetime(2011, 9, 1, 10, 20, 30, tzinfo=UTC))
        response = self.client.get(reverse('admin:timezones_event_changelist'))
        self.assertContains(response, e.dt.astimezone(EAT).isoformat())

    def test_changelist_in_other_timezone(self):
        e = Event.objects.create(dt=datetime.datetime(2011, 9, 1, 10, 20, 30, tzinfo=UTC))
        with timezone.override(ICT):
            response = self.client.get(reverse('admin:timezones_event_changelist'))
        self.assertContains(response, e.dt.astimezone(ICT).isoformat())

    @requires_tz_support
    def test_change_editable(self):
        e = Event.objects.create(dt=datetime.datetime(2011, 9, 1, 10, 20, 30, tzinfo=UTC))
        response = self.client.get(reverse('admin:timezones_event_change', args=(e.pk,)))
        self.assertContains(response, e.dt.astimezone(EAT).date().isoformat())
        self.assertContains(response, e.dt.astimezone(EAT).time().isoformat())

    def test_change_editable_in_other_timezone(self):
        e = Event.objects.create(dt=datetime.datetime(2011, 9, 1, 10, 20, 30, tzinfo=UTC))
        with timezone.override(ICT):
            response = self.client.get(reverse('admin:timezones_event_change', args=(e.pk,)))
        self.assertContains(response, e.dt.astimezone(ICT).date().isoformat())
        self.assertContains(response, e.dt.astimezone(ICT).time().isoformat())

    @requires_tz_support
    def test_change_readonly(self):
        Timestamp.objects.create()
        # re-fetch the object for backends that lose microseconds (MySQL)
        t = Timestamp.objects.get()
        response = self.client.get(reverse('admin:timezones_timestamp_change', args=(t.pk,)))
        self.assertContains(response, t.created.astimezone(EAT).isoformat())

    def test_change_readonly_in_other_timezone(self):
        Timestamp.objects.create()
        # re-fetch the object for backends that lose microseconds (MySQL)
        t = Timestamp.objects.get()
        with timezone.override(ICT):
            response = self.client.get(reverse('admin:timezones_timestamp_change', args=(t.pk,)))
        self.assertContains(response, t.created.astimezone(ICT).isoformat())

AdminTests = override_settings(DATETIME_FORMAT='c', USE_L10N=False, USE_TZ=True)(AdminTests)


class UtilitiesTests(BaseDateTimeTests):

    def test_make_aware(self):
        self.assertEqual(
            timezone.make_aware(datetime.datetime(2011, 9, 1, 13, 20, 30), EAT),
            datetime.datetime(2011, 9, 1, 13, 20, 30, tzinfo=EAT)
        )
        self.assertEqual(
            timezone.make_aware(datetime.datetime(2011, 9, 1, 10, 20, 30), UTC),
            datetime.datetime(2011, 9, 1, 10, 20, 30, tzinfo=UTC)
        )

    def test_make_naive(self):
        self.assertEqual(
            timezone.make_naive(datetime.datetime(2011, 9, 1, 13, 20, 30, tzinfo=EAT), EAT),
            datetime.datetime(2011, 9, 1, 13, 20, 30)
        )
        self.assertEqual(
            timezone.make_naive(datetime.datetime(2011, 9, 1, 13, 20, 30, tzinfo=EAT), UTC),
            datetime.datetime(2011, 9, 1, 10, 20, 30)
        )
        self.assertEqual(
            timezone.make_naive(datetime.datetime(2011, 9, 1, 10, 20, 30, tzinfo=UTC), UTC),
            datetime.datetime(2011, 9, 1, 10, 20, 30)
        )
