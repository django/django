from django.template.defaultfilters import removetags
from django.test import SimpleTestCase, ignore_warnings
from django.utils.deprecation import RemovedInDjango110Warning
from django.utils.safestring import mark_safe

from ..utils import setup


@ignore_warnings(category=RemovedInDjango110Warning)
class RemovetagsTests(SimpleTestCase):

    @setup({'removetags01': '{{ a|removetags:"a b" }} {{ b|removetags:"a b" }}'})
    def test_removetags01(self):
        output = self.engine.render_to_string(
            'removetags01',
            {
                'a': '<a>x</a> <p><b>y</b></p>',
                'b': mark_safe('<a>x</a> <p><b>y</b></p>'),
            },
        )
        self.assertEqual(output, 'x &lt;p&gt;y&lt;/p&gt; x <p>y</p>')

    @setup({'removetags02':
        '{% autoescape off %}{{ a|removetags:"a b" }} {{ b|removetags:"a b" }}{% endautoescape %}'})
    def test_removetags02(self):
        output = self.engine.render_to_string(
            'removetags02',
            {
                'a': '<a>x</a> <p><b>y</b></p>',
                'b': mark_safe('<a>x</a> <p><b>y</b></p>'),
            },
        )
        self.assertEqual(output, 'x <p>y</p> x <p>y</p>')


@ignore_warnings(category=RemovedInDjango110Warning)
class FunctionTests(SimpleTestCase):

    def test_removetags(self):
        self.assertEqual(
            removetags(
                'some <b>html</b> with <script>alert("You smell")</script> disallowed <img /> tags',
                'script img',
            ),
            'some <b>html</b> with alert("You smell") disallowed  tags',
        )

    def test_non_string_input(self):
        self.assertEqual(removetags(123, 'a'), '123')
