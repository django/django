import datetime
import zoneinfo

from django.conf import settings
from django.db import DataError, OperationalError
from django.db.models import (
    DateField,
    DateTimeField,
    F,
    IntegerField,
    Max,
    OuterRef,
    Subquery,
    TimeField,
)
from django.db.models.functions import (
    Extract,
    ExtractDay,
    ExtractHour,
    ExtractIsoWeekDay,
    ExtractIsoYear,
    ExtractMinute,
    ExtractMonth,
    ExtractQuarter,
    ExtractSecond,
    ExtractWeek,
    ExtractWeekDay,
    ExtractYear,
    Trunc,
    TruncDate,
    TruncDay,
    TruncHour,
    TruncMinute,
    TruncMonth,
    TruncQuarter,
    TruncSecond,
    TruncTime,
    TruncWeek,
    TruncYear,
)
from django.test import (
    TestCase,
    override_settings,
    skipIfDBFeature,
    skipUnlessDBFeature,
)
from django.utils import timezone

from ..models import Author, DTModel, Fan


def truncate_to(value, kind, tzinfo=None):
    # Convert to target timezone before truncation
    if tzinfo is not None:
        value = value.astimezone(tzinfo)

    def truncate(value, kind):
        if kind == "second":
            return value.replace(microsecond=0)
        if kind == "minute":
            return value.replace(second=0, microsecond=0)
        if kind == "hour":
            return value.replace(minute=0, second=0, microsecond=0)
        if kind == "day":
            if isinstance(value, datetime.datetime):
                return value.replace(hour=0, minute=0, second=0, microsecond=0)
            return value
        if kind == "week":
            if isinstance(value, datetime.datetime):
                return (value - datetime.timedelta(days=value.weekday())).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
            return value - datetime.timedelta(days=value.weekday())
        if kind == "month":
            if isinstance(value, datetime.datetime):
                return value.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            return value.replace(day=1)
        if kind == "quarter":
            month_in_quarter = value.month - (value.month - 1) % 3
            if isinstance(value, datetime.datetime):
                return value.replace(
                    month=month_in_quarter,
                    day=1,
                    hour=0,
                    minute=0,
                    second=0,
                    microsecond=0,
                )
            return value.replace(month=month_in_quarter, day=1)
        # otherwise, truncate to year
        if isinstance(value, datetime.datetime):
            return value.replace(
                month=1, day=1, hour=0, minute=0, second=0, microsecond=0
            )
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
            name=start_datetime.isoformat() if start_datetime else "None",
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            start_date=start_datetime.date() if start_datetime else None,
            end_date=end_datetime.date() if end_datetime else None,
            start_time=start_datetime.time() if start_datetime else None,
            end_time=end_datetime.time() if end_datetime else None,
            duration=(
                (end_datetime - start_datetime)
                if start_datetime and end_datetime
                else None
            ),
        )

    def test_extract_year_exact_lookup(self):
        """
        Extract year uses a BETWEEN filter to compare the year to allow indexes
        to be used.
        """
        start_datetime = datetime.datetime(2015, 6, 15, 14, 10)
        end_datetime = datetime.datetime(2016, 6, 15, 14, 10)
        if settings.USE_TZ:
            start_datetime = timezone.make_aware(start_datetime)
            end_datetime = timezone.make_aware(end_datetime)
        self.create_model(start_datetime, end_datetime)
        self.create_model(end_datetime, start_datetime)

        for lookup in ("year", "iso_year"):
            with self.subTest(lookup):
                qs = DTModel.objects.filter(
                    **{"start_datetime__%s__exact" % lookup: 2015}
                )
                self.assertEqual(qs.count(), 1)
                query_string = str(qs.query).lower()
                self.assertEqual(query_string.count(" between "), 1)
                self.assertEqual(query_string.count("extract"), 0)
                # exact is implied and should be the same
                qs = DTModel.objects.filter(**{"start_datetime__%s" % lookup: 2015})
                self.assertEqual(qs.count(), 1)
                query_string = str(qs.query).lower()
                self.assertEqual(query_string.count(" between "), 1)
                self.assertEqual(query_string.count("extract"), 0)
                # date and datetime fields should behave the same
                qs = DTModel.objects.filter(**{"start_date__%s" % lookup: 2015})
                self.assertEqual(qs.count(), 1)
                query_string = str(qs.query).lower()
                self.assertEqual(query_string.count(" between "), 1)
                self.assertEqual(query_string.count("extract"), 0)
                # an expression rhs cannot use the between optimization.
                qs = DTModel.objects.annotate(
                    start_year=ExtractYear("start_datetime"),
                ).filter(end_datetime__year=F("start_year") + 1)
                self.assertEqual(qs.count(), 1)
                query_string = str(qs.query).lower()
                self.assertEqual(query_string.count(" between "), 0)
                self.assertEqual(query_string.count("extract"), 3)

    def test_extract_year_greaterthan_lookup(self):
        start_datetime = datetime.datetime(2015, 6, 15, 14, 10)
        end_datetime = datetime.datetime(2016, 6, 15, 14, 10)
        if settings.USE_TZ:
            start_datetime = timezone.make_aware(start_datetime)
            end_datetime = timezone.make_aware(end_datetime)
        self.create_model(start_datetime, end_datetime)
        self.create_model(end_datetime, start_datetime)

        for lookup in ("year", "iso_year"):
            with self.subTest(lookup):
                qs = DTModel.objects.filter(**{"start_datetime__%s__gt" % lookup: 2015})
                self.assertEqual(qs.count(), 1)
                self.assertEqual(str(qs.query).lower().count("extract"), 0)
                qs = DTModel.objects.filter(
                    **{"start_datetime__%s__gte" % lookup: 2015}
                )
                self.assertEqual(qs.count(), 2)
                self.assertEqual(str(qs.query).lower().count("extract"), 0)
                qs = DTModel.objects.annotate(
                    start_year=ExtractYear("start_datetime"),
                ).filter(**{"end_datetime__%s__gte" % lookup: F("start_year")})
                self.assertEqual(qs.count(), 1)
                self.assertGreaterEqual(str(qs.query).lower().count("extract"), 2)

    def test_extract_year_lessthan_lookup(self):
        start_datetime = datetime.datetime(2015, 6, 15, 14, 10)
        end_datetime = datetime.datetime(2016, 6, 15, 14, 10)
        if settings.USE_TZ:
            start_datetime = timezone.make_aware(start_datetime)
            end_datetime = timezone.make_aware(end_datetime)
        self.create_model(start_datetime, end_datetime)
        self.create_model(end_datetime, start_datetime)

        for lookup in ("year", "iso_year"):
            with self.subTest(lookup):
                qs = DTModel.objects.filter(**{"start_datetime__%s__lt" % lookup: 2016})
                self.assertEqual(qs.count(), 1)
                self.assertEqual(str(qs.query).count("extract"), 0)
                qs = DTModel.objects.filter(
                    **{"start_datetime__%s__lte" % lookup: 2016}
                )
                self.assertEqual(qs.count(), 2)
                self.assertEqual(str(qs.query).count("extract"), 0)
                qs = DTModel.objects.annotate(
                    end_year=ExtractYear("end_datetime"),
                ).filter(**{"start_datetime__%s__lte" % lookup: F("end_year")})
                self.assertEqual(qs.count(), 1)
                self.assertGreaterEqual(str(qs.query).lower().count("extract"), 2)

    def test_extract_lookup_name_sql_injection(self):
        start_datetime = datetime.datetime(2015, 6, 15, 14, 30, 50, 321)
        end_datetime = datetime.datetime(2016, 6, 15, 14, 10, 50, 123)
        if settings.USE_TZ:
            start_datetime = timezone.make_aware(start_datetime)
            end_datetime = timezone.make_aware(end_datetime)
        self.create_model(start_datetime, end_datetime)
        self.create_model(end_datetime, start_datetime)

        with self.assertRaises((OperationalError, ValueError)):
            DTModel.objects.filter(
                start_datetime__year=Extract(
                    "start_datetime", "day' FROM start_datetime)) OR 1=1;--"
                )
            ).exists()

    def test_extract_func(self):
        start_datetime = datetime.datetime(2015, 6, 15, 14, 30, 50, 321)
        end_datetime = datetime.datetime(2016, 6, 15, 14, 10, 50, 123)
        if settings.USE_TZ:
            start_datetime = timezone.make_aware(start_datetime)
            end_datetime = timezone.make_aware(end_datetime)
        self.create_model(start_datetime, end_datetime)
        self.create_model(end_datetime, start_datetime)

        with self.assertRaisesMessage(ValueError, "lookup_name must be provided"):
            Extract("start_datetime")

        msg = (
            "Extract input expression must be DateField, DateTimeField, TimeField, or "
            "DurationField."
        )
        with self.assertRaisesMessage(ValueError, msg):
            list(DTModel.objects.annotate(extracted=Extract("name", "hour")))

        with self.assertRaisesMessage(
            ValueError,
            "Cannot extract time component 'second' from DateField 'start_date'.",
        ):
            list(DTModel.objects.annotate(extracted=Extract("start_date", "second")))

        self.assertQuerySetEqual(
            DTModel.objects.annotate(
                extracted=Extract("start_datetime", "year")
            ).order_by("start_datetime"),
            [(start_datetime, start_datetime.year), (end_datetime, end_datetime.year)],
            lambda m: (m.start_datetime, m.extracted),
        )
        self.assertQuerySetEqual(
            DTModel.objects.annotate(
                extracted=Extract("start_datetime", "quarter")
            ).order_by("start_datetime"),
            [(start_datetime, 2), (end_datetime, 2)],
            lambda m: (m.start_datetime, m.extracted),
        )
        self.assertQuerySetEqual(
            DTModel.objects.annotate(
                extracted=Extract("start_datetime", "month")
            ).order_by("start_datetime"),
            [
                (start_datetime, start_datetime.month),
                (end_datetime, end_datetime.month),
            ],
            lambda m: (m.start_datetime, m.extracted),
        )
        self.assertQuerySetEqual(
            DTModel.objects.annotate(
                extracted=Extract("start_datetime", "day")
            ).order_by("start_datetime"),
            [(start_datetime, start_datetime.day), (end_datetime, end_datetime.day)],
            lambda m: (m.start_datetime, m.extracted),
        )
        self.assertQuerySetEqual(
            DTModel.objects.annotate(
                extracted=Extract("start_datetime", "week")
            ).order_by("start_datetime"),
            [(start_datetime, 25), (end_datetime, 24)],
            lambda m: (m.start_datetime, m.extracted),
        )
        self.assertQuerySetEqual(
            DTModel.objects.annotate(
                extracted=Extract("start_datetime", "week_day")
            ).order_by("start_datetime"),
            [
                (start_datetime, (start_datetime.isoweekday() % 7) + 1),
                (end_datetime, (end_datetime.isoweekday() % 7) + 1),
            ],
            lambda m: (m.start_datetime, m.extracted),
        )
        self.assertQuerySetEqual(
            DTModel.objects.annotate(
                extracted=Extract("start_datetime", "iso_week_day"),
            ).order_by("start_datetime"),
            [
                (start_datetime, start_datetime.isoweekday()),
                (end_datetime, end_datetime.isoweekday()),
            ],
            lambda m: (m.start_datetime, m.extracted),
        )
        self.assertQuerySetEqual(
            DTModel.objects.annotate(
                extracted=Extract("start_datetime", "hour")
            ).order_by("start_datetime"),
            [(start_datetime, start_datetime.hour), (end_datetime, end_datetime.hour)],
            lambda m: (m.start_datetime, m.extracted),
        )
        self.assertQuerySetEqual(
            DTModel.objects.annotate(
                extracted=Extract("start_datetime", "minute")
            ).order_by("start_datetime"),
            [
                (start_datetime, start_datetime.minute),
                (end_datetime, end_datetime.minute),
            ],
            lambda m: (m.start_datetime, m.extracted),
        )
        self.assertQuerySetEqual(
            DTModel.objects.annotate(
                extracted=Extract("start_datetime", "second")
            ).order_by("start_datetime"),
            [
                (start_datetime, start_datetime.second),
                (end_datetime, end_datetime.second),
            ],
            lambda m: (m.start_datetime, m.extracted),
        )
        self.assertEqual(
            DTModel.objects.filter(
                start_datetime__year=Extract("start_datetime", "year")
            ).count(),
            2,
        )
        self.assertEqual(
            DTModel.objects.filter(
                start_datetime__hour=Extract("start_datetime", "hour")
            ).count(),
            2,
        )
        self.assertEqual(
            DTModel.objects.filter(
                start_date__month=Extract("start_date", "month")
            ).count(),
            2,
        )
        self.assertEqual(
            DTModel.objects.filter(
                start_time__hour=Extract("start_time", "hour")
            ).count(),
            2,
        )

    def test_extract_none(self):
        self.create_model(None, None)
        for t in (
            Extract("start_datetime", "year"),
            Extract("start_date", "year"),
            Extract("start_time", "hour"),
        ):
            with self.subTest(t):
                self.assertIsNone(
                    DTModel.objects.annotate(extracted=t).first().extracted
                )

    def test_extract_outerref_validation(self):
        inner_qs = DTModel.objects.filter(name=ExtractMonth(OuterRef("name")))
        msg = (
            "Extract input expression must be DateField, DateTimeField, "
            "TimeField, or DurationField."
        )
        with self.assertRaisesMessage(ValueError, msg):
            DTModel.objects.annotate(related_name=Subquery(inner_qs.values("name")[:1]))

    @skipUnlessDBFeature("has_native_duration_field")
    def test_extract_duration(self):
        start_datetime = datetime.datetime(2015, 6, 15, 14, 30, 50, 321)
        end_datetime = datetime.datetime(2016, 6, 15, 14, 10, 50, 123)
        if settings.USE_TZ:
            start_datetime = timezone.make_aware(start_datetime)
            end_datetime = timezone.make_aware(end_datetime)
        self.create_model(start_datetime, end_datetime)
        self.create_model(end_datetime, start_datetime)
        self.assertQuerySetEqual(
            DTModel.objects.annotate(extracted=Extract("duration", "second")).order_by(
                "start_datetime"
            ),
            [
                (start_datetime, (end_datetime - start_datetime).seconds % 60),
                (end_datetime, (start_datetime - end_datetime).seconds % 60),
            ],
            lambda m: (m.start_datetime, m.extracted),
        )
        self.assertEqual(
            DTModel.objects.annotate(
                duration_days=Extract("duration", "day"),
            )
            .filter(duration_days__gt=200)
            .count(),
            1,
        )

    @skipIfDBFeature("has_native_duration_field")
    def test_extract_duration_without_native_duration_field(self):
        msg = "Extract requires native DurationField database support."
        with self.assertRaisesMessage(ValueError, msg):
            list(DTModel.objects.annotate(extracted=Extract("duration", "second")))

    def test_extract_duration_unsupported_lookups(self):
        msg = "Cannot extract component '%s' from DurationField 'duration'."
        for lookup in (
            "year",
            "iso_year",
            "month",
            "week",
            "week_day",
            "iso_week_day",
            "quarter",
        ):
            with self.subTest(lookup):
                with self.assertRaisesMessage(ValueError, msg % lookup):
                    DTModel.objects.annotate(extracted=Extract("duration", lookup))

    def test_extract_year_func(self):
        start_datetime = datetime.datetime(2015, 6, 15, 14, 30, 50, 321)
        end_datetime = datetime.datetime(2016, 6, 15, 14, 10, 50, 123)
        if settings.USE_TZ:
            start_datetime = timezone.make_aware(start_datetime)
            end_datetime = timezone.make_aware(end_datetime)
        self.create_model(start_datetime, end_datetime)
        self.create_model(end_datetime, start_datetime)
        self.assertQuerySetEqual(
            DTModel.objects.annotate(extracted=ExtractYear("start_datetime")).order_by(
                "start_datetime"
            ),
            [(start_datetime, start_datetime.year), (end_datetime, end_datetime.year)],
            lambda m: (m.start_datetime, m.extracted),
        )
        self.assertQuerySetEqual(
            DTModel.objects.annotate(extracted=ExtractYear("start_date")).order_by(
                "start_datetime"
            ),
            [(start_datetime, start_datetime.year), (end_datetime, end_datetime.year)],
            lambda m: (m.start_datetime, m.extracted),
        )
        self.assertEqual(
            DTModel.objects.filter(
                start_datetime__year=ExtractYear("start_datetime")
            ).count(),
            2,
        )

    def test_extract_iso_year_func(self):
        start_datetime = datetime.datetime(2015, 6, 15, 14, 30, 50, 321)
        end_datetime = datetime.datetime(2016, 6, 15, 14, 10, 50, 123)
        if settings.USE_TZ:
            start_datetime = timezone.make_aware(start_datetime)
            end_datetime = timezone.make_aware(end_datetime)
        self.create_model(start_datetime, end_datetime)
        self.create_model(end_datetime, start_datetime)
        self.assertQuerySetEqual(
            DTModel.objects.annotate(
                extracted=ExtractIsoYear("start_datetime")
            ).order_by("start_datetime"),
            [(start_datetime, start_datetime.year), (end_datetime, end_datetime.year)],
            lambda m: (m.start_datetime, m.extracted),
        )
        self.assertQuerySetEqual(
            DTModel.objects.annotate(extracted=ExtractIsoYear("start_date")).order_by(
                "start_datetime"
            ),
            [(start_datetime, start_datetime.year), (end_datetime, end_datetime.year)],
            lambda m: (m.start_datetime, m.extracted),
        )
        # Both dates are from the same week year.
        self.assertEqual(
            DTModel.objects.filter(
                start_datetime__iso_year=ExtractIsoYear("start_datetime")
            ).count(),
            2,
        )

    def test_extract_iso_year_func_boundaries(self):
        end_datetime = datetime.datetime(2016, 6, 15, 14, 10, 50, 123)
        if settings.USE_TZ:
            end_datetime = timezone.make_aware(end_datetime)
        week_52_day_2014 = datetime.datetime(2014, 12, 27, 13, 0)  # Sunday
        week_1_day_2014_2015 = datetime.datetime(2014, 12, 31, 13, 0)  # Wednesday
        week_53_day_2015 = datetime.datetime(2015, 12, 31, 13, 0)  # Thursday
        if settings.USE_TZ:
            week_1_day_2014_2015 = timezone.make_aware(week_1_day_2014_2015)
            week_52_day_2014 = timezone.make_aware(week_52_day_2014)
            week_53_day_2015 = timezone.make_aware(week_53_day_2015)
        days = [week_52_day_2014, week_1_day_2014_2015, week_53_day_2015]
        obj_1_iso_2014 = self.create_model(week_52_day_2014, end_datetime)
        obj_1_iso_2015 = self.create_model(week_1_day_2014_2015, end_datetime)
        obj_2_iso_2015 = self.create_model(week_53_day_2015, end_datetime)
        qs = (
            DTModel.objects.filter(start_datetime__in=days)
            .annotate(
                extracted=ExtractIsoYear("start_datetime"),
            )
            .order_by("start_datetime")
        )
        self.assertQuerySetEqual(
            qs,
            [
                (week_52_day_2014, 2014),
                (week_1_day_2014_2015, 2015),
                (week_53_day_2015, 2015),
            ],
            lambda m: (m.start_datetime, m.extracted),
        )

        qs = DTModel.objects.filter(
            start_datetime__iso_year=2015,
        ).order_by("start_datetime")
        self.assertSequenceEqual(qs, [obj_1_iso_2015, obj_2_iso_2015])
        qs = DTModel.objects.filter(
            start_datetime__iso_year__gt=2014,
        ).order_by("start_datetime")
        self.assertSequenceEqual(qs, [obj_1_iso_2015, obj_2_iso_2015])
        qs = DTModel.objects.filter(
            start_datetime__iso_year__lte=2014,
        ).order_by("start_datetime")
        self.assertSequenceEqual(qs, [obj_1_iso_2014])

    def test_extract_month_func(self):
        start_datetime = datetime.datetime(2015, 6, 15, 14, 30, 50, 321)
        end_datetime = datetime.datetime(2016, 6, 15, 14, 10, 50, 123)
        if settings.USE_TZ:
            start_datetime = timezone.make_aware(start_datetime)
            end_datetime = timezone.make_aware(end_datetime)
        self.create_model(start_datetime, end_datetime)
        self.create_model(end_datetime, start_datetime)
        self.assertQuerySetEqual(
            DTModel.objects.annotate(extracted=ExtractMonth("start_datetime")).order_by(
                "start_datetime"
            ),
            [
                (start_datetime, start_datetime.month),
                (end_datetime, end_datetime.month),
            ],
            lambda m: (m.start_datetime, m.extracted),
        )
        self.assertQuerySetEqual(
            DTModel.objects.annotate(extracted=ExtractMonth("start_date")).order_by(
                "start_datetime"
            ),
            [
                (start_datetime, start_datetime.month),
                (end_datetime, end_datetime.month),
            ],
            lambda m: (m.start_datetime, m.extracted),
        )
        self.assertEqual(
            DTModel.objects.filter(
                start_datetime__month=ExtractMonth("start_datetime")
            ).count(),
            2,
        )

    def test_extract_day_func(self):
        start_datetime = datetime.datetime(2015, 6, 15, 14, 30, 50, 321)
        end_datetime = datetime.datetime(2016, 6, 15, 14, 10, 50, 123)
        if settings.USE_TZ:
            start_datetime = timezone.make_aware(start_datetime)
            end_datetime = timezone.make_aware(end_datetime)
        self.create_model(start_datetime, end_datetime)
        self.create_model(end_datetime, start_datetime)
        self.assertQuerySetEqual(
            DTModel.objects.annotate(extracted=ExtractDay("start_datetime")).order_by(
                "start_datetime"
            ),
            [(start_datetime, start_datetime.day), (end_datetime, end_datetime.day)],
            lambda m: (m.start_datetime, m.extracted),
        )
        self.assertQuerySetEqual(
            DTModel.objects.annotate(extracted=ExtractDay("start_date")).order_by(
                "start_datetime"
            ),
            [(start_datetime, start_datetime.day), (end_datetime, end_datetime.day)],
            lambda m: (m.start_datetime, m.extracted),
        )
        self.assertEqual(
            DTModel.objects.filter(
                start_datetime__day=ExtractDay("start_datetime")
            ).count(),
            2,
        )

    def test_extract_week_func(self):
        start_datetime = datetime.datetime(2015, 6, 15, 14, 30, 50, 321)
        end_datetime = datetime.datetime(2016, 6, 15, 14, 10, 50, 123)
        if settings.USE_TZ:
            start_datetime = timezone.make_aware(start_datetime)
            end_datetime = timezone.make_aware(end_datetime)
        self.create_model(start_datetime, end_datetime)
        self.create_model(end_datetime, start_datetime)
        self.assertQuerySetEqual(
            DTModel.objects.annotate(extracted=ExtractWeek("start_datetime")).order_by(
                "start_datetime"
            ),
            [(start_datetime, 25), (end_datetime, 24)],
            lambda m: (m.start_datetime, m.extracted),
        )
        self.assertQuerySetEqual(
            DTModel.objects.annotate(extracted=ExtractWeek("start_date")).order_by(
                "start_datetime"
            ),
            [(start_datetime, 25), (end_datetime, 24)],
            lambda m: (m.start_datetime, m.extracted),
        )
        # both dates are from the same week.
        self.assertEqual(
            DTModel.objects.filter(
                start_datetime__week=ExtractWeek("start_datetime")
            ).count(),
            2,
        )

    def test_extract_quarter_func(self):
        start_datetime = datetime.datetime(2015, 6, 15, 14, 30, 50, 321)
        end_datetime = datetime.datetime(2016, 8, 15, 14, 10, 50, 123)
        if settings.USE_TZ:
            start_datetime = timezone.make_aware(start_datetime)
            end_datetime = timezone.make_aware(end_datetime)
        self.create_model(start_datetime, end_datetime)
        self.create_model(end_datetime, start_datetime)
        self.assertQuerySetEqual(
            DTModel.objects.annotate(
                extracted=ExtractQuarter("start_datetime")
            ).order_by("start_datetime"),
            [(start_datetime, 2), (end_datetime, 3)],
            lambda m: (m.start_datetime, m.extracted),
        )
        self.assertQuerySetEqual(
            DTModel.objects.annotate(extracted=ExtractQuarter("start_date")).order_by(
                "start_datetime"
            ),
            [(start_datetime, 2), (end_datetime, 3)],
            lambda m: (m.start_datetime, m.extracted),
        )
        self.assertEqual(
            DTModel.objects.filter(
                start_datetime__quarter=ExtractQuarter("start_datetime")
            ).count(),
            2,
        )

    def test_extract_quarter_func_boundaries(self):
        end_datetime = datetime.datetime(2016, 6, 15, 14, 10, 50, 123)
        if settings.USE_TZ:
            end_datetime = timezone.make_aware(end_datetime)

        last_quarter_2014 = datetime.datetime(2014, 12, 31, 13, 0)
        first_quarter_2015 = datetime.datetime(2015, 1, 1, 13, 0)
        if settings.USE_TZ:
            last_quarter_2014 = timezone.make_aware(last_quarter_2014)
            first_quarter_2015 = timezone.make_aware(first_quarter_2015)
        dates = [last_quarter_2014, first_quarter_2015]
        self.create_model(last_quarter_2014, end_datetime)
        self.create_model(first_quarter_2015, end_datetime)
        qs = (
            DTModel.objects.filter(start_datetime__in=dates)
            .annotate(
                extracted=ExtractQuarter("start_datetime"),
            )
            .order_by("start_datetime")
        )
        self.assertQuerySetEqual(
            qs,
            [
                (last_quarter_2014, 4),
                (first_quarter_2015, 1),
            ],
            lambda m: (m.start_datetime, m.extracted),
        )

    def test_extract_week_func_boundaries(self):
        end_datetime = datetime.datetime(2016, 6, 15, 14, 10, 50, 123)
        if settings.USE_TZ:
            end_datetime = timezone.make_aware(end_datetime)

        week_52_day_2014 = datetime.datetime(2014, 12, 27, 13, 0)  # Sunday
        week_1_day_2014_2015 = datetime.datetime(2014, 12, 31, 13, 0)  # Wednesday
        week_53_day_2015 = datetime.datetime(2015, 12, 31, 13, 0)  # Thursday
        if settings.USE_TZ:
            week_1_day_2014_2015 = timezone.make_aware(week_1_day_2014_2015)
            week_52_day_2014 = timezone.make_aware(week_52_day_2014)
            week_53_day_2015 = timezone.make_aware(week_53_day_2015)

        days = [week_52_day_2014, week_1_day_2014_2015, week_53_day_2015]
        self.create_model(week_53_day_2015, end_datetime)
        self.create_model(week_52_day_2014, end_datetime)
        self.create_model(week_1_day_2014_2015, end_datetime)
        qs = (
            DTModel.objects.filter(start_datetime__in=days)
            .annotate(
                extracted=ExtractWeek("start_datetime"),
            )
            .order_by("start_datetime")
        )
        self.assertQuerySetEqual(
            qs,
            [
                (week_52_day_2014, 52),
                (week_1_day_2014_2015, 1),
                (week_53_day_2015, 53),
            ],
            lambda m: (m.start_datetime, m.extracted),
        )

    def test_extract_weekday_func(self):
        start_datetime = datetime.datetime(2015, 6, 15, 14, 30, 50, 321)
        end_datetime = datetime.datetime(2016, 6, 15, 14, 10, 50, 123)
        if settings.USE_TZ:
            start_datetime = timezone.make_aware(start_datetime)
            end_datetime = timezone.make_aware(end_datetime)
        self.create_model(start_datetime, end_datetime)
        self.create_model(end_datetime, start_datetime)
        self.assertQuerySetEqual(
            DTModel.objects.annotate(
                extracted=ExtractWeekDay("start_datetime")
            ).order_by("start_datetime"),
            [
                (start_datetime, (start_datetime.isoweekday() % 7) + 1),
                (end_datetime, (end_datetime.isoweekday() % 7) + 1),
            ],
            lambda m: (m.start_datetime, m.extracted),
        )
        self.assertQuerySetEqual(
            DTModel.objects.annotate(extracted=ExtractWeekDay("start_date")).order_by(
                "start_datetime"
            ),
            [
                (start_datetime, (start_datetime.isoweekday() % 7) + 1),
                (end_datetime, (end_datetime.isoweekday() % 7) + 1),
            ],
            lambda m: (m.start_datetime, m.extracted),
        )
        self.assertEqual(
            DTModel.objects.filter(
                start_datetime__week_day=ExtractWeekDay("start_datetime")
            ).count(),
            2,
        )

    def test_extract_iso_weekday_func(self):
        start_datetime = datetime.datetime(2015, 6, 15, 14, 30, 50, 321)
        end_datetime = datetime.datetime(2016, 6, 15, 14, 10, 50, 123)
        if settings.USE_TZ:
            start_datetime = timezone.make_aware(start_datetime)
            end_datetime = timezone.make_aware(end_datetime)
        self.create_model(start_datetime, end_datetime)
        self.create_model(end_datetime, start_datetime)
        self.assertQuerySetEqual(
            DTModel.objects.annotate(
                extracted=ExtractIsoWeekDay("start_datetime"),
            ).order_by("start_datetime"),
            [
                (start_datetime, start_datetime.isoweekday()),
                (end_datetime, end_datetime.isoweekday()),
            ],
            lambda m: (m.start_datetime, m.extracted),
        )
        self.assertQuerySetEqual(
            DTModel.objects.annotate(
                extracted=ExtractIsoWeekDay("start_date"),
            ).order_by("start_datetime"),
            [
                (start_datetime, start_datetime.isoweekday()),
                (end_datetime, end_datetime.isoweekday()),
            ],
            lambda m: (m.start_datetime, m.extracted),
        )
        self.assertEqual(
            DTModel.objects.filter(
                start_datetime__week_day=ExtractWeekDay("start_datetime"),
            ).count(),
            2,
        )

    def test_extract_hour_func(self):
        start_datetime = datetime.datetime(2015, 6, 15, 14, 30, 50, 321)
        end_datetime = datetime.datetime(2016, 6, 15, 14, 10, 50, 123)
        if settings.USE_TZ:
            start_datetime = timezone.make_aware(start_datetime)
            end_datetime = timezone.make_aware(end_datetime)
        self.create_model(start_datetime, end_datetime)
        self.create_model(end_datetime, start_datetime)
        self.assertQuerySetEqual(
            DTModel.objects.annotate(extracted=ExtractHour("start_datetime")).order_by(
                "start_datetime"
            ),
            [(start_datetime, start_datetime.hour), (end_datetime, end_datetime.hour)],
            lambda m: (m.start_datetime, m.extracted),
        )
        self.assertQuerySetEqual(
            DTModel.objects.annotate(extracted=ExtractHour("start_time")).order_by(
                "start_datetime"
            ),
            [(start_datetime, start_datetime.hour), (end_datetime, end_datetime.hour)],
            lambda m: (m.start_datetime, m.extracted),
        )
        self.assertEqual(
            DTModel.objects.filter(
                start_datetime__hour=ExtractHour("start_datetime")
            ).count(),
            2,
        )

    def test_extract_minute_func(self):
        start_datetime = datetime.datetime(2015, 6, 15, 14, 30, 50, 321)
        end_datetime = datetime.datetime(2016, 6, 15, 14, 10, 50, 123)
        if settings.USE_TZ:
            start_datetime = timezone.make_aware(start_datetime)
            end_datetime = timezone.make_aware(end_datetime)
        self.create_model(start_datetime, end_datetime)
        self.create_model(end_datetime, start_datetime)
        self.assertQuerySetEqual(
            DTModel.objects.annotate(
                extracted=ExtractMinute("start_datetime")
            ).order_by("start_datetime"),
            [
                (start_datetime, start_datetime.minute),
                (end_datetime, end_datetime.minute),
            ],
            lambda m: (m.start_datetime, m.extracted),
        )
        self.assertQuerySetEqual(
            DTModel.objects.annotate(extracted=ExtractMinute("start_time")).order_by(
                "start_datetime"
            ),
            [
                (start_datetime, start_datetime.minute),
                (end_datetime, end_datetime.minute),
            ],
            lambda m: (m.start_datetime, m.extracted),
        )
        self.assertEqual(
            DTModel.objects.filter(
                start_datetime__minute=ExtractMinute("start_datetime")
            ).count(),
            2,
        )

    def test_extract_second_func(self):
        start_datetime = datetime.datetime(2015, 6, 15, 14, 30, 50, 321)
        end_datetime = datetime.datetime(2016, 6, 15, 14, 10, 50, 123)
        if settings.USE_TZ:
            start_datetime = timezone.make_aware(start_datetime)
            end_datetime = timezone.make_aware(end_datetime)
        self.create_model(start_datetime, end_datetime)
        self.create_model(end_datetime, start_datetime)
        self.assertQuerySetEqual(
            DTModel.objects.annotate(
                extracted=ExtractSecond("start_datetime")
            ).order_by("start_datetime"),
            [
                (start_datetime, start_datetime.second),
                (end_datetime, end_datetime.second),
            ],
            lambda m: (m.start_datetime, m.extracted),
        )
        self.assertQuerySetEqual(
            DTModel.objects.annotate(extracted=ExtractSecond("start_time")).order_by(
                "start_datetime"
            ),
            [
                (start_datetime, start_datetime.second),
                (end_datetime, end_datetime.second),
            ],
            lambda m: (m.start_datetime, m.extracted),
        )
        self.assertEqual(
            DTModel.objects.filter(
                start_datetime__second=ExtractSecond("start_datetime")
            ).count(),
            2,
        )

    def test_extract_second_func_no_fractional(self):
        start_datetime = datetime.datetime(2015, 6, 15, 14, 30, 50, 321)
        end_datetime = datetime.datetime(2016, 6, 15, 14, 30, 50, 783)
        if settings.USE_TZ:
            start_datetime = timezone.make_aware(start_datetime)
            end_datetime = timezone.make_aware(end_datetime)
        obj = self.create_model(start_datetime, end_datetime)
        self.assertSequenceEqual(
            DTModel.objects.filter(start_datetime__second=F("end_datetime__second")),
            [obj],
        )
        self.assertSequenceEqual(
            DTModel.objects.filter(start_time__second=F("end_time__second")),
            [obj],
        )

    def test_trunc_lookup_name_sql_injection(self):
        start_datetime = datetime.datetime(2015, 6, 15, 14, 30, 50, 321)
        end_datetime = datetime.datetime(2016, 6, 15, 14, 10, 50, 123)
        if settings.USE_TZ:
            start_datetime = timezone.make_aware(start_datetime)
            end_datetime = timezone.make_aware(end_datetime)
        self.create_model(start_datetime, end_datetime)
        self.create_model(end_datetime, start_datetime)
        # Database backends raise an exception or don't return any results.
        try:
            exists = DTModel.objects.filter(
                start_datetime__date=Trunc(
                    "start_datetime",
                    "year', start_datetime)) OR 1=1;--",
                )
            ).exists()
        except (DataError, OperationalError):
            pass
        else:
            self.assertIs(exists, False)

    def test_trunc_func(self):
        start_datetime = datetime.datetime(999, 6, 15, 14, 30, 50, 321)
        end_datetime = datetime.datetime(2016, 6, 15, 14, 10, 50, 123)
        if settings.USE_TZ:
            start_datetime = timezone.make_aware(start_datetime)
            end_datetime = timezone.make_aware(end_datetime)
        self.create_model(start_datetime, end_datetime)
        self.create_model(end_datetime, start_datetime)

        def assertDatetimeKind(kind):
            truncated_start = truncate_to(start_datetime, kind)
            truncated_end = truncate_to(end_datetime, kind)
            queryset = DTModel.objects.annotate(
                truncated=Trunc("start_datetime", kind, output_field=DateTimeField())
            ).order_by("start_datetime")
            self.assertSequenceEqual(
                queryset.values_list("start_datetime", "truncated"),
                [
                    (start_datetime, truncated_start),
                    (end_datetime, truncated_end),
                ],
            )

        def assertDateKind(kind):
            truncated_start = truncate_to(start_datetime.date(), kind)
            truncated_end = truncate_to(end_datetime.date(), kind)
            queryset = DTModel.objects.annotate(
                truncated=Trunc("start_date", kind, output_field=DateField())
            ).order_by("start_datetime")
            self.assertSequenceEqual(
                queryset.values_list("start_datetime", "truncated"),
                [
                    (start_datetime, truncated_start),
                    (end_datetime, truncated_end),
                ],
            )

        def assertTimeKind(kind):
            truncated_start = truncate_to(start_datetime.time(), kind)
            truncated_end = truncate_to(end_datetime.time(), kind)
            queryset = DTModel.objects.annotate(
                truncated=Trunc("start_time", kind, output_field=TimeField())
            ).order_by("start_datetime")
            self.assertSequenceEqual(
                queryset.values_list("start_datetime", "truncated"),
                [
                    (start_datetime, truncated_start),
                    (end_datetime, truncated_end),
                ],
            )

        def assertDatetimeToTimeKind(kind):
            truncated_start = truncate_to(start_datetime.time(), kind)
            truncated_end = truncate_to(end_datetime.time(), kind)
            queryset = DTModel.objects.annotate(
                truncated=Trunc("start_datetime", kind, output_field=TimeField()),
            ).order_by("start_datetime")
            self.assertSequenceEqual(
                queryset.values_list("start_datetime", "truncated"),
                [
                    (start_datetime, truncated_start),
                    (end_datetime, truncated_end),
                ],
            )

        date_truncations = ["year", "quarter", "month", "day"]
        time_truncations = ["hour", "minute", "second"]
        tests = [
            (assertDateKind, date_truncations),
            (assertTimeKind, time_truncations),
            (assertDatetimeKind, [*date_truncations, *time_truncations]),
            (assertDatetimeToTimeKind, time_truncations),
        ]
        for assertion, truncations in tests:
            for truncation in truncations:
                with self.subTest(assertion=assertion.__name__, truncation=truncation):
                    assertion(truncation)

        qs = DTModel.objects.filter(
            start_datetime__date=Trunc(
                "start_datetime", "day", output_field=DateField()
            )
        )
        self.assertEqual(qs.count(), 2)

    def _test_trunc_week(self, start_datetime, end_datetime):
        if settings.USE_TZ:
            start_datetime = timezone.make_aware(start_datetime)
            end_datetime = timezone.make_aware(end_datetime)
        self.create_model(start_datetime, end_datetime)
        self.create_model(end_datetime, start_datetime)

        self.assertQuerySetEqual(
            DTModel.objects.annotate(
                truncated=Trunc("start_datetime", "week", output_field=DateTimeField())
            ).order_by("start_datetime"),
            [
                (start_datetime, truncate_to(start_datetime, "week")),
                (end_datetime, truncate_to(end_datetime, "week")),
            ],
            lambda m: (m.start_datetime, m.truncated),
        )
        self.assertQuerySetEqual(
            DTModel.objects.annotate(
                truncated=Trunc("start_date", "week", output_field=DateField())
            ).order_by("start_datetime"),
            [
                (start_datetime, truncate_to(start_datetime.date(), "week")),
                (end_datetime, truncate_to(end_datetime.date(), "week")),
            ],
            lambda m: (m.start_datetime, m.truncated),
        )

    def test_trunc_week(self):
        self._test_trunc_week(
            start_datetime=datetime.datetime(2015, 6, 15, 14, 30, 50, 321),
            end_datetime=datetime.datetime(2016, 6, 15, 14, 10, 50, 123),
        )

    def test_trunc_week_before_1000(self):
        self._test_trunc_week(
            start_datetime=datetime.datetime(999, 6, 15, 14, 30, 50, 321),
            end_datetime=datetime.datetime(2016, 6, 15, 14, 10, 50, 123),
        )

    def test_trunc_invalid_arguments(self):
        msg = "output_field must be either DateField, TimeField, or DateTimeField"
        with self.assertRaisesMessage(ValueError, msg):
            list(
                DTModel.objects.annotate(
                    truncated=Trunc(
                        "start_datetime", "year", output_field=IntegerField()
                    ),
                )
            )
        msg = "'name' isn't a DateField, TimeField, or DateTimeField."
        with self.assertRaisesMessage(TypeError, msg):
            list(
                DTModel.objects.annotate(
                    truncated=Trunc("name", "year", output_field=DateTimeField()),
                )
            )
        msg = "Cannot truncate DateField 'start_date' to DateTimeField"
        with self.assertRaisesMessage(ValueError, msg):
            list(DTModel.objects.annotate(truncated=Trunc("start_date", "second")))
        with self.assertRaisesMessage(ValueError, msg):
            list(
                DTModel.objects.annotate(
                    truncated=Trunc(
                        "start_date", "month", output_field=DateTimeField()
                    ),
                )
            )
        msg = "Cannot truncate TimeField 'start_time' to DateTimeField"
        with self.assertRaisesMessage(ValueError, msg):
            list(DTModel.objects.annotate(truncated=Trunc("start_time", "month")))
        with self.assertRaisesMessage(ValueError, msg):
            list(
                DTModel.objects.annotate(
                    truncated=Trunc(
                        "start_time", "second", output_field=DateTimeField()
                    ),
                )
            )

    def test_trunc_none(self):
        self.create_model(None, None)
        for t in (
            Trunc("start_datetime", "year"),
            Trunc("start_date", "year"),
            Trunc("start_time", "hour"),
        ):
            with self.subTest(t):
                self.assertIsNone(
                    DTModel.objects.annotate(truncated=t).first().truncated
                )

    def test_trunc_year_func(self):
        start_datetime = datetime.datetime(2015, 6, 15, 14, 30, 50, 321)
        end_datetime = truncate_to(
            datetime.datetime(2016, 6, 15, 14, 10, 50, 123), "year"
        )
        if settings.USE_TZ:
            start_datetime = timezone.make_aware(start_datetime)
            end_datetime = timezone.make_aware(end_datetime)
        self.create_model(start_datetime, end_datetime)
        self.create_model(end_datetime, start_datetime)
        self.assertQuerySetEqual(
            DTModel.objects.annotate(extracted=TruncYear("start_datetime")).order_by(
                "start_datetime"
            ),
            [
                (start_datetime, truncate_to(start_datetime, "year")),
                (end_datetime, truncate_to(end_datetime, "year")),
            ],
            lambda m: (m.start_datetime, m.extracted),
        )
        self.assertQuerySetEqual(
            DTModel.objects.annotate(extracted=TruncYear("start_date")).order_by(
                "start_datetime"
            ),
            [
                (start_datetime, truncate_to(start_datetime.date(), "year")),
                (end_datetime, truncate_to(end_datetime.date(), "year")),
            ],
            lambda m: (m.start_datetime, m.extracted),
        )
        self.assertEqual(
            DTModel.objects.filter(start_datetime=TruncYear("start_datetime")).count(),
            1,
        )

        with self.assertRaisesMessage(
            ValueError, "Cannot truncate TimeField 'start_time' to DateTimeField"
        ):
            list(DTModel.objects.annotate(truncated=TruncYear("start_time")))

        with self.assertRaisesMessage(
            ValueError, "Cannot truncate TimeField 'start_time' to DateTimeField"
        ):
            list(
                DTModel.objects.annotate(
                    truncated=TruncYear("start_time", output_field=TimeField())
                )
            )

    def test_trunc_quarter_func(self):
        start_datetime = datetime.datetime(2015, 6, 15, 14, 30, 50, 321)
        end_datetime = truncate_to(
            datetime.datetime(2016, 10, 15, 14, 10, 50, 123), "quarter"
        )
        last_quarter_2015 = truncate_to(
            datetime.datetime(2015, 12, 31, 14, 10, 50, 123), "quarter"
        )
        first_quarter_2016 = truncate_to(
            datetime.datetime(2016, 1, 1, 14, 10, 50, 123), "quarter"
        )
        if settings.USE_TZ:
            start_datetime = timezone.make_aware(start_datetime)
            end_datetime = timezone.make_aware(end_datetime)
            last_quarter_2015 = timezone.make_aware(last_quarter_2015)
            first_quarter_2016 = timezone.make_aware(first_quarter_2016)
        self.create_model(start_datetime=start_datetime, end_datetime=end_datetime)
        self.create_model(start_datetime=end_datetime, end_datetime=start_datetime)
        self.create_model(start_datetime=last_quarter_2015, end_datetime=end_datetime)
        self.create_model(start_datetime=first_quarter_2016, end_datetime=end_datetime)
        self.assertQuerySetEqual(
            DTModel.objects.annotate(extracted=TruncQuarter("start_date")).order_by(
                "start_datetime"
            ),
            [
                (start_datetime, truncate_to(start_datetime.date(), "quarter")),
                (last_quarter_2015, truncate_to(last_quarter_2015.date(), "quarter")),
                (first_quarter_2016, truncate_to(first_quarter_2016.date(), "quarter")),
                (end_datetime, truncate_to(end_datetime.date(), "quarter")),
            ],
            lambda m: (m.start_datetime, m.extracted),
        )
        self.assertQuerySetEqual(
            DTModel.objects.annotate(extracted=TruncQuarter("start_datetime")).order_by(
                "start_datetime"
            ),
            [
                (start_datetime, truncate_to(start_datetime, "quarter")),
                (last_quarter_2015, truncate_to(last_quarter_2015, "quarter")),
                (first_quarter_2016, truncate_to(first_quarter_2016, "quarter")),
                (end_datetime, truncate_to(end_datetime, "quarter")),
            ],
            lambda m: (m.start_datetime, m.extracted),
        )

        with self.assertRaisesMessage(
            ValueError, "Cannot truncate TimeField 'start_time' to DateTimeField"
        ):
            list(DTModel.objects.annotate(truncated=TruncQuarter("start_time")))

        with self.assertRaisesMessage(
            ValueError, "Cannot truncate TimeField 'start_time' to DateTimeField"
        ):
            list(
                DTModel.objects.annotate(
                    truncated=TruncQuarter("start_time", output_field=TimeField())
                )
            )

    def test_trunc_month_func(self):
        start_datetime = datetime.datetime(2015, 6, 15, 14, 30, 50, 321)
        end_datetime = truncate_to(
            datetime.datetime(2016, 6, 15, 14, 10, 50, 123), "month"
        )
        if settings.USE_TZ:
            start_datetime = timezone.make_aware(start_datetime)
            end_datetime = timezone.make_aware(end_datetime)
        self.create_model(start_datetime, end_datetime)
        self.create_model(end_datetime, start_datetime)
        self.assertQuerySetEqual(
            DTModel.objects.annotate(extracted=TruncMonth("start_datetime")).order_by(
                "start_datetime"
            ),
            [
                (start_datetime, truncate_to(start_datetime, "month")),
                (end_datetime, truncate_to(end_datetime, "month")),
            ],
            lambda m: (m.start_datetime, m.extracted),
        )
        self.assertQuerySetEqual(
            DTModel.objects.annotate(extracted=TruncMonth("start_date")).order_by(
                "start_datetime"
            ),
            [
                (start_datetime, truncate_to(start_datetime.date(), "month")),
                (end_datetime, truncate_to(end_datetime.date(), "month")),
            ],
            lambda m: (m.start_datetime, m.extracted),
        )
        self.assertEqual(
            DTModel.objects.filter(start_datetime=TruncMonth("start_datetime")).count(),
            1,
        )

        with self.assertRaisesMessage(
            ValueError, "Cannot truncate TimeField 'start_time' to DateTimeField"
        ):
            list(DTModel.objects.annotate(truncated=TruncMonth("start_time")))

        with self.assertRaisesMessage(
            ValueError, "Cannot truncate TimeField 'start_time' to DateTimeField"
        ):
            list(
                DTModel.objects.annotate(
                    truncated=TruncMonth("start_time", output_field=TimeField())
                )
            )

    def test_trunc_week_func(self):
        start_datetime = datetime.datetime(2015, 6, 15, 14, 30, 50, 321)
        end_datetime = truncate_to(
            datetime.datetime(2016, 6, 15, 14, 10, 50, 123), "week"
        )
        if settings.USE_TZ:
            start_datetime = timezone.make_aware(start_datetime)
            end_datetime = timezone.make_aware(end_datetime)
        self.create_model(start_datetime, end_datetime)
        self.create_model(end_datetime, start_datetime)
        self.assertQuerySetEqual(
            DTModel.objects.annotate(extracted=TruncWeek("start_datetime")).order_by(
                "start_datetime"
            ),
            [
                (start_datetime, truncate_to(start_datetime, "week")),
                (end_datetime, truncate_to(end_datetime, "week")),
            ],
            lambda m: (m.start_datetime, m.extracted),
        )
        self.assertEqual(
            DTModel.objects.filter(start_datetime=TruncWeek("start_datetime")).count(),
            1,
        )

        with self.assertRaisesMessage(
            ValueError, "Cannot truncate TimeField 'start_time' to DateTimeField"
        ):
            list(DTModel.objects.annotate(truncated=TruncWeek("start_time")))

        with self.assertRaisesMessage(
            ValueError, "Cannot truncate TimeField 'start_time' to DateTimeField"
        ):
            list(
                DTModel.objects.annotate(
                    truncated=TruncWeek("start_time", output_field=TimeField())
                )
            )

    def test_trunc_date_func(self):
        start_datetime = datetime.datetime(2015, 6, 15, 14, 30, 50, 321)
        end_datetime = datetime.datetime(2016, 6, 15, 14, 10, 50, 123)
        if settings.USE_TZ:
            start_datetime = timezone.make_aware(start_datetime)
            end_datetime = timezone.make_aware(end_datetime)
        self.create_model(start_datetime, end_datetime)
        self.create_model(end_datetime, start_datetime)
        self.assertQuerySetEqual(
            DTModel.objects.annotate(extracted=TruncDate("start_datetime")).order_by(
                "start_datetime"
            ),
            [
                (start_datetime, start_datetime.date()),
                (end_datetime, end_datetime.date()),
            ],
            lambda m: (m.start_datetime, m.extracted),
        )
        self.assertEqual(
            DTModel.objects.filter(
                start_datetime__date=TruncDate("start_datetime")
            ).count(),
            2,
        )

        with self.assertRaisesMessage(
            ValueError, "Cannot truncate TimeField 'start_time' to DateField"
        ):
            list(DTModel.objects.annotate(truncated=TruncDate("start_time")))

        with self.assertRaisesMessage(
            ValueError, "Cannot truncate TimeField 'start_time' to DateField"
        ):
            list(
                DTModel.objects.annotate(
                    truncated=TruncDate("start_time", output_field=TimeField())
                )
            )

    def test_trunc_date_none(self):
        self.create_model(None, None)
        self.assertIsNone(
            DTModel.objects.annotate(truncated=TruncDate("start_datetime"))
            .first()
            .truncated
        )

    def test_trunc_time_func(self):
        start_datetime = datetime.datetime(2015, 6, 15, 14, 30, 50, 321)
        end_datetime = datetime.datetime(2016, 6, 15, 14, 10, 50, 123)
        if settings.USE_TZ:
            start_datetime = timezone.make_aware(start_datetime)
            end_datetime = timezone.make_aware(end_datetime)
        self.create_model(start_datetime, end_datetime)
        self.create_model(end_datetime, start_datetime)
        self.assertQuerySetEqual(
            DTModel.objects.annotate(extracted=TruncTime("start_datetime")).order_by(
                "start_datetime"
            ),
            [
                (start_datetime, start_datetime.time()),
                (end_datetime, end_datetime.time()),
            ],
            lambda m: (m.start_datetime, m.extracted),
        )
        self.assertEqual(
            DTModel.objects.filter(
                start_datetime__time=TruncTime("start_datetime")
            ).count(),
            2,
        )

        with self.assertRaisesMessage(
            ValueError, "Cannot truncate DateField 'start_date' to TimeField"
        ):
            list(DTModel.objects.annotate(truncated=TruncTime("start_date")))

        with self.assertRaisesMessage(
            ValueError, "Cannot truncate DateField 'start_date' to TimeField"
        ):
            list(
                DTModel.objects.annotate(
                    truncated=TruncTime("start_date", output_field=DateField())
                )
            )

    def test_trunc_time_none(self):
        self.create_model(None, None)
        self.assertIsNone(
            DTModel.objects.annotate(truncated=TruncTime("start_datetime"))
            .first()
            .truncated
        )

    def test_trunc_time_comparison(self):
        start_datetime = datetime.datetime(2015, 6, 15, 14, 30, 26)  # 0 microseconds.
        end_datetime = datetime.datetime(2015, 6, 15, 14, 30, 26, 321)
        if settings.USE_TZ:
            start_datetime = timezone.make_aware(start_datetime)
            end_datetime = timezone.make_aware(end_datetime)
        self.create_model(start_datetime, end_datetime)
        self.assertIs(
            DTModel.objects.filter(
                start_datetime__time=start_datetime.time(),
                end_datetime__time=end_datetime.time(),
            ).exists(),
            True,
        )
        self.assertIs(
            DTModel.objects.annotate(
                extracted_start=TruncTime("start_datetime"),
                extracted_end=TruncTime("end_datetime"),
            )
            .filter(
                extracted_start=start_datetime.time(),
                extracted_end=end_datetime.time(),
            )
            .exists(),
            True,
        )

    def test_trunc_day_func(self):
        start_datetime = datetime.datetime(2015, 6, 15, 14, 30, 50, 321)
        end_datetime = truncate_to(
            datetime.datetime(2016, 6, 15, 14, 10, 50, 123), "day"
        )
        if settings.USE_TZ:
            start_datetime = timezone.make_aware(start_datetime)
            end_datetime = timezone.make_aware(end_datetime)
        self.create_model(start_datetime, end_datetime)
        self.create_model(end_datetime, start_datetime)
        self.assertQuerySetEqual(
            DTModel.objects.annotate(extracted=TruncDay("start_datetime")).order_by(
                "start_datetime"
            ),
            [
                (start_datetime, truncate_to(start_datetime, "day")),
                (end_datetime, truncate_to(end_datetime, "day")),
            ],
            lambda m: (m.start_datetime, m.extracted),
        )
        self.assertEqual(
            DTModel.objects.filter(start_datetime=TruncDay("start_datetime")).count(), 1
        )

        with self.assertRaisesMessage(
            ValueError, "Cannot truncate TimeField 'start_time' to DateTimeField"
        ):
            list(DTModel.objects.annotate(truncated=TruncDay("start_time")))

        with self.assertRaisesMessage(
            ValueError, "Cannot truncate TimeField 'start_time' to DateTimeField"
        ):
            list(
                DTModel.objects.annotate(
                    truncated=TruncDay("start_time", output_field=TimeField())
                )
            )

    def test_trunc_hour_func(self):
        start_datetime = datetime.datetime(2015, 6, 15, 14, 30, 50, 321)
        end_datetime = truncate_to(
            datetime.datetime(2016, 6, 15, 14, 10, 50, 123), "hour"
        )
        if settings.USE_TZ:
            start_datetime = timezone.make_aware(start_datetime)
            end_datetime = timezone.make_aware(end_datetime)
        self.create_model(start_datetime, end_datetime)
        self.create_model(end_datetime, start_datetime)
        self.assertQuerySetEqual(
            DTModel.objects.annotate(extracted=TruncHour("start_datetime")).order_by(
                "start_datetime"
            ),
            [
                (start_datetime, truncate_to(start_datetime, "hour")),
                (end_datetime, truncate_to(end_datetime, "hour")),
            ],
            lambda m: (m.start_datetime, m.extracted),
        )
        self.assertQuerySetEqual(
            DTModel.objects.annotate(extracted=TruncHour("start_time")).order_by(
                "start_datetime"
            ),
            [
                (start_datetime, truncate_to(start_datetime.time(), "hour")),
                (end_datetime, truncate_to(end_datetime.time(), "hour")),
            ],
            lambda m: (m.start_datetime, m.extracted),
        )
        self.assertEqual(
            DTModel.objects.filter(start_datetime=TruncHour("start_datetime")).count(),
            1,
        )

        with self.assertRaisesMessage(
            ValueError, "Cannot truncate DateField 'start_date' to DateTimeField"
        ):
            list(DTModel.objects.annotate(truncated=TruncHour("start_date")))

        with self.assertRaisesMessage(
            ValueError, "Cannot truncate DateField 'start_date' to DateTimeField"
        ):
            list(
                DTModel.objects.annotate(
                    truncated=TruncHour("start_date", output_field=DateField())
                )
            )

    def test_trunc_minute_func(self):
        start_datetime = datetime.datetime(2015, 6, 15, 14, 30, 50, 321)
        end_datetime = truncate_to(
            datetime.datetime(2016, 6, 15, 14, 10, 50, 123), "minute"
        )
        if settings.USE_TZ:
            start_datetime = timezone.make_aware(start_datetime)
            end_datetime = timezone.make_aware(end_datetime)
        self.create_model(start_datetime, end_datetime)
        self.create_model(end_datetime, start_datetime)
        self.assertQuerySetEqual(
            DTModel.objects.annotate(extracted=TruncMinute("start_datetime")).order_by(
                "start_datetime"
            ),
            [
                (start_datetime, truncate_to(start_datetime, "minute")),
                (end_datetime, truncate_to(end_datetime, "minute")),
            ],
            lambda m: (m.start_datetime, m.extracted),
        )
        self.assertQuerySetEqual(
            DTModel.objects.annotate(extracted=TruncMinute("start_time")).order_by(
                "start_datetime"
            ),
            [
                (start_datetime, truncate_to(start_datetime.time(), "minute")),
                (end_datetime, truncate_to(end_datetime.time(), "minute")),
            ],
            lambda m: (m.start_datetime, m.extracted),
        )
        self.assertEqual(
            DTModel.objects.filter(
                start_datetime=TruncMinute("start_datetime")
            ).count(),
            1,
        )

        with self.assertRaisesMessage(
            ValueError, "Cannot truncate DateField 'start_date' to DateTimeField"
        ):
            list(DTModel.objects.annotate(truncated=TruncMinute("start_date")))

        with self.assertRaisesMessage(
            ValueError, "Cannot truncate DateField 'start_date' to DateTimeField"
        ):
            list(
                DTModel.objects.annotate(
                    truncated=TruncMinute("start_date", output_field=DateField())
                )
            )

    def test_trunc_second_func(self):
        start_datetime = datetime.datetime(2015, 6, 15, 14, 30, 50, 321)
        end_datetime = truncate_to(
            datetime.datetime(2016, 6, 15, 14, 10, 50, 123), "second"
        )
        if settings.USE_TZ:
            start_datetime = timezone.make_aware(start_datetime)
            end_datetime = timezone.make_aware(end_datetime)
        self.create_model(start_datetime, end_datetime)
        self.create_model(end_datetime, start_datetime)
        self.assertQuerySetEqual(
            DTModel.objects.annotate(extracted=TruncSecond("start_datetime")).order_by(
                "start_datetime"
            ),
            [
                (start_datetime, truncate_to(start_datetime, "second")),
                (end_datetime, truncate_to(end_datetime, "second")),
            ],
            lambda m: (m.start_datetime, m.extracted),
        )
        self.assertQuerySetEqual(
            DTModel.objects.annotate(extracted=TruncSecond("start_time")).order_by(
                "start_datetime"
            ),
            [
                (start_datetime, truncate_to(start_datetime.time(), "second")),
                (end_datetime, truncate_to(end_datetime.time(), "second")),
            ],
            lambda m: (m.start_datetime, m.extracted),
        )
        self.assertEqual(
            DTModel.objects.filter(
                start_datetime=TruncSecond("start_datetime")
            ).count(),
            1,
        )

        with self.assertRaisesMessage(
            ValueError, "Cannot truncate DateField 'start_date' to DateTimeField"
        ):
            list(DTModel.objects.annotate(truncated=TruncSecond("start_date")))

        with self.assertRaisesMessage(
            ValueError, "Cannot truncate DateField 'start_date' to DateTimeField"
        ):
            list(
                DTModel.objects.annotate(
                    truncated=TruncSecond("start_date", output_field=DateField())
                )
            )

    def test_trunc_subquery_with_parameters(self):
        author_1 = Author.objects.create(name="J. R. R. Tolkien")
        author_2 = Author.objects.create(name="G. R. R. Martin")
        fan_since_1 = datetime.datetime(2016, 2, 3, 15, 0, 0)
        fan_since_2 = datetime.datetime(2015, 2, 3, 15, 0, 0)
        fan_since_3 = datetime.datetime(2017, 2, 3, 15, 0, 0)
        if settings.USE_TZ:
            fan_since_1 = timezone.make_aware(fan_since_1)
            fan_since_2 = timezone.make_aware(fan_since_2)
            fan_since_3 = timezone.make_aware(fan_since_3)
        Fan.objects.create(author=author_1, name="Tom", fan_since=fan_since_1)
        Fan.objects.create(author=author_1, name="Emma", fan_since=fan_since_2)
        Fan.objects.create(author=author_2, name="Isabella", fan_since=fan_since_3)

        inner = (
            Fan.objects.filter(
                author=OuterRef("pk"), name__in=("Emma", "Isabella", "Tom")
            )
            .values("author")
            .annotate(newest_fan=Max("fan_since"))
            .values("newest_fan")
        )
        outer = Author.objects.annotate(
            newest_fan_year=TruncYear(Subquery(inner, output_field=DateTimeField()))
        )
        tz = datetime.UTC if settings.USE_TZ else None
        self.assertSequenceEqual(
            outer.order_by("name").values("name", "newest_fan_year"),
            [
                {
                    "name": "G. R. R. Martin",
                    "newest_fan_year": datetime.datetime(2017, 1, 1, 0, 0, tzinfo=tz),
                },
                {
                    "name": "J. R. R. Tolkien",
                    "newest_fan_year": datetime.datetime(2016, 1, 1, 0, 0, tzinfo=tz),
                },
            ],
        )

    def test_extract_outerref(self):
        datetime_1 = datetime.datetime(2000, 1, 1)
        datetime_2 = datetime.datetime(2001, 3, 5)
        datetime_3 = datetime.datetime(2002, 1, 3)
        if settings.USE_TZ:
            datetime_1 = timezone.make_aware(datetime_1)
            datetime_2 = timezone.make_aware(datetime_2)
            datetime_3 = timezone.make_aware(datetime_3)
        obj_1 = self.create_model(datetime_1, datetime_3)
        obj_2 = self.create_model(datetime_2, datetime_1)
        obj_3 = self.create_model(datetime_3, datetime_2)

        inner_qs = DTModel.objects.filter(
            start_datetime__year=2000,
            start_datetime__month=ExtractMonth(OuterRef("end_datetime")),
        )
        qs = DTModel.objects.annotate(
            related_pk=Subquery(inner_qs.values("pk")[:1]),
        )
        self.assertSequenceEqual(
            qs.order_by("name").values("pk", "related_pk"),
            [
                {"pk": obj_1.pk, "related_pk": obj_1.pk},
                {"pk": obj_2.pk, "related_pk": obj_1.pk},
                {"pk": obj_3.pk, "related_pk": None},
            ],
        )


@override_settings(USE_TZ=True, TIME_ZONE="UTC")
class DateFunctionWithTimeZoneTests(DateFunctionTests):
    def test_extract_func_with_timezone(self):
        start_datetime = datetime.datetime(2015, 6, 15, 23, 30, 1, 321)
        end_datetime = datetime.datetime(2015, 6, 16, 13, 11, 27, 123)
        start_datetime = timezone.make_aware(start_datetime)
        end_datetime = timezone.make_aware(end_datetime)
        self.create_model(start_datetime, end_datetime)
        delta_tzinfo_pos = datetime.timezone(datetime.timedelta(hours=5))
        delta_tzinfo_neg = datetime.timezone(datetime.timedelta(hours=-5, minutes=17))
        melb = zoneinfo.ZoneInfo("Australia/Melbourne")

        qs = DTModel.objects.annotate(
            day=Extract("start_datetime", "day"),
            day_melb=Extract("start_datetime", "day", tzinfo=melb),
            week=Extract("start_datetime", "week", tzinfo=melb),
            isoyear=ExtractIsoYear("start_datetime", tzinfo=melb),
            weekday=ExtractWeekDay("start_datetime"),
            weekday_melb=ExtractWeekDay("start_datetime", tzinfo=melb),
            isoweekday=ExtractIsoWeekDay("start_datetime"),
            isoweekday_melb=ExtractIsoWeekDay("start_datetime", tzinfo=melb),
            quarter=ExtractQuarter("start_datetime", tzinfo=melb),
            hour=ExtractHour("start_datetime"),
            hour_melb=ExtractHour("start_datetime", tzinfo=melb),
            hour_with_delta_pos=ExtractHour("start_datetime", tzinfo=delta_tzinfo_pos),
            hour_with_delta_neg=ExtractHour("start_datetime", tzinfo=delta_tzinfo_neg),
            minute_with_delta_neg=ExtractMinute(
                "start_datetime", tzinfo=delta_tzinfo_neg
            ),
        ).order_by("start_datetime")

        utc_model = qs.get()
        self.assertEqual(utc_model.day, 15)
        self.assertEqual(utc_model.day_melb, 16)
        self.assertEqual(utc_model.week, 25)
        self.assertEqual(utc_model.isoyear, 2015)
        self.assertEqual(utc_model.weekday, 2)
        self.assertEqual(utc_model.weekday_melb, 3)
        self.assertEqual(utc_model.isoweekday, 1)
        self.assertEqual(utc_model.isoweekday_melb, 2)
        self.assertEqual(utc_model.quarter, 2)
        self.assertEqual(utc_model.hour, 23)
        self.assertEqual(utc_model.hour_melb, 9)
        self.assertEqual(utc_model.hour_with_delta_pos, 4)
        self.assertEqual(utc_model.hour_with_delta_neg, 18)
        self.assertEqual(utc_model.minute_with_delta_neg, 47)

        with timezone.override(melb):
            melb_model = qs.get()

        self.assertEqual(melb_model.day, 16)
        self.assertEqual(melb_model.day_melb, 16)
        self.assertEqual(melb_model.week, 25)
        self.assertEqual(melb_model.isoyear, 2015)
        self.assertEqual(melb_model.weekday, 3)
        self.assertEqual(melb_model.isoweekday, 2)
        self.assertEqual(melb_model.quarter, 2)
        self.assertEqual(melb_model.weekday_melb, 3)
        self.assertEqual(melb_model.isoweekday_melb, 2)
        self.assertEqual(melb_model.hour, 9)
        self.assertEqual(melb_model.hour_melb, 9)

    def test_extract_func_with_timezone_minus_no_offset(self):
        start_datetime = datetime.datetime(2015, 6, 15, 23, 30, 1, 321)
        end_datetime = datetime.datetime(2015, 6, 16, 13, 11, 27, 123)
        start_datetime = timezone.make_aware(start_datetime)
        end_datetime = timezone.make_aware(end_datetime)
        self.create_model(start_datetime, end_datetime)
        ust_nera = zoneinfo.ZoneInfo("Asia/Ust-Nera")

        qs = DTModel.objects.annotate(
            hour=ExtractHour("start_datetime"),
            hour_tz=ExtractHour("start_datetime", tzinfo=ust_nera),
        ).order_by("start_datetime")

        utc_model = qs.get()
        self.assertEqual(utc_model.hour, 23)
        self.assertEqual(utc_model.hour_tz, 9)

        with timezone.override(ust_nera):
            ust_nera_model = qs.get()

        self.assertEqual(ust_nera_model.hour, 9)
        self.assertEqual(ust_nera_model.hour_tz, 9)

    def test_extract_func_explicit_timezone_priority(self):
        start_datetime = datetime.datetime(2015, 6, 15, 23, 30, 1, 321)
        end_datetime = datetime.datetime(2015, 6, 16, 13, 11, 27, 123)
        start_datetime = timezone.make_aware(start_datetime)
        end_datetime = timezone.make_aware(end_datetime)
        self.create_model(start_datetime, end_datetime)
        melb = zoneinfo.ZoneInfo("Australia/Melbourne")
        with timezone.override(melb):
            model = (
                DTModel.objects.annotate(
                    day_melb=Extract("start_datetime", "day"),
                    day_utc=Extract("start_datetime", "day", tzinfo=datetime.UTC),
                )
                .order_by("start_datetime")
                .get()
            )
            self.assertEqual(model.day_melb, 16)
            self.assertEqual(model.day_utc, 15)

    def test_extract_invalid_field_with_timezone(self):
        melb = zoneinfo.ZoneInfo("Australia/Melbourne")
        msg = "tzinfo can only be used with DateTimeField."
        with self.assertRaisesMessage(ValueError, msg):
            DTModel.objects.annotate(
                day_melb=Extract("start_date", "day", tzinfo=melb),
            ).get()
        with self.assertRaisesMessage(ValueError, msg):
            DTModel.objects.annotate(
                hour_melb=Extract("start_time", "hour", tzinfo=melb),
            ).get()

    def test_trunc_timezone_applied_before_truncation(self):
        start_datetime = datetime.datetime(2016, 1, 1, 1, 30, 50, 321)
        end_datetime = datetime.datetime(2016, 6, 15, 14, 10, 50, 123)
        start_datetime = timezone.make_aware(start_datetime)
        end_datetime = timezone.make_aware(end_datetime)
        self.create_model(start_datetime, end_datetime)
        melb = zoneinfo.ZoneInfo("Australia/Melbourne")
        pacific = zoneinfo.ZoneInfo("America/Los_Angeles")

        model = (
            DTModel.objects.annotate(
                melb_year=TruncYear("start_datetime", tzinfo=melb),
                pacific_year=TruncYear("start_datetime", tzinfo=pacific),
                melb_date=TruncDate("start_datetime", tzinfo=melb),
                pacific_date=TruncDate("start_datetime", tzinfo=pacific),
                melb_time=TruncTime("start_datetime", tzinfo=melb),
                pacific_time=TruncTime("start_datetime", tzinfo=pacific),
            )
            .order_by("start_datetime")
            .get()
        )

        melb_start_datetime = start_datetime.astimezone(melb)
        pacific_start_datetime = start_datetime.astimezone(pacific)
        self.assertEqual(model.start_datetime, start_datetime)
        self.assertEqual(model.melb_year, truncate_to(start_datetime, "year", melb))
        self.assertEqual(
            model.pacific_year, truncate_to(start_datetime, "year", pacific)
        )
        self.assertEqual(model.start_datetime.year, 2016)
        self.assertEqual(model.melb_year.year, 2016)
        self.assertEqual(model.pacific_year.year, 2015)
        self.assertEqual(model.melb_date, melb_start_datetime.date())
        self.assertEqual(model.pacific_date, pacific_start_datetime.date())
        self.assertEqual(model.melb_time, melb_start_datetime.time())
        self.assertEqual(model.pacific_time, pacific_start_datetime.time())

    def test_trunc_func_with_timezone(self):
        """
        If the truncated datetime transitions to a different offset (daylight
        saving) then the returned value will have that new timezone/offset.
        """
        start_datetime = datetime.datetime(2015, 6, 15, 14, 30, 50, 321)
        end_datetime = datetime.datetime(2016, 6, 15, 14, 10, 50, 123)
        start_datetime = timezone.make_aware(start_datetime)
        end_datetime = timezone.make_aware(end_datetime)
        self.create_model(start_datetime, end_datetime)
        self.create_model(end_datetime, start_datetime)

        def assertDatetimeKind(kind, tzinfo):
            truncated_start = truncate_to(
                start_datetime.astimezone(tzinfo), kind, tzinfo
            )
            truncated_end = truncate_to(end_datetime.astimezone(tzinfo), kind, tzinfo)
            queryset = DTModel.objects.annotate(
                truncated=Trunc(
                    "start_datetime",
                    kind,
                    output_field=DateTimeField(),
                    tzinfo=tzinfo,
                )
            ).order_by("start_datetime")
            self.assertSequenceEqual(
                queryset.values_list("start_datetime", "truncated"),
                [
                    (start_datetime, truncated_start),
                    (end_datetime, truncated_end),
                ],
            )

        def assertDatetimeToDateKind(kind, tzinfo):
            truncated_start = truncate_to(
                start_datetime.astimezone(tzinfo).date(), kind
            )
            truncated_end = truncate_to(end_datetime.astimezone(tzinfo).date(), kind)
            queryset = DTModel.objects.annotate(
                truncated=Trunc(
                    "start_datetime",
                    kind,
                    output_field=DateField(),
                    tzinfo=tzinfo,
                ),
            ).order_by("start_datetime")
            self.assertSequenceEqual(
                queryset.values_list("start_datetime", "truncated"),
                [
                    (start_datetime, truncated_start),
                    (end_datetime, truncated_end),
                ],
            )

        def assertDatetimeToTimeKind(kind, tzinfo):
            truncated_start = truncate_to(
                start_datetime.astimezone(tzinfo).time(), kind
            )
            truncated_end = truncate_to(end_datetime.astimezone(tzinfo).time(), kind)
            queryset = DTModel.objects.annotate(
                truncated=Trunc(
                    "start_datetime",
                    kind,
                    output_field=TimeField(),
                    tzinfo=tzinfo,
                )
            ).order_by("start_datetime")
            self.assertSequenceEqual(
                queryset.values_list("start_datetime", "truncated"),
                [
                    (start_datetime, truncated_start),
                    (end_datetime, truncated_end),
                ],
            )

        timezones = [
            zoneinfo.ZoneInfo("Australia/Melbourne"),
            zoneinfo.ZoneInfo("Etc/GMT+10"),
        ]
        date_truncations = ["year", "quarter", "month", "week", "day"]
        time_truncations = ["hour", "minute", "second"]
        tests = [
            (assertDatetimeToDateKind, date_truncations),
            (assertDatetimeToTimeKind, time_truncations),
            (assertDatetimeKind, [*date_truncations, *time_truncations]),
        ]
        for assertion, truncations in tests:
            for truncation in truncations:
                for tzinfo in timezones:
                    with self.subTest(
                        assertion=assertion.__name__,
                        truncation=truncation,
                        tzinfo=tzinfo.key,
                    ):
                        assertion(truncation, tzinfo)

        qs = DTModel.objects.filter(
            start_datetime__date=Trunc(
                "start_datetime", "day", output_field=DateField()
            )
        )
        self.assertEqual(qs.count(), 2)

    def test_trunc_invalid_field_with_timezone(self):
        melb = zoneinfo.ZoneInfo("Australia/Melbourne")
        msg = "tzinfo can only be used with DateTimeField."
        with self.assertRaisesMessage(ValueError, msg):
            DTModel.objects.annotate(
                day_melb=Trunc("start_date", "day", tzinfo=melb),
            ).get()
        with self.assertRaisesMessage(ValueError, msg):
            DTModel.objects.annotate(
                hour_melb=Trunc("start_time", "hour", tzinfo=melb),
            ).get()
