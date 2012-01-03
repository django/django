from django.utils import regex_helper
from django.utils import unittest


class NormalizeTests(unittest.TestCase):
    def test_empty(self):
        pattern = r""
        expected = [(u'', [])]
        result = regex_helper.normalize(pattern)
        self.assertEqual(result, expected)

    def test_escape(self):
        pattern = r"\\\^\$\.\|\?\*\+\(\)\["
        expected = [(u'\\^$.|?*+()[', [])]
        result = regex_helper.normalize(pattern)
        self.assertEqual(result, expected)

    def test_group_positional(self):
        pattern = r"(.*)-(.+)"
        expected = [(u'%(_0)s-%(_1)s', ['_0', '_1'])]
        result = regex_helper.normalize(pattern)
        self.assertEqual(result, expected)

    def test_group_ignored(self):
        pattern = r"(?i)(?L)(?m)(?s)(?u)(?#)"
        expected = [(u'', [])]
        result = regex_helper.normalize(pattern)
        self.assertEqual(result, expected)

    def test_group_noncapturing(self):
        pattern = r"(?:non-capturing)"
        expected = [(u'non-capturing', [])]
        result = regex_helper.normalize(pattern)
        self.assertEqual(result, expected)

    def test_group_named(self):
        pattern = r"(?P<first_group_name>.*)-(?P<second_group_name>.*)"
        expected = [(u'%(first_group_name)s-%(second_group_name)s',
                    ['first_group_name', 'second_group_name'])]
        result = regex_helper.normalize(pattern)
        self.assertEqual(result, expected)

    def test_group_backreference(self):
        pattern = r"(?P<first_group_name>.*)-(?P=first_group_name)"
        expected = [(u'%(first_group_name)s-%(first_group_name)s',
                    ['first_group_name'])]
        result = regex_helper.normalize(pattern)
        self.assertEqual(result, expected)
