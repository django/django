import os
from datetime import datetime

from django.test import SimpleTestCase
from django.utils import html, safestring
from django.utils._os import upath
from django.utils.encoding import force_text
from django.utils.functional import lazystr


class TestUtilsHtml(SimpleTestCase):

    def check_output(self, function, value, output=None):
        """
        function(value) equals output. If output is None, function(value)
        equals value.
        """
        if output is None:
            output = value
        self.assertEqual(function(value), output)

    def test_escape(self):
        f = html.escape
        items = (
            ('&', '&amp;'),
            ('<', '&lt;'),
            ('>', '&gt;'),
            ('"', '&quot;'),
            ("'", '&#39;'),
        )
        # Substitution patterns for testing the above items.
        patterns = ("%s", "asdf%sfdsa", "%s1", "1%sb")
        for value, output in items:
            for pattern in patterns:
                self.check_output(f, pattern % value, pattern % output)
                self.check_output(f, lazystr(pattern % value), pattern % output)
            # Check repeated values.
            self.check_output(f, value * 2, output * 2)
        # Verify it doesn't double replace &.
        self.check_output(f, '<&', '&lt;&amp;')

    def test_format_html(self):
        self.assertEqual(
            html.format_html("{} {} {third} {fourth}",
                             "< Dangerous >",
                             html.mark_safe("<b>safe</b>"),
                             third="< dangerous again",
                             fourth=html.mark_safe("<i>safe again</i>")
                             ),
            "&lt; Dangerous &gt; <b>safe</b> &lt; dangerous again <i>safe again</i>"
        )

    def test_linebreaks(self):
        f = html.linebreaks
        items = (
            ("para1\n\npara2\r\rpara3", "<p>para1</p>\n\n<p>para2</p>\n\n<p>para3</p>"),
            ("para1\nsub1\rsub2\n\npara2", "<p>para1<br />sub1<br />sub2</p>\n\n<p>para2</p>"),
            ("para1\r\n\r\npara2\rsub1\r\rpara4", "<p>para1</p>\n\n<p>para2<br />sub1</p>\n\n<p>para4</p>"),
            ("para1\tmore\n\npara2", "<p>para1\tmore</p>\n\n<p>para2</p>"),
        )
        for value, output in items:
            self.check_output(f, value, output)
            self.check_output(f, lazystr(value), output)

    def test_strip_tags(self):
        f = html.strip_tags
        items = (
            ('<p>See: &#39;&eacute; is an apostrophe followed by e acute</p>',
             'See: &#39;&eacute; is an apostrophe followed by e acute'),
            ('<adf>a', 'a'),
            ('</adf>a', 'a'),
            ('<asdf><asdf>e', 'e'),
            ('hi, <f x', 'hi, <f x'),
            ('234<235, right?', '234<235, right?'),
            ('a4<a5 right?', 'a4<a5 right?'),
            ('b7>b2!', 'b7>b2!'),
            ('</fe', '</fe'),
            ('<x>b<y>', 'b'),
            ('a<p onclick="alert(\'<test>\')">b</p>c', 'abc'),
            ('a<p a >b</p>c', 'abc'),
            ('d<a:b c:d>e</p>f', 'def'),
            ('<strong>foo</strong><a href="http://example.com">bar</a>', 'foobar'),
            # caused infinite loop on Pythons not patched with
            # http://bugs.python.org/issue20288
            ('&gotcha&#;<>', '&gotcha&#;<>'),
        )
        for value, output in items:
            self.check_output(f, value, output)
            self.check_output(f, lazystr(value), output)

        # Some convoluted syntax for which parsing may differ between python versions
        output = html.strip_tags('<sc<!-- -->ript>test<<!-- -->/script>')
        self.assertNotIn('<script>', output)
        self.assertIn('test', output)
        output = html.strip_tags('<script>alert()</script>&h')
        self.assertNotIn('<script>', output)
        self.assertIn('alert()', output)

        # Test with more lengthy content (also catching performance regressions)
        for filename in ('strip_tags1.html', 'strip_tags2.txt'):
            path = os.path.join(os.path.dirname(upath(__file__)), 'files', filename)
            with open(path, 'r') as fp:
                content = force_text(fp.read())
                start = datetime.now()
                stripped = html.strip_tags(content)
                elapsed = datetime.now() - start
            self.assertEqual(elapsed.seconds, 0)
            self.assertIn("Please try again.", stripped)
            self.assertNotIn('<', stripped)

    def test_strip_spaces_between_tags(self):
        f = html.strip_spaces_between_tags
        # Strings that should come out untouched.
        items = (' <adf>', '<adf> ', ' </adf> ', ' <f> x</f>')
        for value in items:
            self.check_output(f, value)
            self.check_output(f, lazystr(value))
        # Strings that have spaces to strip.
        items = (
            ('<d> </d>', '<d></d>'),
            ('<p>hello </p>\n<p> world</p>', '<p>hello </p><p> world</p>'),
            ('\n<p>\t</p>\n<p> </p>\n', '\n<p></p><p></p>\n'),
        )
        for value, output in items:
            self.check_output(f, value, output)
            self.check_output(f, lazystr(value), output)

    def test_escapejs(self):
        f = html.escapejs
        items = (
            ('"double quotes" and \'single quotes\'', '\\u0022double quotes\\u0022 and \\u0027single quotes\\u0027'),
            (r'\ : backslashes, too', '\\u005C : backslashes, too'),
            (
                'and lots of whitespace: \r\n\t\v\f\b',
                'and lots of whitespace: \\u000D\\u000A\\u0009\\u000B\\u000C\\u0008'
            ),
            (r'<script>and this</script>', '\\u003Cscript\\u003Eand this\\u003C/script\\u003E'),
            (
                'paragraph separator:\u2029and line separator:\u2028',
                'paragraph separator:\\u2029and line separator:\\u2028'
            ),
        )
        for value, output in items:
            self.check_output(f, value, output)
            self.check_output(f, lazystr(value), output)

    def test_smart_urlquote(self):
        quote = html.smart_urlquote
        # IDNs are properly quoted
        self.assertEqual(quote('http://öäü.com/'), 'http://xn--4ca9at.com/')
        self.assertEqual(quote('http://öäü.com/öäü/'), 'http://xn--4ca9at.com/%C3%B6%C3%A4%C3%BC/')
        # Everything unsafe is quoted, !*'();:@&=+$,/?#[]~ is considered safe as per RFC
        self.assertEqual(quote('http://example.com/path/öäü/'), 'http://example.com/path/%C3%B6%C3%A4%C3%BC/')
        self.assertEqual(quote('http://example.com/%C3%B6/ä/'), 'http://example.com/%C3%B6/%C3%A4/')
        self.assertEqual(quote('http://example.com/?x=1&y=2+3&z='), 'http://example.com/?x=1&y=2+3&z=')
        self.assertEqual(quote('http://example.com/?x=<>"\''), 'http://example.com/?x=%3C%3E%22%27')
        self.assertEqual(quote('http://example.com/?q=http://example.com/?x=1%26q=django'),
                         'http://example.com/?q=http%3A%2F%2Fexample.com%2F%3Fx%3D1%26q%3Ddjango')
        self.assertEqual(quote('http://example.com/?q=http%3A%2F%2Fexample.com%2F%3Fx%3D1%26q%3Ddjango'),
                         'http://example.com/?q=http%3A%2F%2Fexample.com%2F%3Fx%3D1%26q%3Ddjango')

    def test_conditional_escape(self):
        s = '<h1>interop</h1>'
        self.assertEqual(html.conditional_escape(s),
                         '&lt;h1&gt;interop&lt;/h1&gt;')
        self.assertEqual(html.conditional_escape(safestring.mark_safe(s)), s)

    def test_html_safe(self):
        @html.html_safe
        class HtmlClass(object):
            def __str__(self):
                return "<h1>I'm a html class!</h1>"

        html_obj = HtmlClass()
        self.assertTrue(hasattr(HtmlClass, '__html__'))
        self.assertTrue(hasattr(html_obj, '__html__'))
        self.assertEqual(force_text(html_obj), html_obj.__html__())

    def test_html_safe_subclass(self):
        class BaseClass(object):
            def __html__(self):
                # defines __html__ on its own
                return 'some html content'

            def __str__(self):
                return 'some non html content'

        @html.html_safe
        class Subclass(BaseClass):
            def __str__(self):
                # overrides __str__ and is marked as html_safe
                return 'some html safe content'

        subclass_obj = Subclass()
        self.assertEqual(force_text(subclass_obj), subclass_obj.__html__())

    def test_html_safe_defines_html_error(self):
        msg = "can't apply @html_safe to HtmlClass because it defines __html__()."
        with self.assertRaisesMessage(ValueError, msg):
            @html.html_safe
            class HtmlClass(object):
                def __html__(self):
                    return "<h1>I'm a html class!</h1>"

    def test_html_safe_doesnt_define_str(self):
        msg = "can't apply @html_safe to HtmlClass because it doesn't define __str__()."
        with self.assertRaisesMessage(ValueError, msg):
            @html.html_safe
            class HtmlClass(object):
                pass
