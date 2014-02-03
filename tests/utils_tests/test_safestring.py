from __future__ import unicode_literals

from django.template import Template, Context
from django.test import TestCase
from django.utils.encoding import force_text, force_bytes
from django.utils.functional import lazy, Promise
from django.utils.safestring import mark_safe, mark_for_escaping, SafeData, EscapeData
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

    def test_mark_for_escaping(self):
        s = mark_for_escaping('a&b')
        self.assertRenderEqual('{{ s }}', 'a&amp;b', s=s)
        self.assertRenderEqual('{% autoescape off %}{{ s }}{% endautoescape %}', 'a&amp;b', s=s)
        self.assertRenderEqual('{{ s }}', 'a&amp;b', s=mark_for_escaping(s))

    def test_html(self):
        s = '<h1>interop</h1>'
        self.assertEqual(s, mark_safe(s).__html__())

    def test_concatenation(self):
        safe = mark_safe('&')
        unknown = '&'
        unsafe = mark_for_escaping('&')

        # Adding two safe strings results in another safe string
        self.assertIsInstance(safe + safe, SafeData)
        self.assertEqual(safe + safe, '&&')

        # Adding a safe string to an unsafe one results in an unsafe one
        self.assertNotIsInstance(safe + unknown, SafeData)
        self.assertNotIsInstance(safe + unsafe, SafeData)
        self.assertEqual(safe + unknown, '&&')
        self.assertEqual(safe + unsafe, '&&')


class LazySafeStringTests(TestCase):
    def assertRenderEqual(self, tpl, expected, **context):
        context = Context(context)
        tpl = Template(tpl)
        self.assertEqual(tpl.render(context), expected)


    def test_mark_safe(self):
        s = lazystr('a&b')
        b = lazybytes(b'a&b')

        self.assertIsInstance(mark_safe(s), Promise)
        self.assertIsInstance(mark_safe(b), Promise)
        self.assertIsInstance(mark_safe(s), SafeData)
        self.assertIsInstance(mark_safe(b), SafeData)
        self.assertRenderEqual('{{ s }}', 'a&b', s=mark_safe(s))

    def test_mark_for_escaping(self):
        s = lazystr('a&b')
        b = lazybytes(b'a&b')

        self.assertIsInstance(mark_for_escaping(s), Promise)
        self.assertIsInstance(mark_for_escaping(b), Promise)
        self.assertIsInstance(mark_for_escaping(s), EscapeData)
        self.assertIsInstance(mark_for_escaping(b), EscapeData)
        self.assertRenderEqual('{% autoescape off %}{{ s }}{% endautoescape %}', 'a&amp;b', s=mark_for_escaping(s))

    def test_regression_20296(self):
        s = mark_safe(translation.ugettext_lazy("username"))
        with translation.override('fr'):
            self.assertRenderEqual('{{ s }}', "nom d'utilisateur", s=s)

    def test_concatenation(self):
        safe = mark_safe(lazystr('&'))
        unknown = lazystr('&')
        unsafe = mark_for_escaping(lazystr('&'))

        # Adding two safe strings results in another safe string
        self.assertIsInstance(safe + safe, SafeData)
        self.assertEqual(safe + safe, '&&')

        # Adding a safe string to an unsafe one results in an unsafe one
        self.assertNotIsInstance(safe + unknown, SafeData)
        self.assertNotIsInstance(safe + unsafe, SafeData)
        self.assertEqual(safe + unknown, '&&')
        self.assertEqual(safe + unsafe, '&&')
