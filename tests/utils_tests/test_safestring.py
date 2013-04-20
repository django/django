from __future__ import absolute_import, unicode_literals


from django.template import Template, Context
from django.test import TestCase
from django.utils.encoding import force_text, force_bytes
from django.utils.functional import lazy, Promise
from django.utils.html import escape, conditional_escape
from django.utils.safestring import mark_safe, mark_for_escaping
from django.utils import six
from django.utils import translation

lazystr = lazy(force_text, six.text_type)
lazybytes = lazy(force_bytes, bytes)


class SafeStringTest(TestCase):
    def assertRenderEqual(self, tpl, expected, **context):
        context = Context(context)
        tpl = Template(tpl)
        self.assertEqual(tpl.render(context), expected)

    def test_mark_safe(self):
        s = mark_safe('a&b')

        self.assertRenderEqual('{{ s }}', 'a&b', s=s)
        self.assertRenderEqual('{{ s|force_escape }}', 'a&amp;b', s=s)

    def test_mark_safe_lazy(self):
        s = lazystr('a&b')
        b = lazybytes(b'a&b')

        self.assertIsInstance(mark_safe(s), Promise)
        self.assertIsInstance(mark_safe(b), Promise)
        self.assertRenderEqual('{{ s }}', 'a&b', s=mark_safe(s))

    def test_mark_for_escaping(self):
        s = mark_for_escaping('a&b')
        self.assertRenderEqual('{{ s }}', 'a&amp;b', s=s)
        self.assertRenderEqual('{{ s }}', 'a&amp;b', s=mark_for_escaping(s))

    def test_mark_for_escaping_lazy(self):
        s = lazystr('a&b')
        b = lazybytes(b'a&b')

        self.assertIsInstance(mark_for_escaping(s), Promise)
        self.assertIsInstance(mark_for_escaping(b), Promise)
        self.assertRenderEqual('{% autoescape off %}{{ s }}{% endautoescape %}', 'a&amp;b', s=mark_for_escaping(s))

    def test_regression_20296(self):
        s = mark_safe(translation.ugettext_lazy("username"))
        with translation.override('fr'):
            self.assertRenderEqual('{{ s }}', "nom d'utilisateur", s=s)
