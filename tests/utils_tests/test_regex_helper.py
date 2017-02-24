import unittest
import warnings

from django.utils import regex_helper


class NormalizeTests(unittest.TestCase):
    def test_empty(self):
        pattern = r""
        expected = [('', [])]
        result = regex_helper.normalize(pattern)
        self.assertEqual(result, expected)

    def test_escape(self):
        pattern = r"\\\^\$\.\|\?\*\+\(\)\["
        expected = [('\\^$.|?*+()[', [])]
        result = regex_helper.normalize(pattern)
        self.assertEqual(result, expected)

    def test_group_positional(self):
        pattern = r"(.*)-(.+)"
        expected = [('%(_0)s-%(_1)s', ['_0', '_1'])]
        result = regex_helper.normalize(pattern)
        self.assertEqual(result, expected)

    def test_group_ignored(self):
        pattern = r"(?i)(?L)(?m)(?s)(?u)(?#)"
        expected = [('', [])]
        with warnings.catch_warnings(record=True) as warns:
            warnings.simplefilter('always')
            result = regex_helper.normalize(pattern)
        self.assertEqual(result, expected)
        for i, char in enumerate('iLmsu#'):
            self.assertEqual(str(warns[i].message), 'Using (?%s) in url() patterns is deprecated.' % char)

    def test_group_noncapturing(self):
        pattern = r"(?:non-capturing)"
        expected = [('non-capturing', [])]
        result = regex_helper.normalize(pattern)
        self.assertEqual(result, expected)

    def test_group_named(self):
        pattern = r"(?P<first_group_name>.*)-(?P<second_group_name>.*)"
        expected = [('%(first_group_name)s-%(second_group_name)s',
                    ['first_group_name', 'second_group_name'])]
        result = regex_helper.normalize(pattern)
        self.assertEqual(result, expected)

    def test_group_backreference(self):
        pattern = r"(?P<first_group_name>.*)-(?P=first_group_name)"
        expected = [('%(first_group_name)s-%(first_group_name)s',
                    ['first_group_name'])]
        result = regex_helper.normalize(pattern)
        self.assertEqual(result, expected)
