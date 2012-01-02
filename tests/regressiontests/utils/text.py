# -*- coding: utf-8 -*-
import unittest

from django.utils import text

class TestUtilsText(unittest.TestCase):

    def test_truncate_chars(self):
        truncator = text.Truncator(
            u'The quick brown fox jumped over the lazy dog.'
        )
        self.assertEqual(u'The quick brown fox jumped over the lazy dog.',
            truncator.chars(100)),
        self.assertEqual(u'The quick brown fox ...',
            truncator.chars(23)),
        self.assertEqual(u'The quick brown fo.....',
            truncator.chars(23, '.....')),

        # Ensure that we normalize our unicode data first
        nfc = text.Truncator(u'o\xfco\xfco\xfco\xfc')
        nfd = text.Truncator(u'ou\u0308ou\u0308ou\u0308ou\u0308')
        self.assertEqual(u'oüoüoüoü', nfc.chars(8))
        self.assertEqual(u'oüoüoüoü', nfd.chars(8))
        self.assertEqual(u'oü...', nfc.chars(5))
        self.assertEqual(u'oü...', nfd.chars(5))

        # Ensure the final length is calculated correctly when there are
        # combining characters with no precomposed form, and that combining
        # characters are not split up.
        truncator = text.Truncator(u'-B\u030AB\u030A----8')
        self.assertEqual(u'-B\u030A...', truncator.chars(5))
        self.assertEqual(u'-B\u030AB\u030A-...', truncator.chars(7))
        self.assertEqual(u'-B\u030AB\u030A----8', truncator.chars(8))

        # Ensure the length of the end text is correctly calculated when it
        # contains combining characters with no precomposed form.
        truncator = text.Truncator(u'-----')
        self.assertEqual(u'---B\u030A', truncator.chars(4, u'B\u030A'))
        self.assertEqual(u'-----', truncator.chars(5, u'B\u030A'))

        # Make a best effort to shorten to the desired length, but requesting
        # a length shorter than the ellipsis shouldn't break
        self.assertEqual(u'...', text.Truncator(u'asdf').chars(1))

    def test_truncate_words(self):
        truncator = text.Truncator(u'The quick brown fox jumped over the lazy '
            'dog.')
        self.assertEqual(u'The quick brown fox jumped over the lazy dog.',
            truncator.words(10))
        self.assertEqual(u'The quick brown fox...', truncator.words(4))
        self.assertEqual(u'The quick brown fox[snip]',
            truncator.words(4, '[snip]'))

    def test_truncate_html_words(self):
        truncator = text.Truncator('<p><strong><em>The quick brown fox jumped '
            'over the lazy dog.</em></strong></p>')
        self.assertEqual(u'<p><strong><em>The quick brown fox jumped over the '
            'lazy dog.</em></strong></p>', truncator.words(10, html=True))
        self.assertEqual(u'<p><strong><em>The quick brown fox...</em>'
            '</strong></p>', truncator.words(4, html=True))
        self.assertEqual(u'<p><strong><em>The quick brown fox....</em>'
            '</strong></p>', truncator.words(4, '....', html=True))
        self.assertEqual(u'<p><strong><em>The quick brown fox</em></strong>'
            '</p>', truncator.words(4, '', html=True))
        # Test with new line inside tag
        truncator = text.Truncator('<p>The quick <a href="xyz.html"\n'
            'id="mylink">brown fox</a> jumped over the lazy dog.</p>')
        self.assertEqual(u'<p>The quick <a href="xyz.html"\n'
            'id="mylink">brown...</a></p>', truncator.words(3, '...', html=True))

    def test_old_truncate_words(self):
        self.assertEqual(u'The quick brown fox jumped over the lazy dog.',
            text.truncate_words(u'The quick brown fox jumped over the lazy dog.', 10))
        self.assertEqual(u'The quick brown fox ...',
            text.truncate_words('The quick brown fox jumped over the lazy dog.', 4))
        self.assertEqual(u'The quick brown fox ....',
            text.truncate_words('The quick brown fox jumped over the lazy dog.', 4, '....'))

    def test_old_truncate_html_words(self):
        self.assertEqual(u'<p><strong><em>The quick brown fox jumped over the lazy dog.</em></strong></p>',
            text.truncate_html_words('<p><strong><em>The quick brown fox jumped over the lazy dog.</em></strong></p>', 10))
        self.assertEqual(u'<p><strong><em>The quick brown fox ...</em></strong></p>',
            text.truncate_html_words('<p><strong><em>The quick brown fox jumped over the lazy dog.</em></strong></p>', 4))
        self.assertEqual(u'<p><strong><em>The quick brown fox ....</em></strong></p>',
            text.truncate_html_words('<p><strong><em>The quick brown fox jumped over the lazy dog.</em></strong></p>', 4, '....'))
        self.assertEqual(u'<p><strong><em>The quick brown fox</em></strong></p>',
            text.truncate_html_words('<p><strong><em>The quick brown fox jumped over the lazy dog.</em></strong></p>', 4, None))

    def test_wrap(self):
        digits = '1234 67 9'
        self.assertEqual(text.wrap(digits, 100), u'1234 67 9')
        self.assertEqual(text.wrap(digits, 9), u'1234 67 9')
        self.assertEqual(text.wrap(digits, 8), u'1234 67\n9')

        self.assertEqual(text.wrap('short\na long line', 7),
                         u'short\na long\nline')

        self.assertEqual(text.wrap('do-not-break-long-words please? ok', 8),
                         u'do-not-break-long-words\nplease?\nok')

        long_word = 'l%sng' % ('o' * 20)
        self.assertEqual(text.wrap(long_word, 20), long_word)
        self.assertEqual(text.wrap('a %s word' % long_word, 10),
                         u'a\n%s\nword' % long_word)
