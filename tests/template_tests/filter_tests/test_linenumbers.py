from django.test import SimpleTestCase
from django.utils.safestring import mark_safe

from ..utils import render, setup


class LinenumbersTests(SimpleTestCase):
    """
    The contents of "linenumbers" is escaped according to the current
    autoescape setting.
    """

    @setup({'linenumbers01': '{{ a|linenumbers }} {{ b|linenumbers }}'})
    def test_linenumbers01(self):
        output = render(
            'linenumbers01',
            {'a': 'one\n<two>\nthree', 'b': mark_safe('one\n&lt;two&gt;\nthree')},
        )
        self.assertEqual(output, '1. one\n2. &lt;two&gt;\n3. three '
                                 '1. one\n2. &lt;two&gt;\n3. three')

    @setup({'linenumbers02':
        '{% autoescape off %}{{ a|linenumbers }} {{ b|linenumbers }}{% endautoescape %}'})
    def test_linenumbers02(self):
        output = render(
            'linenumbers02',
            {'a': 'one\n<two>\nthree', 'b': mark_safe('one\n&lt;two&gt;\nthree')},
        )
        self.assertEqual(output, '1. one\n2. <two>\n3. three '
                                 '1. one\n2. &lt;two&gt;\n3. three')
