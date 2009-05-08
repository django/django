"""
Tests for django.utils.
"""

from unittest import TestCase

from django.utils import html, checksums

import timesince
import datastructures
import dateformat
import itercompat
from decorators import DecoratorFromMiddlewareTests

# We need this because "datastructures" uses sorted() and the tests are run in
# the scope of this module.
try:
    sorted
except NameError:
    from django.utils.itercompat import sorted  # For Python 2.3

# Extra tests
__test__ = {
    'timesince': timesince,
    'datastructures': datastructures,
    'dateformat': dateformat,
    'itercompat': itercompat,
}

class TestUtilsHtml(TestCase):

    def check_output(self, function, value, output=None):
        """
        Check that function(value) equals output.  If output is None,
        check that function(value) equals value.
        """
        if output is None:
            output = value
        self.assertEqual(function(value), output)

    def test_escape(self):
        f = html.escape
        items = (
            ('&','&amp;'),
            ('<', '&lt;'),
            ('>', '&gt;'),
            ('"', '&quot;'),
            ("'", '&#39;'),
        )
        # Substitution patterns for testing the above items.
        patterns = ("%s", "asdf%sfdsa", "%s1", "1%sb")
        for value, output in items:
            for pattern in patterns:
                self.check_output(f, pattern % value, pattern % output)
            # Check repeated values.
            self.check_output(f, value * 2, output * 2)
        # Verify it doesn't double replace &.
        self.check_output(f, '<&', '&lt;&amp;')

    def test_linebreaks(self):
        f = html.linebreaks
        items = (
            ("para1\n\npara2\r\rpara3", "<p>para1</p>\n\n<p>para2</p>\n\n<p>para3</p>"),
            ("para1\nsub1\rsub2\n\npara2", "<p>para1<br />sub1<br />sub2</p>\n\n<p>para2</p>"),
            ("para1\r\n\r\npara2\rsub1\r\rpara4", "<p>para1</p>\n\n<p>para2<br />sub1</p>\n\n<p>para4</p>"),
            ("para1\tmore\n\npara2", "<p>para1\tmore</p>\n\n<p>para2</p>"),
        )
        for value, output in items:
            self.check_output(f, value, output)

    def test_strip_tags(self):
        f = html.strip_tags
        items = (
            ('<adf>a', 'a'),
            ('</adf>a', 'a'),
            ('<asdf><asdf>e', 'e'),
            ('<f', '<f'),
            ('</fe', '</fe'),
            ('<x>b<y>', 'b'),
        )
        for value, output in items:
            self.check_output(f, value, output)

    def test_strip_spaces_between_tags(self):
        f = html.strip_spaces_between_tags
        # Strings that should come out untouched.
        items = (' <adf>', '<adf> ', ' </adf> ', ' <f> x</f>')
        for value in items:
            self.check_output(f, value)
        # Strings that have spaces to strip.
        items = (
            ('<d> </d>', '<d></d>'),
            ('<p>hello </p>\n<p> world</p>', '<p>hello </p><p> world</p>'),
            ('\n<p>\t</p>\n<p> </p>\n', '\n<p></p><p></p>\n'),
        )
        for value, output in items:
            self.check_output(f, value, output)

    def test_strip_entities(self):
        f = html.strip_entities
        # Strings that should come out untouched.
        values = ("&", "&a", "&a", "a&#a")
        for value in values:
            self.check_output(f, value)
        # Valid entities that should be stripped from the patterns.
        entities = ("&#1;", "&#12;", "&a;", "&fdasdfasdfasdf;")
        patterns = (
            ("asdf %(entity)s ", "asdf  "),
            ("%(entity)s%(entity)s", ""),
            ("&%(entity)s%(entity)s", "&"),
            ("%(entity)s3", "3"),
        )
        for entity in entities:
            for in_pattern, output in patterns:
                self.check_output(f, in_pattern % {'entity': entity}, output)

    def test_fix_ampersands(self):
        f = html.fix_ampersands
        # Strings without ampersands or with ampersands already encoded.
        values = ("a&#1;", "b", "&a;", "&amp; &x; ", "asdf")
        patterns = (
            ("%s", "%s"),
            ("&%s", "&amp;%s"),
            ("&%s&", "&amp;%s&amp;"),
        )
        for value in values:
            for in_pattern, out_pattern in patterns:
                self.check_output(f, in_pattern % value, out_pattern % value)
        # Strings with ampersands that need encoding.
        items = (
            ("&#;", "&amp;#;"),
            ("&#875 ;", "&amp;#875 ;"),
            ("&#4abc;", "&amp;#4abc;"),
        )
        for value, output in items:
            self.check_output(f, value, output)

class TestUtilsChecksums(TestCase):

    def check_output(self, function, value, output=None):
        """
        Check that function(value) equals output.  If output is None,
        check that function(value) equals value.
        """
        if output is None:
            output = value
        self.assertEqual(function(value), output)

    def test_luhn(self):
        f = checksums.luhn
        items = (
            (4111111111111111, True), ('4111111111111111', True),
            (4222222222222, True), (378734493671000, True),
            (5424000000000015, True), (5555555555554444, True),
            (1008, True), ('0000001008', True), ('000000001008', True),
            (4012888888881881, True), (1234567890123456789012345678909, True),
            (4111111111211111, False), (42222222222224, False),
            (100, False), ('100', False), ('0000100', False),
            ('abc', False), (None, False), (object(), False),
        )
        for value, output in items:
            self.check_output(f, value, output)

if __name__ == "__main__":
    import doctest
    doctest.testmod()
