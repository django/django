import datetime
from unittest import mock

try:
    import zoneinfo
except ImportError:
    from backports import zoneinfo

from django.test import SimpleTestCase, override_settings
from django.utils import timezone
from django.utils.deprecation import RemovedInDjango50Warning

PARIS_ZI = zoneinfo.ZoneInfo("Europe/Paris")
EAT = timezone.get_fixed_timezone(180)  # Africa/Nairobi
ICT = timezone.get_fixed_timezone(420)  # Asia/Bangkok
UTC = datetime.timezone.utc


class TimezoneTests(SimpleTestCase):
    def test_default_timezone_is_zoneinfo(self):
        self.assertIsInstance(timezone.get_default_timezone(), zoneinfo.ZoneInfo)

    def test_now(self):
        with override_settings(USE_TZ=True):
            self.assertTrue(timezone.is_aware(timezone.now()))
        with override_settings(USE_TZ=False):
            self.assertTrue(timezone.is_naive(timezone.now()))

    def test_localdate(self):
        naive = datetime.datetime(2015, 1, 1, 0, 0, 1)
        with self.assertRaisesMessage(
            ValueError, "localtime() cannot be applied to a naive datetime"
        ):
            timezone.localdate(naive)
        with self.assertRaisesMessage(
            ValueError, "localtime() cannot be applied to a naive datetime"
        ):
            timezone.localdate(naive, timezone=EAT)

        aware = datetime.datetime(2015, 1, 1, 0, 0, 1, tzinfo=ICT)
        self.assertEqual(
            timezone.localdate(aware, timezone=EAT), datetime.date(2014, 12, 31)
        )
        with timezone.override(EAT):
            self.assertEqual(timezone.localdate(aware), datetime.date(2014, 12, 31))

        with mock.patch("django.utils.timezone.now", return_value=aware):
            self.assertEqual(
                timezone.localdate(timezone=EAT), datetime.date(2014, 12, 31)
            )
            with timezone.override(EAT):
                self.assertEqual(timezone.localdate(), datetime.date(2014, 12, 31))

    def test_override(self):
        default = timezone.get_default_timezone()
        try:
            timezone.activate(ICT)

            with timezone.override(EAT):
                self.assertIs(EAT, timezone.get_current_timezone())
            self.assertIs(ICT, timezone.get_current_timezone())

            with timezone.override(None):
                self.assertIs(default, timezone.get_current_timezone())
            self.assertIs(ICT, timezone.get_current_timezone())

            timezone.deactivate()

            with timezone.override(EAT):
                self.assertIs(EAT, timezone.get_current_timezone())
            self.assertIs(default, timezone.get_current_timezone())

            with timezone.override(None):
                self.assertIs(default, timezone.get_current_timezone())
            self.assertIs(default, timezone.get_current_timezone())
        finally:
            timezone.deactivate()

    def test_override_decorator(self):
        default = timezone.get_default_timezone()

        @timezone.override(EAT)
        def func_tz_eat():
            self.assertIs(EAT, timezone.get_current_timezone())

        @timezone.override(None)
        def func_tz_none():
            self.assertIs(default, timezone.get_current_timezone())

        try:
            timezone.activate(ICT)

            func_tz_eat()
            self.assertIs(ICT, timezone.get_current_timezone())

            func_tz_none()
            self.assertIs(ICT, timezone.get_current_timezone())

            timezone.deactivate()

            func_tz_eat()
            self.assertIs(default, timezone.get_current_timezone())

            func_tz_none()
            self.assertIs(default, timezone.get_current_timezone())
        finally:
            timezone.deactivate()

    def test_override_string_tz(self):
        with timezone.override("Asia/Bangkok"):
            self.assertEqual(timezone.get_current_timezone_name(), "Asia/Bangkok")

    def test_override_fixed_offset(self):
        with timezone.override(datetime.timezone(datetime.timedelta(), "tzname")):
            self.assertEqual(timezone.get_current_timezone_name(), "tzname")

    def test_activate_invalid_timezone(self):
        with self.assertRaisesMessage(ValueError, "Invalid timezone: None"):
            timezone.activate(None)

    def test_is_aware(self):
        self.assertTrue(
            timezone.is_aware(datetime.datetime(2011, 9, 1, 13, 20, 30, tzinfo=EAT))
        )
        self.assertFalse(timezone.is_aware(datetime.datetime(2011, 9, 1, 13, 20, 30)))

    def test_is_naive(self):
        self.assertFalse(
            timezone.is_naive(datetime.datetime(2011, 9, 1, 13, 20, 30, tzinfo=EAT))
        )
        self.assertTrue(timezone.is_naive(datetime.datetime(2011, 9, 1, 13, 20, 30)))

    def test_make_aware(self):
        self.assertEqual(
            timezone.make_aware(datetime.datetime(2011, 9, 1, 13, 20, 30), EAT),
            datetime.datetime(2011, 9, 1, 13, 20, 30, tzinfo=EAT),
        )
        with self.assertRaises(ValueError):
            timezone.make_aware(
                datetime.datetime(2011, 9, 1, 13, 20, 30, tzinfo=EAT), EAT
            )

    def test_make_naive(self):
        self.assertEqual(
            timezone.make_naive(
                datetime.datetime(2011, 9, 1, 13, 20, 30, tzinfo=EAT), EAT
            ),
            datetime.datetime(2011, 9, 1, 13, 20, 30),
        )
        self.assertEqual(
            timezone.make_naive(
                datetime.datetime(2011, 9, 1, 17, 20, 30, tzinfo=ICT), EAT
            ),
            datetime.datetime(2011, 9, 1, 13, 20, 30),
        )

        with self.assertRaisesMessage(
            ValueError, "make_naive() cannot be applied to a naive datetime"
        ):
            timezone.make_naive(datetime.datetime(2011, 9, 1, 13, 20, 30), EAT)

    def test_make_naive_no_tz(self):
        self.assertEqual(
            timezone.make_naive(datetime.datetime(2011, 9, 1, 13, 20, 30, tzinfo=EAT)),
            datetime.datetime(2011, 9, 1, 5, 20, 30),
        )

    def test_make_aware_no_tz(self):
        self.assertEqual(
            timezone.make_aware(datetime.datetime(2011, 9, 1, 13, 20, 30)),
            datetime.datetime(
                2011, 9, 1, 13, 20, 30, tzinfo=timezone.get_fixed_timezone(-300)
            ),
        )

    def test_make_aware2(self):
        CEST = datetime.timezone(datetime.timedelta(hours=2), "CEST")
        self.assertEqual(
            timezone.make_aware(datetime.datetime(2011, 9, 1, 12, 20, 30), PARIS_ZI),
            datetime.datetime(2011, 9, 1, 12, 20, 30, tzinfo=CEST),
        )
        with self.assertRaises(ValueError):
            timezone.make_aware(
                datetime.datetime(2011, 9, 1, 12, 20, 30, tzinfo=PARIS_ZI), PARIS_ZI
            )

    def test_make_naive_zoneinfo(self):
        self.assertEqual(
            timezone.make_naive(
                datetime.datetime(2011, 9, 1, 12, 20, 30, tzinfo=PARIS_ZI), PARIS_ZI
            ),
            datetime.datetime(2011, 9, 1, 12, 20, 30),
        )

        self.assertEqual(
            timezone.make_naive(
                datetime.datetime(2011, 9, 1, 12, 20, 30, fold=1, tzinfo=PARIS_ZI),
                PARIS_ZI,
            ),
            datetime.datetime(2011, 9, 1, 12, 20, 30, fold=1),
        )

    def test_make_aware_zoneinfo_ambiguous(self):
        # 2:30 happens twice, once before DST ends and once after
        ambiguous = datetime.datetime(2015, 10, 25, 2, 30)

        std = timezone.make_aware(ambiguous.replace(fold=1), timezone=PARIS_ZI)
        dst = timezone.make_aware(ambiguous, timezone=PARIS_ZI)

        self.assertEqual(
            std.astimezone(UTC) - dst.astimezone(UTC), datetime.timedelta(hours=1)
        )
        self.assertEqual(std.utcoffset(), datetime.timedelta(hours=1))
        self.assertEqual(dst.utcoffset(), datetime.timedelta(hours=2))

    def test_make_aware_zoneinfo_non_existent(self):
        # 2:30 never happened due to DST
        non_existent = datetime.datetime(2015, 3, 29, 2, 30)

        std = timezone.make_aware(non_existent, PARIS_ZI)
        dst = timezone.make_aware(non_existent.replace(fold=1), PARIS_ZI)

        self.assertEqual(
            std.astimezone(UTC) - dst.astimezone(UTC), datetime.timedelta(hours=1)
        )
        self.assertEqual(std.utcoffset(), datetime.timedelta(hours=1))
        self.assertEqual(dst.utcoffset(), datetime.timedelta(hours=2))

    def test_make_aware_is_dst_deprecation_warning(self):
        msg = (
            "The is_dst argument to make_aware(), used by the Trunc() "
            "database functions and QuerySet.datetimes(), is deprecated as it "
            "has no effect with zoneinfo time zones."
        )
        with self.assertRaisesMessage(RemovedInDjango50Warning, msg):
            timezone.make_aware(
                datetime.datetime(2011, 9, 1, 13, 20, 30), EAT, is_dst=True
            )

    def test_get_timezone_name(self):
        """
        The _get_timezone_name() helper must return the offset for fixed offset
        timezones, for usage with Trunc DB functions.

        The datetime.timezone examples show the current behavior.
        """
        tests = [
            # datetime.timezone, fixed offset with and without `name`.
            (datetime.timezone(datetime.timedelta(hours=10)), "UTC+10:00"),
            (
                datetime.timezone(datetime.timedelta(hours=10), name="Etc/GMT-10"),
                "Etc/GMT-10",
            ),
            # zoneinfo, named and fixed offset.
            (zoneinfo.ZoneInfo("Europe/Madrid"), "Europe/Madrid"),
            (zoneinfo.ZoneInfo("Etc/GMT-10"), "+10"),
        ]
        for tz, expected in tests:
            with self.subTest(tz=tz, expected=expected):
                self.assertEqual(timezone._get_timezone_name(tz), expected)

    def test_get_default_timezone(self):
        self.assertEqual(timezone.get_default_timezone_name(), "America/Chicago")

    def test_fixedoffset_timedelta(self):
        delta = datetime.timedelta(hours=1)
        self.assertEqual(timezone.get_fixed_timezone(delta).utcoffset(None), delta)

    def test_fixedoffset_negative_timedelta(self):
        delta = datetime.timedelta(hours=-2)
        self.assertEqual(timezone.get_fixed_timezone(delta).utcoffset(None), delta)
