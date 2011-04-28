import unittest

from django.utils import html

class TestUtilsHtml(unittest.TestCase):

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
            ('<adf>a', 'a'),
            ('</adf>a', 'a'),
            ('<asdf><asdf>e', 'e'),
            ('<f', '<f'),
            ('</fe', '</fe'),
            ('<x>b<y>', 'b'),
        )
        for value, output in items:
            self.check_output(f, value, output)

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
            (u'"double quotes" and \'single quotes\'', u'\\u0022double quotes\\u0022 and \\u0027single quotes\\u0027'),
            (ur'\ : backslashes, too', u'\\u005C : backslashes, too'),
            (u'and lots of whitespace: \r\n\t\v\f\b', u'and lots of whitespace: \\u000D\\u000A\\u0009\\u000B\\u000C\\u0008'),
            (ur'<script>and this</script>', u'\\u003Cscript\\u003Eand this\\u003C/script\\u003E'),
            (u'paragraph separator:\u2029and line separator:\u2028', u'paragraph separator:\\u2029and line separator:\\u2028'),
        )
        for value, output in items:
            self.check_output(f, value, output)

    def test_clean_html(self):
        f = html.clean_html
        items = (
            (u'<p>I <i>believe</i> in <b>semantic markup</b>!</p>', u'<p>I <em>believe</em> in <strong>semantic markup</strong>!</p>'),
            (u'I escape & I don\'t <a href="#" target="_blank">target</a>', u'I escape &amp; I don\'t <a href="#" >target</a>'),
            (u'<p>I kill whitespace</p><br clear="all"><p>&nbsp;</p>', u'<p>I kill whitespace</p>'),
            # also a regression test for #7267: this used to raise an UnicodeDecodeError
            (u'<p>* foo</p><p>* bar</p>', u'<ul>\n<li> foo</li><li> bar</li>\n</ul>'),
        )
        for value, output in items:
            self.check_output(f, value, output)
