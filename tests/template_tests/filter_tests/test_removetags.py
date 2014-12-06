import warnings

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
