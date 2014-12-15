import warnings

from django.template.defaultfilters import removetags
from django.test import SimpleTestCase
from django.utils.deprecation import RemovedInDjango20Warning
from django.utils.safestring import mark_safe

from ..utils import render, setup


class RemovetagsTests(SimpleTestCase):

    @setup({'removetags01': '{{ a|removetags:"a b" }} {{ b|removetags:"a b" }}'})
    def test_removetags01(self):
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', RemovedInDjango20Warning)
            output = render(
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
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', RemovedInDjango20Warning)
            output = render(
                'removetags02',
                {
                    'a': '<a>x</a> <p><b>y</b></p>',
                    'b': mark_safe('<a>x</a> <p><b>y</b></p>'),
                },
            )
        self.assertEqual(output, 'x <p>y</p> x <p>y</p>')


class FunctionTests(SimpleTestCase):

    def test_removetags(self):
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', RemovedInDjango20Warning)
            self.assertEqual(
                removetags(
                    'some <b>html</b> with <script>alert("You smell")</script> disallowed <img /> tags',
                    'script img',
                ),
                'some <b>html</b> with alert("You smell") disallowed  tags',
            )

    def test_non_string_input(self):
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', RemovedInDjango20Warning)
            self.assertEqual(removetags(123, 'a'), '123')
