from django.test import SimpleTestCase

from ..utils import render, setup


class SafeseqTests(SimpleTestCase):

    @setup({'safeseq01': '{{ a|join:", " }} -- {{ a|safeseq|join:", " }}'})
    def test_safeseq01(self):
        output = render('safeseq01', {'a': ['&', '<']})
        self.assertEqual(output, '&amp;, &lt; -- &, <')

    @setup({'safeseq02':
        '{% autoescape off %}{{ a|join:", " }} -- {{ a|safeseq|join:", " }}{% endautoescape %}'})
    def test_safeseq02(self):
        output = render('safeseq02', {'a': ['&', '<']})
        self.assertEqual(output, '&, < -- &, <')
