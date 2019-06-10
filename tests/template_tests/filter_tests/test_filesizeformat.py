from django.template.defaultfilters import filesizeformat
from django.test import SimpleTestCase
from django.utils import translation


class FunctionTests(SimpleTestCase):

    def test_formats(self):
        tests = [
            (0, '0\xa0bytes'),
            (1, '1\xa0byte'),
            (1023, '1023\xa0bytes'),
            (1024, '1.0\xa0KB'),
            (10 * 1024, '10.0\xa0KB'),
            (1024 * 1024 - 1, '1024.0\xa0KB'),
            (1024 * 1024, '1.0\xa0MB'),
            (1024 * 1024 * 50, '50.0\xa0MB'),
            (1024 * 1024 * 1024 - 1, '1024.0\xa0MB'),
            (1024 * 1024 * 1024, '1.0\xa0GB'),
            (1024 * 1024 * 1024 * 1024, '1.0\xa0TB'),
            (1024 * 1024 * 1024 * 1024 * 1024, '1.0\xa0PB'),
            (1024 * 1024 * 1024 * 1024 * 1024 * 2000, '2000.0\xa0PB'),
            (complex(1, -1), '0\xa0bytes'),
            ('', '0\xa0bytes'),
            ('\N{GREEK SMALL LETTER ALPHA}', '0\xa0bytes'),
        ]
        for value, expected in tests:
            with self.subTest(value=value):
                self.assertEqual(filesizeformat(value), expected)

    def test_localized_formats(self):
        tests = [
            (0, '0\xa0Bytes'),
            (1, '1\xa0Byte'),
            (1023, '1023\xa0Bytes'),
            (1024, '1,0\xa0KB'),
            (10 * 1024, '10,0\xa0KB'),
            (1024 * 1024 - 1, '1024,0\xa0KB'),
            (1024 * 1024, '1,0\xa0MB'),
            (1024 * 1024 * 50, '50,0\xa0MB'),
            (1024 * 1024 * 1024 - 1, '1024,0\xa0MB'),
            (1024 * 1024 * 1024, '1,0\xa0GB'),
            (1024 * 1024 * 1024 * 1024, '1,0\xa0TB'),
            (1024 * 1024 * 1024 * 1024 * 1024, '1,0\xa0PB'),
            (1024 * 1024 * 1024 * 1024 * 1024 * 2000, '2000,0\xa0PB'),
            (complex(1, -1), '0\xa0Bytes'),
            ('', '0\xa0Bytes'),
            ('\N{GREEK SMALL LETTER ALPHA}', '0\xa0Bytes'),
        ]
        with self.settings(USE_L10N=True), translation.override('de'):
            for value, expected in tests:
                with self.subTest(value=value):
                    self.assertEqual(filesizeformat(value), expected)

    def test_negative_numbers(self):
        tests = [
            (-1, '-1\xa0byte'),
            (-100, '-100\xa0bytes'),
            (-1024 * 1024 * 50, '-50.0\xa0MB'),
        ]
        for value, expected in tests:
            with self.subTest(value=value):
                self.assertEqual(filesizeformat(value), expected)
