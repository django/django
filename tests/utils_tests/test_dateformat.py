from datetime import date, datetime, time, timezone, tzinfo

from django.test import SimpleTestCase, override_settings
from django.test.utils import TZ_SUPPORT, requires_tz_support
from django.utils import dateformat, translation
from django.utils.dateformat import Formatter, format
from django.utils.timezone import get_default_timezone, get_fixed_timezone, make_aware


@override_settings(TIME_ZONE="Europe/Copenhagen")
class DateFormatTests(SimpleTestCase):
    def setUp(self):
        self._orig_lang = translation.get_language()
        translation.activate("en-us")

    def tearDown(self):
        translation.activate(self._orig_lang)

    def test_date(self):
        d = date(2009, 5, 16)
        self.assertEqual(date.fromtimestamp(int(format(d, "U"))), d)

    def test_naive_datetime(self):
        dt = datetime(2009, 5, 16, 5, 30, 30)
        self.assertEqual(datetime.fromtimestamp(int(format(dt, "U"))), dt)

    def test_naive_ambiguous_datetime(self):
        # dt is ambiguous in Europe/Copenhagen.
        dt = datetime(2015, 10, 25, 2, 30, 0)

        # Try all formatters that involve self.timezone.
        self.assertEqual(format(dt, "I"), "")
        self.assertEqual(format(dt, "O"), "")
        self.assertEqual(format(dt, "T"), "")
        self.assertEqual(format(dt, "Z"), "")

    @requires_tz_support
    def test_datetime_with_local_tzinfo(self):
        ltz = get_default_timezone()
        dt = make_aware(datetime(2009, 5, 16, 5, 30, 30), ltz)
        self.assertEqual(datetime.fromtimestamp(int(format(dt, "U")), ltz), dt)
        self.assertEqual(
            datetime.fromtimestamp(int(format(dt, "U"))), dt.replace(tzinfo=None)
        )

    @requires_tz_support
    def test_datetime_with_tzinfo(self):
        tz = get_fixed_timezone(-510)
        ltz = get_default_timezone()
        dt = make_aware(datetime(2009, 5, 16, 5, 30, 30), ltz)
        self.assertEqual(datetime.fromtimestamp(int(format(dt, "U")), tz), dt)
        self.assertEqual(datetime.fromtimestamp(int(format(dt, "U")), ltz), dt)
        # astimezone() is safe here because the target timezone doesn't have DST
        self.assertEqual(
            datetime.fromtimestamp(int(format(dt, "U"))),
            dt.astimezone(ltz).replace(tzinfo=None),
        )
        self.assertEqual(
            datetime.fromtimestamp(int(format(dt, "U")), tz).timetuple(),
            dt.astimezone(tz).timetuple(),
        )
        self.assertEqual(
            datetime.fromtimestamp(int(format(dt, "U")), ltz).timetuple(),
            dt.astimezone(ltz).timetuple(),
        )

    def test_epoch(self):
        udt = datetime(1970, 1, 1, tzinfo=timezone.utc)
        self.assertEqual(format(udt, "U"), "0")

    def test_empty_format(self):
        my_birthday = datetime(1979, 7, 8, 22, 00)

        self.assertEqual(dateformat.format(my_birthday, ""), "")

    def test_am_pm(self):
        morning = time(7, 00)
        evening = time(19, 00)
        self.assertEqual(dateformat.format(morning, "a"), "a.m.")
        self.assertEqual(dateformat.format(evening, "a"), "p.m.")
        self.assertEqual(dateformat.format(morning, "A"), "AM")
        self.assertEqual(dateformat.format(evening, "A"), "PM")

    def test_microsecond(self):
        # Regression test for #18951
        dt = datetime(2009, 5, 16, microsecond=123)
        self.assertEqual(dateformat.format(dt, "u"), "000123")

    def test_date_formats(self):
        # Specifiers 'I', 'r', and 'U' are covered in test_timezones().
        my_birthday = datetime(1979, 7, 8, 22, 00)
        for specifier, expected in [
            ("b", "jul"),
            ("d", "08"),
            ("D", "Sun"),
            ("E", "July"),
            ("F", "July"),
            ("j", "8"),
            ("l", "Sunday"),
            ("L", "False"),
            ("m", "07"),
            ("M", "Jul"),
            ("n", "7"),
            ("N", "July"),
            ("o", "1979"),
            ("S", "th"),
            ("t", "31"),
            ("w", "0"),
            ("W", "27"),
            ("y", "79"),
            ("Y", "1979"),
            ("z", "189"),
        ]:
            with self.subTest(specifier=specifier):
                self.assertEqual(dateformat.format(my_birthday, specifier), expected)

    def test_date_formats_c_format(self):
        timestamp = datetime(2008, 5, 19, 11, 45, 23, 123456)
        self.assertEqual(
            dateformat.format(timestamp, "c"), "2008-05-19T11:45:23.123456"
        )

    def test_time_formats(self):
        # Specifiers 'I', 'r', and 'U' are covered in test_timezones().
        my_birthday = datetime(1979, 7, 8, 22, 00)
        for specifier, expected in [
            ("a", "p.m."),
            ("A", "PM"),
            ("f", "10"),
            ("g", "10"),
            ("G", "22"),
            ("h", "10"),
            ("H", "22"),
            ("i", "00"),
            ("P", "10 p.m."),
            ("s", "00"),
            ("u", "000000"),
        ]:
            with self.subTest(specifier=specifier):
                self.assertEqual(dateformat.format(my_birthday, specifier), expected)

    def test_dateformat(self):
        my_birthday = datetime(1979, 7, 8, 22, 00)

        for format_, expected in [
            # Simple case for escaping a word.
            (r"jS \o\f F", "8th of July"),
            # Simple cases with leading or trailing backslash.
            # (Not using raw strings here as they cannot end with a backslash.)
            ("\\jS \\o\\f F", "jth of July"),
            ("jS \\o\\f F\\", "8th of July\\"),
            # More pathological cases of nested escaping.
            (r"Y z \C\E\T", "1979 189 CET"),
            (r"Y z \\\C\\\E\\\T", r"1979 189 \C\E\T"),
            (r"Y z \\\\\C\\\\\E\\\\\T", r"1979 189 \\C\\E\\T"),
            # FIXME: These should work, but the current implementation is broken.
            # (r"Y z \\C\\E\\T", r"1979 189 \C\July\CET"),
            # (r"Y z \\\\C\\\\E\\\\T", r"1979 189 \\C\\July\\CET"),
        ]:
            with self.subTest(format=format_):
                self.assertEqual(dateformat.format(my_birthday, format_), expected)

    def test_futuredates(self):
        the_future = datetime(2100, 10, 25, 0, 00)
        self.assertEqual(dateformat.format(the_future, r"Y"), "2100")

    def test_day_of_year_leap(self):
        self.assertEqual(dateformat.format(datetime(2000, 12, 31), "z"), "366")

    def test_timezones(self):
        my_birthday = datetime(1979, 7, 8, 22, 00)
        summertime = datetime(2005, 10, 30, 1, 00)
        wintertime = datetime(2005, 10, 30, 4, 00)
        noon = time(12, 0, 0)

        # 3h30m to the west of UTC
        tz = get_fixed_timezone(-210)
        aware_dt = datetime(2009, 5, 16, 5, 30, 30, tzinfo=tz)

        if TZ_SUPPORT:
            for specifier, expected in [
                ("e", ""),
                ("O", "+0100"),
                ("r", "Sun, 08 Jul 1979 22:00:00 +0100"),
                ("T", "CET"),
                ("U", "300315600"),
                ("Z", "3600"),
            ]:
                with self.subTest(specifier=specifier):
                    self.assertEqual(
                        dateformat.format(my_birthday, specifier), expected
                    )

            self.assertEqual(dateformat.format(aware_dt, "e"), "-0330")
            self.assertEqual(
                dateformat.format(aware_dt, "r"),
                "Sat, 16 May 2009 05:30:30 -0330",
            )

            self.assertEqual(dateformat.format(summertime, "I"), "1")
            self.assertEqual(dateformat.format(summertime, "O"), "+0200")

            self.assertEqual(dateformat.format(wintertime, "I"), "0")
            self.assertEqual(dateformat.format(wintertime, "O"), "+0100")

            for specifier in ["e", "O", "T", "Z"]:
                with self.subTest(specifier=specifier):
                    self.assertEqual(dateformat.time_format(noon, specifier), "")

        # Ticket #16924 -- We don't need timezone support to test this
        self.assertEqual(dateformat.format(aware_dt, "O"), "-0330")

    def test_invalid_time_format_specifiers(self):
        my_birthday = date(1984, 8, 7)

        for specifier in Formatter.time_specifiers:
            with self.subTest(specifier=specifier):
                msg = (
                    "The format for date objects may not contain time-related "
                    f"format specifiers (found {specifier!r})."
                )
                with self.assertRaisesMessage(TypeError, msg):
                    dateformat.format(my_birthday, specifier)

    @requires_tz_support
    def test_e_format_with_named_time_zone(self):
        dt = datetime(1970, 1, 1, tzinfo=timezone.utc)
        self.assertEqual(dateformat.format(dt, "e"), "UTC")

    @requires_tz_support
    def test_e_format_with_time_zone_with_unimplemented_tzname(self):
        class NoNameTZ(tzinfo):
            """Time zone without .tzname() defined."""

            def utcoffset(self, dt):
                return None

        dt = datetime(1970, 1, 1, tzinfo=NoNameTZ())
        self.assertEqual(dateformat.format(dt, "e"), "")

    def test_P_format(self):
        for expected, t in [
            ("midnight", time(0)),
            ("noon", time(12)),
            ("4 a.m.", time(4)),
            ("8:30 a.m.", time(8, 30)),
            ("4 p.m.", time(16)),
            ("8:30 p.m.", time(20, 30)),
        ]:
            with self.subTest(time=t):
                self.assertEqual(dateformat.time_format(t, "P"), expected)

    def test_r_format_with_date(self):
        # Assume midnight in default timezone if datetime.date provided.
        dt = date(2022, 7, 1)
        self.assertEqual(
            dateformat.format(dt, "r"),
            "Fri, 01 Jul 2022 00:00:00 +0200",
        )

    def test_r_format_with_non_en_locale(self):
        # Changing the locale doesn't change the "r" format.
        dt = datetime(1979, 7, 8, 22, 00)
        with translation.override("fr"):
            self.assertEqual(
                dateformat.format(dt, "r"),
                "Sun, 08 Jul 1979 22:00:00 +0100",
            )

    def test_S_format(self):
        for expected, days in [
            ("st", [1, 21, 31]),
            ("nd", [2, 22]),
            ("rd", [3, 23]),
            ("th", (n for n in range(4, 31) if n not in [21, 22, 23])),
        ]:
            for day in days:
                dt = date(1970, 1, day)
                with self.subTest(day=day):
                    self.assertEqual(dateformat.format(dt, "S"), expected)

    def test_y_format_year_before_1000(self):
        tests = [
            (476, "76"),
            (42, "42"),
            (4, "04"),
        ]
        for year, expected_date in tests:
            with self.subTest(year=year):
                self.assertEqual(
                    dateformat.format(datetime(year, 9, 8, 5, 0), "y"),
                    expected_date,
                )

    def test_Y_format_year_before_1000(self):
        self.assertEqual(dateformat.format(datetime(1, 1, 1), "Y"), "0001")
        self.assertEqual(dateformat.format(datetime(999, 1, 1), "Y"), "0999")

    def test_twelve_hour_format(self):
        tests = [
            (0, "12", "12"),
            (1, "1", "01"),
            (11, "11", "11"),
            (12, "12", "12"),
            (13, "1", "01"),
            (23, "11", "11"),
        ]
        for hour, g_expected, h_expected in tests:
            dt = datetime(2000, 1, 1, hour)
            with self.subTest(hour=hour):
                self.assertEqual(dateformat.format(dt, "g"), g_expected)
                self.assertEqual(dateformat.format(dt, "h"), h_expected)

    def test_multibyte_single_char_format(self):
        tests = [
            "😀",
            "à",
            "ă",
            "⌚",
            "ខ",
        ]
        dt = datetime(1970, 1, 1, tzinfo=timezone.utc)
        for format_ in tests:
            with self.subTest(format=format_):
                self.assertEqual(dateformat.format(dt, format_), format_)
