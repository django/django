# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.template.defaultfilters import upper
from django.test import SimpleTestCase
from django.utils.safestring import mark_safe

from ..utils import setup


class UpperTests(SimpleTestCase):
    """
    The "upper" filter messes up entities (which are case-sensitive),
    so it's not safe for non-escaping purposes.
    """

    @setup({'upper01': '{% autoescape off %}{{ a|upper }} {{ b|upper }}{% endautoescape %}'})
    def test_upper01(self):
        output = self.engine.render_to_string('upper01', {'a': 'a & b', 'b': mark_safe('a &amp; b')})
        self.assertEqual(output, 'A & B A &AMP; B')

    @setup({'upper02': '{{ a|upper }} {{ b|upper }}'})
    def test_upper02(self):
        output = self.engine.render_to_string('upper02', {'a': 'a & b', 'b': mark_safe('a &amp; b')})
        self.assertEqual(output, 'A &amp; B A &amp;AMP; B')


class FunctionTests(SimpleTestCase):

    def test_upper(self):
        self.assertEqual(upper('Mixed case input'), 'MIXED CASE INPUT')

    def test_unicode(self):
        # lowercase e umlaut
        self.assertEqual(upper('\xeb'), '\xcb')

    def test_non_string_input(self):
        self.assertEqual(upper(123), '123')
