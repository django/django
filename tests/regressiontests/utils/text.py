from django.test import TestCase

from django.utils import text

class TestUtilsText(TestCase):
    def test_truncate_words(self):
        self.assertEqual(u'The quick brown fox jumped over the lazy dog.',
            text.truncate_words(u'The quick brown fox jumped over the lazy dog.', 10))
        self.assertEqual(u'The quick brown fox ...',
            text.truncate_words('The quick brown fox jumped over the lazy dog.', 4))
        self.assertEqual(u'The quick brown fox ....',
            text.truncate_words('The quick brown fox jumped over the lazy dog.', 4, '....'))
        self.assertEqual(u'<p><strong><em>The quick brown fox jumped over the lazy dog.</em></strong></p>',
            text.truncate_html_words('<p><strong><em>The quick brown fox jumped over the lazy dog.</em></strong></p>', 10))
        self.assertEqual(u'<p><strong><em>The quick brown fox ...</em></strong></p>',
            text.truncate_html_words('<p><strong><em>The quick brown fox jumped over the lazy dog.</em></strong></p>', 4))
        self.assertEqual(u'<p><strong><em>The quick brown fox ....</em></strong></p>',
            text.truncate_html_words('<p><strong><em>The quick brown fox jumped over the lazy dog.</em></strong></p>', 4, '....'))
        self.assertEqual(u'<p><strong><em>The quick brown fox</em></strong></p>',
            text.truncate_html_words('<p><strong><em>The quick brown fox jumped over the lazy dog.</em></strong></p>', 4, None))
