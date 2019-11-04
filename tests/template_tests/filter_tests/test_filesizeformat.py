from django.template.defaultfilters import filesizeformat
from django.test import SimpleTestCase
from django.utils import translation


class FunctionTests(SimpleTestCase):

    def test_formats(self):
        self.assertEqual(filesizeformat(1023), '1023\xa0bytes')
        self.assertEqual(filesizeformat(1024), '1.0\xa0KB')
        self.assertEqual(filesizeformat(10 * 1024), '10.0\xa0KB')
        self.assertEqual(filesizeformat(1024 * 1024 - 1), '1024.0\xa0KB')
        self.assertEqual(filesizeformat(1024 * 1024), '1.0\xa0MB')
        self.assertEqual(filesizeformat(1024 * 1024 * 50), '50.0\xa0MB')
        self.assertEqual(filesizeformat(1024 * 1024 * 1024 - 1), '1024.0\xa0MB')
        self.assertEqual(filesizeformat(1024 * 1024 * 1024), '1.0\xa0GB')
        self.assertEqual(filesizeformat(1024 * 1024 * 1024 * 1024), '1.0\xa0TB')
        self.assertEqual(filesizeformat(1024 * 1024 * 1024 * 1024 * 1024), '1.0\xa0PB')
        self.assertEqual(filesizeformat(1024 * 1024 * 1024 * 1024 * 1024 * 2000), '2000.0\xa0PB')
        self.assertEqual(filesizeformat(complex(1, -1)), '0\xa0bytes')
        self.assertEqual(filesizeformat(""), '0\xa0bytes')
        self.assertEqual(filesizeformat("\N{GREEK SMALL LETTER ALPHA}"), '0\xa0bytes')

    def test_localized_formats(self):
        with self.settings(USE_L10N=True), translation.override('de'):
            self.assertEqual(filesizeformat(1023), '1023\xa0Bytes')
            self.assertEqual(filesizeformat(1024), '1,0\xa0KB')
            self.assertEqual(filesizeformat(10 * 1024), '10,0\xa0KB')
            self.assertEqual(filesizeformat(1024 * 1024 - 1), '1024,0\xa0KB')
            self.assertEqual(filesizeformat(1024 * 1024), '1,0\xa0MB')
            self.assertEqual(filesizeformat(1024 * 1024 * 50), '50,0\xa0MB')
            self.assertEqual(filesizeformat(1024 * 1024 * 1024 - 1), '1024,0\xa0MB')
            self.assertEqual(filesizeformat(1024 * 1024 * 1024), '1,0\xa0GB')
            self.assertEqual(filesizeformat(1024 * 1024 * 1024 * 1024), '1,0\xa0TB')
            self.assertEqual(filesizeformat(1024 * 1024 * 1024 * 1024 * 1024), '1,0\xa0PB')
            self.assertEqual(filesizeformat(1024 * 1024 * 1024 * 1024 * 1024 * 2000), '2000,0\xa0PB')
            self.assertEqual(filesizeformat(complex(1, -1)), '0\xa0Bytes')
            self.assertEqual(filesizeformat(""), '0\xa0Bytes')
            self.assertEqual(filesizeformat("\N{GREEK SMALL LETTER ALPHA}"), '0\xa0Bytes')

    def test_negative_numbers(self):
        self.assertEqual(filesizeformat(-100), '-100\xa0bytes')
        self.assertEqual(filesizeformat(-1024 * 1024 * 50), '-50.0\xa0MB')
