from django.template import Context, Template
from django.test import SimpleTestCase
from django.utils import html
from django.utils.functional import lazy, lazystr
from django.utils.safestring import SafeData, mark_safe


class customescape(str):
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

    def test_mark_safe_str(self):
        """
        Calling str() on a SafeText instance doesn't lose the safe status.
        """
        s = mark_safe('a&b')
        self.assertIsInstance(str(s), type(s))

    def test_mark_safe_object_implementing_dunder_html(self):
        e = customescape('<a&b>')
        s = mark_safe(e)
        self.assertIs(s, e)

        self.assertRenderEqual('{{ s }}', '<<a&b>>', s=s)
        self.assertRenderEqual('{{ s|force_escape }}', '&lt;a&amp;b&gt;', s=s)

    def test_mark_safe_lazy(self):
        s = lazystr('a&b')

        self.assertIsInstance(mark_safe(s), SafeData)
        self.assertRenderEqual('{{ s }}', 'a&b', s=mark_safe(s))

    def test_mark_safe_object_implementing_dunder_str(self):
        class Obj:
            def __str__(self):
                return '<obj>'

        s = mark_safe(Obj())

        self.assertRenderEqual('{{ s }}', '<obj>', s=s)

    def test_mark_safe_result_implements_dunder_html(self):
        self.assertEqual(mark_safe('a&b').__html__(), 'a&b')

    def test_mark_safe_lazy_result_implements_dunder_html(self):
        self.assertEqual(mark_safe(lazystr('a&b')).__html__(), 'a&b')

    def test_add_lazy_safe_text_and_safe_text(self):
        s = html.escape(lazystr('a'))
        s += mark_safe('&b')
        self.assertRenderEqual('{{ s }}', 'a&b', s=s)

        s = html.escapejs(lazystr('a'))
        s += mark_safe('&b')
        self.assertRenderEqual('{{ s }}', 'a&b', s=s)

    def test_mark_safe_as_decorator(self):
        """
        mark_safe used as a decorator leaves the result of a function
        unchanged.
        """
        def clean_string_provider():
            return '<html><body>dummy</body></html>'

        self.assertEqual(mark_safe(clean_string_provider)(), clean_string_provider())

    def test_mark_safe_decorator_does_not_affect_dunder_html(self):
        """
        mark_safe doesn't affect a callable that has an __html__() method.
        """
        class SafeStringContainer:
            def __html__(self):
                return '<html></html>'

        self.assertIs(mark_safe(SafeStringContainer), SafeStringContainer)

    def test_mark_safe_decorator_does_not_affect_promises(self):
        """
        mark_safe doesn't affect lazy strings (Promise objects).
        """
        def html_str():
            return '<html></html>'

        lazy_str = lazy(html_str, str)()
        self.assertEqual(mark_safe(lazy_str), html_str())
