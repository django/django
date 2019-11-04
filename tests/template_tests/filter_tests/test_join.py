from django.template.defaultfilters import join
from django.test import SimpleTestCase
from django.utils.safestring import mark_safe

from ..utils import setup


class JoinTests(SimpleTestCase):

    @setup({'join01': '{{ a|join:", " }}'})
    def test_join01(self):
        output = self.engine.render_to_string('join01', {'a': ['alpha', 'beta & me']})
        self.assertEqual(output, 'alpha, beta &amp; me')

    @setup({'join02': '{% autoescape off %}{{ a|join:", " }}{% endautoescape %}'})
    def test_join02(self):
        output = self.engine.render_to_string('join02', {'a': ['alpha', 'beta & me']})
        self.assertEqual(output, 'alpha, beta & me')

    @setup({'join03': '{{ a|join:" &amp; " }}'})
    def test_join03(self):
        output = self.engine.render_to_string('join03', {'a': ['alpha', 'beta & me']})
        self.assertEqual(output, 'alpha &amp; beta &amp; me')

    @setup({'join04': '{% autoescape off %}{{ a|join:" &amp; " }}{% endautoescape %}'})
    def test_join04(self):
        output = self.engine.render_to_string('join04', {'a': ['alpha', 'beta & me']})
        self.assertEqual(output, 'alpha &amp; beta & me')

    # Joining with unsafe joiners doesn't result in unsafe strings.
    @setup({'join05': '{{ a|join:var }}'})
    def test_join05(self):
        output = self.engine.render_to_string('join05', {'a': ['alpha', 'beta & me'], 'var': ' & '})
        self.assertEqual(output, 'alpha &amp; beta &amp; me')

    @setup({'join06': '{{ a|join:var }}'})
    def test_join06(self):
        output = self.engine.render_to_string('join06', {'a': ['alpha', 'beta & me'], 'var': mark_safe(' & ')})
        self.assertEqual(output, 'alpha & beta &amp; me')

    @setup({'join07': '{{ a|join:var|lower }}'})
    def test_join07(self):
        output = self.engine.render_to_string('join07', {'a': ['Alpha', 'Beta & me'], 'var': ' & '})
        self.assertEqual(output, 'alpha &amp; beta &amp; me')

    @setup({'join08': '{{ a|join:var|lower }}'})
    def test_join08(self):
        output = self.engine.render_to_string('join08', {'a': ['Alpha', 'Beta & me'], 'var': mark_safe(' & ')})
        self.assertEqual(output, 'alpha & beta &amp; me')


class FunctionTests(SimpleTestCase):

    def test_list(self):
        self.assertEqual(join([0, 1, 2], 'glue'), '0glue1glue2')

    def test_autoescape(self):
        self.assertEqual(
            join(['<a>', '<img>', '</a>'], '<br>'),
            '&lt;a&gt;&lt;br&gt;&lt;img&gt;&lt;br&gt;&lt;/a&gt;',
        )

    def test_autoescape_off(self):
        self.assertEqual(
            join(['<a>', '<img>', '</a>'], '<br>', autoescape=False),
            '<a>&lt;br&gt;<img>&lt;br&gt;</a>',
        )

    def test_noniterable_arg(self):
        obj = object()
        self.assertEqual(join(obj, '<br>'), obj)

    def test_noniterable_arg_autoescape_off(self):
        obj = object()
        self.assertEqual(join(obj, '<br>', autoescape=False), obj)
