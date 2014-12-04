from django.test import SimpleTestCase
from django.utils.safestring import mark_safe

from ..utils import render, setup


class UrlizetruncTests(SimpleTestCase):

    @setup({'urlizetrunc01':
        '{% autoescape off %}{{ a|urlizetrunc:"8" }} {{ b|urlizetrunc:"8" }}{% endautoescape %}'})
    def test_urlizetrunc01(self):
        output = render(
            'urlizetrunc01',
            {
                'a': '"Unsafe" http://example.com/x=&y=',
                'b': mark_safe('&quot;Safe&quot; http://example.com?x=&amp;y='),
            },
        )
        self.assertEqual(
            output,
            '"Unsafe" <a href="http://example.com/x=&y=" rel="nofollow">http:...</a> '
            '&quot;Safe&quot; <a href="http://example.com?x=&y=" rel="nofollow">http:...</a>'
        )

    @setup({'urlizetrunc02': '{{ a|urlizetrunc:"8" }} {{ b|urlizetrunc:"8" }}'})
    def test_urlizetrunc02(self):
        output = render(
            'urlizetrunc02',
            {
                'a': '"Unsafe" http://example.com/x=&y=',
                'b': mark_safe('&quot;Safe&quot; http://example.com?x=&amp;y='),
            },
        )
        self.assertEqual(
            output,
            '&quot;Unsafe&quot; <a href="http://example.com/x=&y=" rel="nofollow">http:...</a> '
            '&quot;Safe&quot; <a href="http://example.com?x=&y=" rel="nofollow">http:...</a>'
        )
