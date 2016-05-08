from __future__ import unicode_literals

from django.template import Context, Template
from django.test import SimpleTestCase, ignore_warnings
from django.utils import html, six, text
from django.utils.deprecation import RemovedInDjango20Warning
from django.utils.encoding import force_bytes
from django.utils.functional import lazy, lazystr
from django.utils.safestring import (
    EscapeData, SafeData, mark_for_escaping, mark_safe,
)

lazybytes = lazy(force_bytes, bytes)


class customescape(six.text_type):
    def __html__(self):
        # implement specific and obviously wrong escaping
        # in order to be able to tell for sure when it runs
        return self.replace('<', '<<').replace('>', '>>')


class SafeStringTest(SimpleTestCase):
    def assertRenderEqual(self, tpl, expected, **context):
        context = Context(context)
        tpl = Template(tpl)
        self.assertEqual(tpl.render(context), expected)

    def test_mark_safe(self):
        s = mark_safe('a&b')

        self.assertRenderEqual('{{ s }}', 'a&b', s=s)
        self.assertRenderEqual('{{ s|force_escape }}', 'a&amp;b', s=s)

    def test_mark_safe_object_implementing_dunder_html(self):
        e = customescape('<a&b>')
        s = mark_safe(e)
        self.assertIs(s, e)

        self.assertRenderEqual('{{ s }}', '<<a&b>>', s=s)
        self.assertRenderEqual('{{ s|force_escape }}', '&lt;a&amp;b&gt;', s=s)

    def test_mark_safe_lazy(self):
        s = lazystr('a&b')
        b = lazybytes(b'a&b')

        self.assertIsInstance(mark_safe(s), SafeData)
        self.assertIsInstance(mark_safe(b), SafeData)
        self.assertRenderEqual('{{ s }}', 'a&b', s=mark_safe(s))

    def test_mark_safe_object_implementing_dunder_str(self):
        class Obj(object):
            def __str__(self):
                return '<obj>'

        s = mark_safe(Obj())

        self.assertRenderEqual('{{ s }}', '<obj>', s=s)

    def test_mark_safe_result_implements_dunder_html(self):
        self.assertEqual(mark_safe('a&b').__html__(), 'a&b')

    def test_mark_safe_lazy_result_implements_dunder_html(self):
        self.assertEqual(mark_safe(lazystr('a&b')).__html__(), 'a&b')

    @ignore_warnings(category=RemovedInDjango20Warning)
    def test_mark_for_escaping(self):
        s = mark_for_escaping('a&b')
        self.assertRenderEqual('{{ s }}', 'a&amp;b', s=s)
        self.assertRenderEqual('{{ s }}', 'a&amp;b', s=mark_for_escaping(s))

    @ignore_warnings(category=RemovedInDjango20Warning)
    def test_mark_for_escaping_object_implementing_dunder_html(self):
        e = customescape('<a&b>')
        s = mark_for_escaping(e)
        self.assertIs(s, e)

        self.assertRenderEqual('{{ s }}', '<<a&b>>', s=s)
        self.assertRenderEqual('{{ s|force_escape }}', '&lt;a&amp;b&gt;', s=s)

    @ignore_warnings(category=RemovedInDjango20Warning)
    def test_mark_for_escaping_lazy(self):
        s = lazystr('a&b')
        b = lazybytes(b'a&b')

        self.assertIsInstance(mark_for_escaping(s), EscapeData)
        self.assertIsInstance(mark_for_escaping(b), EscapeData)
        self.assertRenderEqual('{% autoescape off %}{{ s }}{% endautoescape %}', 'a&amp;b', s=mark_for_escaping(s))

    @ignore_warnings(category=RemovedInDjango20Warning)
    def test_mark_for_escaping_object_implementing_dunder_str(self):
        class Obj(object):
            def __str__(self):
                return '<obj>'

        s = mark_for_escaping(Obj())

        self.assertRenderEqual('{{ s }}', '&lt;obj&gt;', s=s)

    def test_add_lazy_safe_text_and_safe_text(self):
        s = html.escape(lazystr('a'))
        s += mark_safe('&b')
        self.assertRenderEqual('{{ s }}', 'a&b', s=s)

        s = html.escapejs(lazystr('a'))
        s += mark_safe('&b')
        self.assertRenderEqual('{{ s }}', 'a&b', s=s)

        s = text.slugify(lazystr('a'))
        s += mark_safe('&b')
        self.assertRenderEqual('{{ s }}', 'a&b', s=s)
