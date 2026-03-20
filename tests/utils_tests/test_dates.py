from django.test import SimpleTestCase
from django.utils.dates import (
    MONTHS,
    MONTHS_3,
    MONTHS_ALT,
    MONTHS_AP,
    WEEKDAYS,
    WEEKDAYS_ABBR,
)


class WeekdaysTests(SimpleTestCase):
    def test_weekdays_has_seven_entries(self):
        self.assertEqual(set(WEEKDAYS.keys()), set(range(7)))

    def test_weekdays_abbr_has_seven_entries(self):
        self.assertEqual(set(WEEKDAYS_ABBR.keys()), set(range(7)))

    def test_weekdays_values_resolve_to_str(self):
        for key, value in WEEKDAYS.items():
            with self.subTest(key=key):
                self.assertIsInstance(str(value), str)
                self.assertGreater(len(str(value)), 0)

    def test_weekdays_abbr_values_resolve_to_str(self):
        for key, value in WEEKDAYS_ABBR.items():
            with self.subTest(key=key):
                self.assertIsInstance(str(value), str)
                self.assertGreater(len(str(value)), 0)

    def test_weekdays_abbr_shorter_than_full(self):
        for key in WEEKDAYS:
            with self.subTest(key=key):
                self.assertLessEqual(
                    len(str(WEEKDAYS_ABBR[key])), len(str(WEEKDAYS[key]))
                )


class MonthsTests(SimpleTestCase):
    EXPECTED_KEYS = set(range(1, 13))

    def test_months_has_twelve_entries(self):
        self.assertEqual(set(MONTHS.keys()), self.EXPECTED_KEYS)

    def test_months_3_has_twelve_entries(self):
        self.assertEqual(set(MONTHS_3.keys()), self.EXPECTED_KEYS)

    def test_months_ap_has_twelve_entries(self):
        self.assertEqual(set(MONTHS_AP.keys()), self.EXPECTED_KEYS)

    def test_months_alt_has_twelve_entries(self):
        self.assertEqual(set(MONTHS_ALT.keys()), self.EXPECTED_KEYS)

    def test_months_values_resolve_to_str(self):
        for key, value in MONTHS.items():
            with self.subTest(key=key):
                self.assertIsInstance(str(value), str)
                self.assertGreater(len(str(value)), 0)

    def test_months_3_values_are_three_chars(self):
        for key, value in MONTHS_3.items():
            with self.subTest(key=key):
                self.assertEqual(len(str(value)), 3)

    def test_months_3_values_are_lowercase(self):
        for key, value in MONTHS_3.items():
            with self.subTest(key=key):
                resolved = str(value)
                self.assertEqual(resolved, resolved.lower())

    def test_months_ap_values_resolve_to_str(self):
        for key, value in MONTHS_AP.items():
            with self.subTest(key=key):
                self.assertIsInstance(str(value), str)
                self.assertGreater(len(str(value)), 0)

    def test_months_alt_values_resolve_to_str(self):
        for key, value in MONTHS_ALT.items():
            with self.subTest(key=key):
                self.assertIsInstance(str(value), str)
                self.assertGreater(len(str(value)), 0)
