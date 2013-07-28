# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime
import os

from django.utils import html
from django.utils._os import upath
from django.utils.encoding import force_text
from django.utils.unittest import TestCase


class TestUtilsHtml(TestCase):

    def check_output(self, function, value, output=None):
        """
        Check that function(value) equals output.  If output is None,
        check that function(value) equals value.
        """
        if output is None:
            output = value
        self.assertEqual(function(value), output)

    def test_escape(self):
        f = html.escape
        items = (
            ('&','&amp;'),
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
            # Check repeated values.
            self.check_output(f, value * 2, output * 2)
        # Verify it doesn't double replace &.
        self.check_output(f, '<&', '&lt;&amp;')

    def test_format_html(self):
        self.assertEqual(
            html.format_html("{0} {1} {third} {fourth}",
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
        )
        for value, output in items:
            self.check_output(f, value, output)

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
        # Strings that have spaces to strip.
        items = (
            ('<d> </d>', '<d></d>'),
            ('<p>hello </p>\n<p> world</p>', '<p>hello </p><p> world</p>'),
            ('\n<p>\t</p>\n<p> </p>\n', '\n<p></p><p></p>\n'),
        )
        for value, output in items:
            self.check_output(f, value, output)

    def test_strip_entities(self):
        f = html.strip_entities
        # Strings that should come out untouched.
        values = ("&", "&a", "&a", "a&#a")
        for value in values:
            self.check_output(f, value)
        # Valid entities that should be stripped from the patterns.
        entities = ("&#1;", "&#12;", "&a;", "&fdasdfasdfasdf;")
        patterns = (
            ("asdf %(entity)s ", "asdf  "),
            ("%(entity)s%(entity)s", ""),
            ("&%(entity)s%(entity)s", "&"),
            ("%(entity)s3", "3"),
        )
        for entity in entities:
            for in_pattern, output in patterns:
                self.check_output(f, in_pattern % {'entity': entity}, output)

    def test_fix_ampersands(self):
        f = html.fix_ampersands
        # Strings without ampersands or with ampersands already encoded.
        values = ("a&#1;", "b", "&a;", "&amp; &x; ", "asdf")
        patterns = (
            ("%s", "%s"),
            ("&%s", "&amp;%s"),
            ("&%s&", "&amp;%s&amp;"),
        )
        for value in values:
            for in_pattern, out_pattern in patterns:
                self.check_output(f, in_pattern % value, out_pattern % value)
        # Strings with ampersands that need encoding.
        items = (
            ("&#;", "&amp;#;"),
            ("&#875 ;", "&amp;#875 ;"),
            ("&#4abc;", "&amp;#4abc;"),
        )
        for value, output in items:
            self.check_output(f, value, output)

    def test_escapejs(self):
        f = html.escapejs
        items = (
            ('"double quotes" and \'single quotes\'', '\\u0022double quotes\\u0022 and \\u0027single quotes\\u0027'),
            (r'\ : backslashes, too', '\\u005C : backslashes, too'),
            ('and lots of whitespace: \r\n\t\v\f\b', 'and lots of whitespace: \\u000D\\u000A\\u0009\\u000B\\u000C\\u0008'),
            (r'<script>and this</script>', '\\u003Cscript\\u003Eand this\\u003C/script\\u003E'),
            ('paragraph separator:\u2029and line separator:\u2028', 'paragraph separator:\\u2029and line separator:\\u2028'),
        )
        for value, output in items:
            self.check_output(f, value, output)

    def test_clean_html(self):
        f = html.clean_html
        items = (
            ('<p>I <i>believe</i> in <b>semantic markup</b>!</p>', '<p>I <em>believe</em> in <strong>semantic markup</strong>!</p>'),
            ('I escape & I don\'t <a href="#" target="_blank">target</a>', 'I escape &amp; I don\'t <a href="#" >target</a>'),
            ('<p>I kill whitespace</p><br clear="all"><p>&nbsp;</p>', '<p>I kill whitespace</p>'),
            # also a regression test for #7267: this used to raise an UnicodeDecodeError
            ('<p>* foo</p><p>* bar</p>', '<ul>\n<li> foo</li><li> bar</li>\n</ul>'),
        )
        for value, output in items:
            self.check_output(f, value, output)

    def test_remove_tags(self):
        f = html.remove_tags
        items = (
            ("<b><i>Yes</i></b>", "b i", "Yes"),
            ("<a>x</a> <p><b>y</b></p>", "a b", "x <p>y</p>"),
        )
        for value, tags, output in items:
            self.assertEqual(f(value, tags), output)

    def test_smart_urlquote(self):
        quote = html.smart_urlquote
        # Ensure that IDNs are properly quoted
        self.assertEqual(quote('http://öäü.com/'), 'http://xn--4ca9at.com/')
        self.assertEqual(quote('http://öäü.com/öäü/'), 'http://xn--4ca9at.com/%C3%B6%C3%A4%C3%BC/')
        # Ensure that everything unsafe is quoted, !*'();:@&=+$,/?#[]~ is considered safe as per RFC
        self.assertEqual(quote('http://example.com/path/öäü/'), 'http://example.com/path/%C3%B6%C3%A4%C3%BC/')
        self.assertEqual(quote('http://example.com/%C3%B6/ä/'), 'http://example.com/%C3%B6/%C3%A4/')
        self.assertEqual(quote('http://example.com/?x=1&y=2'), 'http://example.com/?x=1&y=2')
