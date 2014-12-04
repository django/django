from django.test import SimpleTestCase
from django.utils.safestring import mark_safe

from ..utils import render, setup


class JoinTests(SimpleTestCase):

    @setup({'join01': '{{ a|join:", " }}'})
    def test_join01(self):
        output = render('join01', {'a': ['alpha', 'beta & me']})
        self.assertEqual(output, 'alpha, beta &amp; me')

    @setup({'join02': '{% autoescape off %}{{ a|join:", " }}{% endautoescape %}'})
    def test_join02(self):
        output = render('join02', {'a': ['alpha', 'beta & me']})
        self.assertEqual(output, 'alpha, beta & me')

    @setup({'join03': '{{ a|join:" &amp; " }}'})
    def test_join03(self):
        output = render('join03', {'a': ['alpha', 'beta & me']})
        self.assertEqual(output, 'alpha &amp; beta &amp; me')

    @setup({'join04': '{% autoescape off %}{{ a|join:" &amp; " }}{% endautoescape %}'})
    def test_join04(self):
        output = render('join04', {'a': ['alpha', 'beta & me']})
        self.assertEqual(output, 'alpha &amp; beta & me')

    # #11377 Test that joining with unsafe joiners doesn't result in
    # unsafe strings
    @setup({'join05': '{{ a|join:var }}'})
    def test_join05(self):
        output = render('join05', {'a': ['alpha', 'beta & me'], 'var': ' & '})
        self.assertEqual(output, 'alpha &amp; beta &amp; me')

    @setup({'join06': '{{ a|join:var }}'})
    def test_join06(self):
        output = render('join06', {'a': ['alpha', 'beta & me'], 'var': mark_safe(' & ')})
        self.assertEqual(output, 'alpha & beta &amp; me')

    @setup({'join07': '{{ a|join:var|lower }}'})
    def test_join07(self):
        output = render('join07', {'a': ['Alpha', 'Beta & me'], 'var': ' & '})
        self.assertEqual(output, 'alpha &amp; beta &amp; me')

    @setup({'join08': '{{ a|join:var|lower }}'})
    def test_join08(self):
        output = render('join08', {'a': ['Alpha', 'Beta & me'], 'var': mark_safe(' & ')})
        self.assertEqual(output, 'alpha & beta &amp; me')
