# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import warnings

from django.test import SimpleTestCase
from django.utils import text

class TestUtilsText(SimpleTestCase):

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
            truncator.words(3, '...', html=True ))
        truncator = text.Truncator('<br>The <hr/>quick <em>brown fox</em> '
            'jumped over the lazy dog.')
        self.assertEqual('<br>The <hr/>quick <em>brown...</em>',
            truncator.words(3, '...', html=True ))

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

    def test_slugify(self):
        items = (
            ('Hello, World!', 'hello-world'),
            ('spam & eggs', 'spam-eggs'),
        )
        for value, output in items:
            self.assertEqual(text.slugify(value), output)
