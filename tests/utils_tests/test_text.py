# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
import warnings
from unittest import skipUnless

from django.test import SimpleTestCase, ignore_warnings
from django.test.utils import reset_warning_registry
from django.utils import six, text
from django.utils.deprecation import RemovedInDjango19Warning
from django.utils.encoding import force_text
from django.utils.functional import lazy
from django.utils.translation import override

lazystr = lazy(force_text, six.text_type)

IS_WIDE_BUILD = (len('\U0001F4A9') == 1)


class TestUtilsText(SimpleTestCase):

    def test_get_text_list(self):
        self.assertEqual(text.get_text_list(['a', 'b', 'c', 'd']), 'a, b, c or d')
        self.assertEqual(text.get_text_list(['a', 'b', 'c'], 'and'), 'a, b and c')
        self.assertEqual(text.get_text_list(['a', 'b'], 'and'), 'a and b')
        self.assertEqual(text.get_text_list(['a']), 'a')
        self.assertEqual(text.get_text_list([]), '')
        with override('ar'):
            self.assertEqual(text.get_text_list(['a', 'b', 'c']), "a، b أو c")

    def test_smart_split(self):
        testdata = [
            ('This is "a person" test.',
                ['This', 'is', '"a person"', 'test.']),
            ('This is "a person\'s" test.',
                ['This', 'is', '"a person\'s"', 'test.']),
            ('This is "a person\\"s" test.',
                ['This', 'is', '"a person\\"s"', 'test.']),
            ('"a \'one',
                ['"a', "'one"]),
            ('all friends\' tests',
                ['all', 'friends\'', 'tests']),
            ('url search_page words="something else"',
                ['url', 'search_page', 'words="something else"']),
            ("url search_page words='something else'",
                ['url', 'search_page', "words='something else'"]),
            ('url search_page words "something else"',
                ['url', 'search_page', 'words', '"something else"']),
            ('url search_page words-"something else"',
                ['url', 'search_page', 'words-"something else"']),
            ('url search_page words=hello',
                ['url', 'search_page', 'words=hello']),
            ('url search_page words="something else',
                ['url', 'search_page', 'words="something', 'else']),
            ("cut:','|cut:' '",
                ["cut:','|cut:' '"]),
            (lazystr("a b c d"),  # Test for #20231
                ['a', 'b', 'c', 'd']),
        ]
        for test, expected in testdata:
            self.assertEqual(list(text.smart_split(test)), expected)

    def test_truncate_chars(self):
        truncator = text.Truncator(
            'The quick brown fox jumped over the lazy dog.'
        )
        self.assertEqual('The quick brown fox jumped over the lazy dog.',
            truncator.chars(100)),
        self.assertEqual('The quick brown fox ...',
            truncator.chars(23)),
        self.assertEqual('The quick brown fo.....',
            truncator.chars(23, '.....')),

        # Ensure that we normalize our unicode data first
        nfc = text.Truncator('o\xfco\xfco\xfco\xfc')
        nfd = text.Truncator('ou\u0308ou\u0308ou\u0308ou\u0308')
        self.assertEqual('oüoüoüoü', nfc.chars(8))
        self.assertEqual('oüoüoüoü', nfd.chars(8))
        self.assertEqual('oü...', nfc.chars(5))
        self.assertEqual('oü...', nfd.chars(5))

        # Ensure the final length is calculated correctly when there are
        # combining characters with no precomposed form, and that combining
        # characters are not split up.
        truncator = text.Truncator('-B\u030AB\u030A----8')
        self.assertEqual('-B\u030A...', truncator.chars(5))
        self.assertEqual('-B\u030AB\u030A-...', truncator.chars(7))
        self.assertEqual('-B\u030AB\u030A----8', truncator.chars(8))

        # Ensure the length of the end text is correctly calculated when it
        # contains combining characters with no precomposed form.
        truncator = text.Truncator('-----')
        self.assertEqual('---B\u030A', truncator.chars(4, 'B\u030A'))
        self.assertEqual('-----', truncator.chars(5, 'B\u030A'))

        # Make a best effort to shorten to the desired length, but requesting
        # a length shorter than the ellipsis shouldn't break
        self.assertEqual('...', text.Truncator('asdf').chars(1))

    def test_truncate_words(self):
        truncator = text.Truncator('The quick brown fox jumped over the lazy '
            'dog.')
        self.assertEqual('The quick brown fox jumped over the lazy dog.',
            truncator.words(10))
        self.assertEqual('The quick brown fox...', truncator.words(4))
        self.assertEqual('The quick brown fox[snip]',
            truncator.words(4, '[snip]'))

    def test_truncate_html_words(self):
        truncator = text.Truncator('<p id="par"><strong><em>The quick brown fox'
            ' jumped over the lazy dog.</em></strong></p>')
        self.assertEqual('<p id="par"><strong><em>The quick brown fox jumped over'
            ' the lazy dog.</em></strong></p>', truncator.words(10, html=True))
        self.assertEqual('<p id="par"><strong><em>The quick brown fox...</em>'
            '</strong></p>', truncator.words(4, html=True))
        self.assertEqual('<p id="par"><strong><em>The quick brown fox....</em>'
            '</strong></p>', truncator.words(4, '....', html=True))
        self.assertEqual('<p id="par"><strong><em>The quick brown fox</em>'
            '</strong></p>', truncator.words(4, '', html=True))

        # Test with new line inside tag
        truncator = text.Truncator('<p>The quick <a href="xyz.html"\n'
            'id="mylink">brown fox</a> jumped over the lazy dog.</p>')
        self.assertEqual('<p>The quick <a href="xyz.html"\n'
            'id="mylink">brown...</a></p>', truncator.words(3, '...', html=True))

        # Test self-closing tags
        truncator = text.Truncator('<br/>The <hr />quick brown fox jumped over'
            ' the lazy dog.')
        self.assertEqual('<br/>The <hr />quick brown...',
            truncator.words(3, '...', html=True))
        truncator = text.Truncator('<br>The <hr/>quick <em>brown fox</em> '
            'jumped over the lazy dog.')
        self.assertEqual('<br>The <hr/>quick <em>brown...</em>',
            truncator.words(3, '...', html=True))

        # Test html entities
        truncator = text.Truncator('<i>Buenos d&iacute;as!'
            ' &#x00bf;C&oacute;mo est&aacute;?</i>')
        self.assertEqual('<i>Buenos d&iacute;as! &#x00bf;C&oacute;mo...</i>',
            truncator.words(3, '...', html=True))
        truncator = text.Truncator('<p>I &lt;3 python, what about you?</p>')
        self.assertEqual('<p>I &lt;3 python...</p>',
            truncator.words(3, '...', html=True))

    def test_wrap(self):
        digits = '1234 67 9'
        self.assertEqual(text.wrap(digits, 100), '1234 67 9')
        self.assertEqual(text.wrap(digits, 9), '1234 67 9')
        self.assertEqual(text.wrap(digits, 8), '1234 67\n9')

        self.assertEqual(text.wrap('short\na long line', 7),
                         'short\na long\nline')

        self.assertEqual(text.wrap('do-not-break-long-words please? ok', 8),
                         'do-not-break-long-words\nplease?\nok')

        long_word = 'l%sng' % ('o' * 20)
        self.assertEqual(text.wrap(long_word, 20), long_word)
        self.assertEqual(text.wrap('a %s word' % long_word, 10),
                         'a\n%s\nword' % long_word)

    def test_normalize_newlines(self):
        self.assertEqual(text.normalize_newlines("abc\ndef\rghi\r\n"),
                         "abc\ndef\nghi\n")
        self.assertEqual(text.normalize_newlines("\n\r\r\n\r"), "\n\n\n\n")
        self.assertEqual(text.normalize_newlines("abcdefghi"), "abcdefghi")
        self.assertEqual(text.normalize_newlines(""), "")

    def test_normalize_newlines_bytes(self):
        """normalize_newlines should be able to handle bytes too"""
        normalized = text.normalize_newlines(b"abc\ndef\rghi\r\n")
        self.assertEqual(normalized, "abc\ndef\nghi\n")
        self.assertIsInstance(normalized, six.text_type)

    def test_slugify(self):
        items = (
            ('Hello, World!', 'hello-world'),
            ('spam & eggs', 'spam-eggs'),
        )
        for value, output in items:
            self.assertEqual(text.slugify(value), output)

    def test_unescape_entities(self):
        items = [
            ('', ''),
            ('foo', 'foo'),
            ('&amp;', '&'),
            ('&#x26;', '&'),
            ('&#38;', '&'),
            ('foo &amp; bar', 'foo & bar'),
            ('foo & bar', 'foo & bar'),
        ]
        for value, output in items:
            self.assertEqual(text.unescape_entities(value), output)

    def test_get_valid_filename(self):
        filename = "^&'@{}[],$=!-#()%+~_123.txt"
        self.assertEqual(text.get_valid_filename(filename), "-_123.txt")

    def test_compress_sequence(self):
        data = [{'key': i} for i in range(10)]
        seq = list(json.JSONEncoder().iterencode(data))
        seq = [s.encode('utf-8') for s in seq]
        actual_length = len(b''.join(seq))
        out = text.compress_sequence(seq)
        compressed_length = len(b''.join(out))
        self.assertTrue(compressed_length < actual_length)

    @ignore_warnings(category=RemovedInDjango19Warning)
    def test_javascript_quote(self):
        input = "<script>alert('Hello \\xff.\n Welcome\there\r');</script>"
        output = r"<script>alert(\'Hello \\xff.\n Welcome\there\r\');<\/script>"
        self.assertEqual(text.javascript_quote(input), output)

        # Exercising quote_double_quotes keyword argument
        input = '"Text"'
        self.assertEqual(text.javascript_quote(input), '"Text"')
        self.assertEqual(text.javascript_quote(input, quote_double_quotes=True),
                         '&quot;Text&quot;')

    @ignore_warnings(category=RemovedInDjango19Warning)
    @skipUnless(IS_WIDE_BUILD, 'Not running in a wide build of Python')
    def test_javascript_quote_unicode(self):
        input = "<script>alert('Hello \\xff.\n Wel𝕃come\there\r');</script>"
        output = r"<script>alert(\'Hello \\xff.\n Wel𝕃come\there\r\');<\/script>"
        self.assertEqual(text.javascript_quote(input), output)

    def test_deprecation(self):
        reset_warning_registry()
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            text.javascript_quote('thingy')
            self.assertEqual(len(w), 1)
            self.assertIn('escapejs()', repr(w[0].message))
