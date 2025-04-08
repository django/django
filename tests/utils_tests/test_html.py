import os
from datetime import datetime

from django.core.exceptions import SuspiciousOperation
from django.core.serializers.json import DjangoJSONEncoder
from django.test import SimpleTestCase
from django.utils.deprecation import RemovedInDjango60Warning
from django.utils.functional import lazystr
from django.utils.html import (
    conditional_escape,
    escape,
    escapejs,
    format_html,
    html_safe,
    json_script,
    linebreaks,
    smart_urlquote,
    strip_spaces_between_tags,
    strip_tags,
    urlize,
)
from django.utils.safestring import mark_safe


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
        items = (
            ("&", "&amp;"),
            ("<", "&lt;"),
            (">", "&gt;"),
            ('"', "&quot;"),
            ("'", "&#x27;"),
        )
        # Substitution patterns for testing the above items.
        patterns = ("%s", "asdf%sfdsa", "%s1", "1%sb")
        for value, output in items:
            with self.subTest(value=value, output=output):
                for pattern in patterns:
                    with self.subTest(value=value, output=output, pattern=pattern):
                        self.check_output(escape, pattern % value, pattern % output)
                        self.check_output(
                            escape, lazystr(pattern % value), pattern % output
                        )
                # Check repeated values.
                self.check_output(escape, value * 2, output * 2)
        # Verify it doesn't double replace &.
        self.check_output(escape, "<&", "&lt;&amp;")

    def test_format_html(self):
        self.assertEqual(
            format_html(
                "{} {} {third} {fourth}",
                "< Dangerous >",
                mark_safe("<b>safe</b>"),
                third="< dangerous again",
                fourth=mark_safe("<i>safe again</i>"),
            ),
            "&lt; Dangerous &gt; <b>safe</b> &lt; dangerous again <i>safe again</i>",
        )

    def test_format_html_no_params(self):
        msg = "Calling format_html() without passing args or kwargs is deprecated."
        # RemovedInDjango60Warning: when the deprecation ends, replace with:
        # msg = "args or kwargs must be provided."
        # with self.assertRaisesMessage(TypeError, msg):
        with self.assertWarnsMessage(RemovedInDjango60Warning, msg) as ctx:
            name = "Adam"
            self.assertEqual(format_html(f"<i>{name}</i>"), "<i>Adam</i>")
        self.assertEqual(ctx.filename, __file__)

    def test_linebreaks(self):
        items = (
            ("para1\n\npara2\r\rpara3", "<p>para1</p>\n\n<p>para2</p>\n\n<p>para3</p>"),
            (
                "para1\nsub1\rsub2\n\npara2",
                "<p>para1<br>sub1<br>sub2</p>\n\n<p>para2</p>",
            ),
            (
                "para1\r\n\r\npara2\rsub1\r\rpara4",
                "<p>para1</p>\n\n<p>para2<br>sub1</p>\n\n<p>para4</p>",
            ),
            ("para1\tmore\n\npara2", "<p>para1\tmore</p>\n\n<p>para2</p>"),
        )
        for value, output in items:
            with self.subTest(value=value, output=output):
                self.check_output(linebreaks, value, output)
                self.check_output(linebreaks, lazystr(value), output)

    def test_strip_tags(self):
        items = (
            (
                "<p>See: &#39;&eacute; is an apostrophe followed by e acute</p>",
                "See: &#39;&eacute; is an apostrophe followed by e acute",
            ),
            (
                "<p>See: &#x27;&eacute; is an apostrophe followed by e acute</p>",
                "See: &#x27;&eacute; is an apostrophe followed by e acute",
            ),
            ("<adf>a", "a"),
            ("</adf>a", "a"),
            ("<asdf><asdf>e", "e"),
            ("hi, <f x", "hi, <f x"),
            ("234<235, right?", "234<235, right?"),
            ("a4<a5 right?", "a4<a5 right?"),
            ("b7>b2!", "b7>b2!"),
            ("</fe", "</fe"),
            ("<x>b<y>", "b"),
            ("a<p onclick=\"alert('<test>')\">b</p>c", "abc"),
            ("a<p a >b</p>c", "abc"),
            ("d<a:b c:d>e</p>f", "def"),
            ('<strong>foo</strong><a href="http://example.com">bar</a>', "foobar"),
            # caused infinite loop on Pythons not patched with
            # https://bugs.python.org/issue20288
            ("&gotcha&#;<>", "&gotcha&#;<>"),
            ("<sc<!-- -->ript>test<<!-- -->/script>", "ript>test"),
            ("<script>alert()</script>&h", "alert()h"),
            ("><!" + ("&" * 16000) + "D", "><!" + ("&" * 16000) + "D"),
            ("X<<<<br>br>br>br>X", "XX"),
            ("<" * 50 + "a>" * 50, ""),
            (">" + "<a" * 500 + "a", ">" + "<a" * 500 + "a"),
            ("<a" * 49 + "a" * 951, "<a" * 49 + "a" * 951),
            ("<" + "a" * 1_002, "<" + "a" * 1_002),
        )
        for value, output in items:
            with self.subTest(value=value, output=output):
                self.check_output(strip_tags, value, output)
                self.check_output(strip_tags, lazystr(value), output)

    def test_strip_tags_suspicious_operation_max_depth(self):
        value = "<" * 51 + "a>" * 51, "<a>"
        with self.assertRaises(SuspiciousOperation):
            strip_tags(value)

    def test_strip_tags_suspicious_operation_large_open_tags(self):
        items = [
            ">" + "<a" * 501,
            "<a" * 50 + "a" * 950,
        ]
        for value in items:
            with self.subTest(value=value):
                with self.assertRaises(SuspiciousOperation):
                    strip_tags(value)

    def test_strip_tags_files(self):
        # Test with more lengthy content (also catching performance regressions)
        for filename in ("strip_tags1.html", "strip_tags2.txt"):
            with self.subTest(filename=filename):
                path = os.path.join(os.path.dirname(__file__), "files", filename)
                with open(path) as fp:
                    content = fp.read()
                    start = datetime.now()
                    stripped = strip_tags(content)
                    elapsed = datetime.now() - start
                self.assertEqual(elapsed.seconds, 0)
                self.assertIn("Test string that has not been stripped.", stripped)
                self.assertNotIn("<", stripped)

    def test_strip_spaces_between_tags(self):
        # Strings that should come out untouched.
        items = (" <adf>", "<adf> ", " </adf> ", " <f> x</f>")
        for value in items:
            with self.subTest(value=value):
                self.check_output(strip_spaces_between_tags, value)
                self.check_output(strip_spaces_between_tags, lazystr(value))

        # Strings that have spaces to strip.
        items = (
            ("<d> </d>", "<d></d>"),
            ("<p>hello </p>\n<p> world</p>", "<p>hello </p><p> world</p>"),
            ("\n<p>\t</p>\n<p> </p>\n", "\n<p></p><p></p>\n"),
        )
        for value, output in items:
            with self.subTest(value=value, output=output):
                self.check_output(strip_spaces_between_tags, value, output)
                self.check_output(strip_spaces_between_tags, lazystr(value), output)

    def test_escapejs(self):
        items = (
            (
                "\"double quotes\" and 'single quotes'",
                "\\u0022double quotes\\u0022 and \\u0027single quotes\\u0027",
            ),
            (r"\ : backslashes, too", "\\u005C : backslashes, too"),
            (
                "and lots of whitespace: \r\n\t\v\f\b",
                "and lots of whitespace: \\u000D\\u000A\\u0009\\u000B\\u000C\\u0008",
            ),
            (
                r"<script>and this</script>",
                "\\u003Cscript\\u003Eand this\\u003C/script\\u003E",
            ),
            (
                "paragraph separator:\u2029and line separator:\u2028",
                "paragraph separator:\\u2029and line separator:\\u2028",
            ),
            ("`", "\\u0060"),
        )
        for value, output in items:
            with self.subTest(value=value, output=output):
                self.check_output(escapejs, value, output)
                self.check_output(escapejs, lazystr(value), output)

    def test_json_script(self):
        tests = (
            # "<", ">" and "&" are quoted inside JSON strings
            (
                (
                    "&<>",
                    '<script id="test_id" type="application/json">'
                    '"\\u0026\\u003C\\u003E"</script>',
                )
            ),
            # "<", ">" and "&" are quoted inside JSON objects
            (
                {"a": "<script>test&ing</script>"},
                '<script id="test_id" type="application/json">'
                '{"a": "\\u003Cscript\\u003Etest\\u0026ing\\u003C/script\\u003E"}'
                "</script>",
            ),
            # Lazy strings are quoted
            (
                lazystr("&<>"),
                '<script id="test_id" type="application/json">"\\u0026\\u003C\\u003E"'
                "</script>",
            ),
            (
                {"a": lazystr("<script>test&ing</script>")},
                '<script id="test_id" type="application/json">'
                '{"a": "\\u003Cscript\\u003Etest\\u0026ing\\u003C/script\\u003E"}'
                "</script>",
            ),
        )
        for arg, expected in tests:
            with self.subTest(arg=arg):
                self.assertEqual(json_script(arg, "test_id"), expected)

    def test_json_script_custom_encoder(self):
        class CustomDjangoJSONEncoder(DjangoJSONEncoder):
            def encode(self, o):
                return '{"hello": "world"}'

        self.assertHTMLEqual(
            json_script({}, encoder=CustomDjangoJSONEncoder),
            '<script type="application/json">{"hello": "world"}</script>',
        )

    def test_json_script_without_id(self):
        self.assertHTMLEqual(
            json_script({"key": "value"}),
            '<script type="application/json">{"key": "value"}</script>',
        )

    def test_smart_urlquote(self):
        items = (
            ("http://öäü.com/", "http://xn--4ca9at.com/"),
            ("http://öäü.com/öäü/", "http://xn--4ca9at.com/%C3%B6%C3%A4%C3%BC/"),
            # Everything unsafe is quoted, !*'();:@&=+$,/?#[]~ is considered
            # safe as per RFC.
            (
                "http://example.com/path/öäü/",
                "http://example.com/path/%C3%B6%C3%A4%C3%BC/",
            ),
            ("http://example.com/%C3%B6/ä/", "http://example.com/%C3%B6/%C3%A4/"),
            ("http://example.com/?x=1&y=2+3&z=", "http://example.com/?x=1&y=2+3&z="),
            ("http://example.com/?x=<>\"'", "http://example.com/?x=%3C%3E%22%27"),
            (
                "http://example.com/?q=http://example.com/?x=1%26q=django",
                "http://example.com/?q=http%3A%2F%2Fexample.com%2F%3Fx%3D1%26q%3D"
                "django",
            ),
            (
                "http://example.com/?q=http%3A%2F%2Fexample.com%2F%3Fx%3D1%26q%3D"
                "django",
                "http://example.com/?q=http%3A%2F%2Fexample.com%2F%3Fx%3D1%26q%3D"
                "django",
            ),
            ("http://.www.f oo.bar/", "http://.www.f%20oo.bar/"),
        )
        # IDNs are properly quoted
        for value, output in items:
            with self.subTest(value=value, output=output):
                self.assertEqual(smart_urlquote(value), output)

    def test_conditional_escape(self):
        s = "<h1>interop</h1>"
        self.assertEqual(conditional_escape(s), "&lt;h1&gt;interop&lt;/h1&gt;")
        self.assertEqual(conditional_escape(mark_safe(s)), s)
        self.assertEqual(conditional_escape(lazystr(mark_safe(s))), s)

    def test_html_safe(self):
        @html_safe
        class HtmlClass:
            def __str__(self):
                return "<h1>I'm a html class!</h1>"

        html_obj = HtmlClass()
        self.assertTrue(hasattr(HtmlClass, "__html__"))
        self.assertTrue(hasattr(html_obj, "__html__"))
        self.assertEqual(str(html_obj), html_obj.__html__())

    def test_html_safe_subclass(self):
        class BaseClass:
            def __html__(self):
                # defines __html__ on its own
                return "some html content"

            def __str__(self):
                return "some non html content"

        @html_safe
        class Subclass(BaseClass):
            def __str__(self):
                # overrides __str__ and is marked as html_safe
                return "some html safe content"

        subclass_obj = Subclass()
        self.assertEqual(str(subclass_obj), subclass_obj.__html__())

    def test_html_safe_defines_html_error(self):
        msg = "can't apply @html_safe to HtmlClass because it defines __html__()."
        with self.assertRaisesMessage(ValueError, msg):

            @html_safe
            class HtmlClass:
                def __html__(self):
                    return "<h1>I'm a html class!</h1>"

    def test_html_safe_doesnt_define_str(self):
        msg = "can't apply @html_safe to HtmlClass because it doesn't define __str__()."
        with self.assertRaisesMessage(ValueError, msg):

            @html_safe
            class HtmlClass:
                pass

    def test_urlize(self):
        tests = (
            (
                "Search for google.com/?q=! and see.",
                'Search for <a href="http://google.com/?q=">google.com/?q=</a>! and '
                "see.",
            ),
            (
                "Search for google.com/?q=1&lt! and see.",
                'Search for <a href="http://google.com/?q=1%3C">google.com/?q=1&lt'
                "</a>! and see.",
            ),
            (
                lazystr("Search for google.com/?q=!"),
                'Search for <a href="http://google.com/?q=">google.com/?q=</a>!',
            ),
            ("foo@example.com", '<a href="mailto:foo@example.com">foo@example.com</a>'),
            (
                "test@" + "한.글." * 15 + "aaa",
                '<a href="mailto:test@'
                + "xn--6q8b.xn--bj0b." * 15
                + 'aaa">'
                + "test@"
                + "한.글." * 15
                + "aaa</a>",
            ),
        )
        for value, output in tests:
            with self.subTest(value=value):
                self.assertEqual(urlize(value), output)

    def test_urlize_unchanged_inputs(self):
        tests = (
            ("a" + "@a" * 50000) + "a",  # simple_email_re catastrophic test
            # Unicode domain catastrophic tests.
            "a@" + "한.글." * 1_000_000 + "a",
            "http://" + "한.글." * 1_000_000 + "com",
            "www." + "한.글." * 1_000_000 + "com",
            ("a" + "." * 1000000) + "a",  # trailing_punctuation catastrophic test
            "foo@",
            "@foo.com",
            "foo@.example.com",
            "foo@localhost",
            "foo@localhost.",
            # trim_punctuation catastrophic tests
            "(" * 100_000 + ":" + ")" * 100_000,
            "(" * 100_000 + "&:" + ")" * 100_000,
            "([" * 100_000 + ":" + "])" * 100_000,
            "[(" * 100_000 + ":" + ")]" * 100_000,
            "([[" * 100_000 + ":" + "]])" * 100_000,
            "&:" + ";" * 100_000,
            "&.;" * 100_000,
            ".;" * 100_000,
            "&" + ";:" * 100_000,
        )
        for value in tests:
            with self.subTest(value=value):
                self.assertEqual(urlize(value), value)
