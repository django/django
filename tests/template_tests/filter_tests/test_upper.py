from django.test import SimpleTestCase
from django.utils.safestring import mark_safe

from ..utils import render, setup


class UpperTests(SimpleTestCase):
    """
    The "upper" filter messes up entities (which are case-sensitive),
    so it's not safe for non-escaping purposes.
    """

    @setup({'upper01': '{% autoescape off %}{{ a|upper }} {{ b|upper }}{% endautoescape %}'})
    def test_upper01(self):
        output = render('upper01', {'a': 'a & b', 'b': mark_safe('a &amp; b')})
        self.assertEqual(output, 'A & B A &AMP; B')

    @setup({'upper02': '{{ a|upper }} {{ b|upper }}'})
    def test_upper02(self):
        output = render('upper02', {'a': 'a & b', 'b': mark_safe('a &amp; b')})
        self.assertEqual(output, 'A &amp; B A &amp;AMP; B')
