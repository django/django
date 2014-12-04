from django.test import SimpleTestCase
from django.utils.safestring import mark_safe

from ..utils import render, setup


class StriptagsTests(SimpleTestCase):

    @setup({'striptags01': '{{ a|striptags }} {{ b|striptags }}'})
    def test_striptags01(self):
        output = render(
            'striptags01',
            {
                'a': '<a>x</a> <p><b>y</b></p>',
                'b': mark_safe('<a>x</a> <p><b>y</b></p>'),
            },
        )
        self.assertEqual(output, 'x y x y')

    @setup({'striptags02': '{% autoescape off %}{{ a|striptags }} {{ b|striptags }}{% endautoescape %}'})
    def test_striptags02(self):
        output = render(
            'striptags02',
            {
                'a': '<a>x</a> <p><b>y</b></p>',
                'b': mark_safe('<a>x</a> <p><b>y</b></p>'),
            },
        )
        self.assertEqual(output, 'x y x y')
