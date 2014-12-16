from django.test import SimpleTestCase
from django.utils.safestring import mark_safe

from ..utils import render, setup


class UrlizeTests(SimpleTestCase):

    @setup({'urlize01': '{% autoescape off %}{{ a|urlize }} {{ b|urlize }}{% endautoescape %}'})
    def test_urlize01(self):
        output = render(
            'urlize01',
            {'a': 'http://example.com/?x=&y=', 'b': mark_safe('http://example.com?x=&amp;y=&lt;2&gt;')},
        )
        self.assertEqual(
            output,
            '<a href="http://example.com/?x=&y=" rel="nofollow">http://example.com/?x=&y=</a> '
            '<a href="http://example.com?x=&y=%3C2%3E" rel="nofollow">http://example.com?x=&amp;y=&lt;2&gt;</a>'
        )

    @setup({'urlize02': '{{ a|urlize }} {{ b|urlize }}'})
    def test_urlize02(self):
        output = render(
            'urlize02',
            {'a': "http://example.com/?x=&y=", 'b': mark_safe("http://example.com?x=&amp;y=")},
        )
        self.assertEqual(
            output,
            '<a href="http://example.com/?x=&y=" rel="nofollow">http://example.com/?x=&amp;y=</a> '
            '<a href="http://example.com?x=&y=" rel="nofollow">http://example.com?x=&amp;y=</a>'
        )

    @setup({'urlize03': '{% autoescape off %}{{ a|urlize }}{% endautoescape %}'})
    def test_urlize03(self):
        output = render('urlize03', {'a': mark_safe("a &amp; b")})
        self.assertEqual(output, 'a &amp; b')

    @setup({'urlize04': '{{ a|urlize }}'})
    def test_urlize04(self):
        output = render('urlize04', {'a': mark_safe("a &amp; b")})
        self.assertEqual(output, 'a &amp; b')

    # This will lead to a nonsense result, but at least it won't be
    # exploitable for XSS purposes when auto-escaping is on.
    @setup({'urlize05': '{% autoescape off %}{{ a|urlize }}{% endautoescape %}'})
    def test_urlize05(self):
        output = render('urlize05', {'a': "<script>alert('foo')</script>"})
        self.assertEqual(output, "<script>alert('foo')</script>")

    @setup({'urlize06': '{{ a|urlize }}'})
    def test_urlize06(self):
        output = render('urlize06', {'a': "<script>alert('foo')</script>"})
        self.assertEqual(output, '&lt;script&gt;alert(&#39;foo&#39;)&lt;/script&gt;')

    # mailto: testing for urlize
    @setup({'urlize07': '{{ a|urlize }}'})
    def test_urlize07(self):
        output = render('urlize07', {'a': "Email me at me@example.com"})
        self.assertEqual(
            output,
            'Email me at <a href="mailto:me@example.com">me@example.com</a>',
        )

    @setup({'urlize08': '{{ a|urlize }}'})
    def test_urlize08(self):
        output = render('urlize08', {'a': "Email me at <me@example.com>"})
        self.assertEqual(
            output,
            'Email me at &lt;<a href="mailto:me@example.com">me@example.com</a>&gt;',
        )
