import unittest

from django.utils.lorem_ipsum import words, sentence, paragraph, paragraphs


class WebdesignTest(unittest.TestCase):

    def test_negative_words(self):
        """
        Common words when passing negative words
        """
        self.assertEqual(words(-5), 'lorem ipsum dolor sit amet consectetur adipisicing elit sed do eiusmod '
                                    'tempor incididunt ut')

    def test_same_or_less_common_words(self):
        """
        First n standard lorem ipsum words
        """
        self.assertEqual(words(7), 'lorem ipsum dolor sit amet consectetur adipisicing')

    def test_common_words_in_string(self):
        """
        String starts with all the standard lorem ipsum words
        """
        self.assertTrue(words(25).startswith('lorem ipsum dolor sit amet consectetur adipisicing elit sed do eiusmod '
                                             'tempor incididunt ut labore et dolore magna aliqua'))

    def test_more_words_than_common(self):
        """
        String has n words
        """
        self.assertEqual(len(words(25).split()), 25)

    def test_common_crazy_amount_of_words(self):
        """
        String has n words when n is greater than WORDS
        """
        self.assertEqual(len(words(500).split()), 500)

    def test_not_common_words(self):
        """
        String does not start with the common words
        """
        self.assertFalse(words(5, False).startswith('lorem ipsum dolor sit amet'))

    def test_sentence_starts_with_capital(self):
        """
        Sentence starts with a capital letter
        """
        self.assertTrue(sentence()[0].isupper())
        self.assertTrue(sentence()[1].islower())

    def test_sentence_ends_well(self):
        """
        Sentence ends with a question mark or a period
        """
        self.assertIn(sentence()[-1], '?.')

    def test_paragraph(self):
        """
        Paragraph is a string
        """
        par = paragraph()
        self.assertIsInstance(par, str)
        self.assertTrue(len(par) > 0)

    def test_paragraphs(self):
        """
        Common lorem ipsum paragraph
        """
        self.assertEqual(
            paragraphs(1), [
                'Lorem ipsum dolor sit amet, consectetur adipisicing elit, '
                'sed do eiusmod tempor incididunt ut labore et dolore magna '
                'aliqua. Ut enim ad minim veniam, quis nostrud exercitation '
                'ullamco laboris nisi ut aliquip ex ea commodo consequat. '
                'Duis aute irure dolor in reprehenderit in voluptate velit '
                'esse cillum dolore eu fugiat nulla pariatur. Excepteur sint '
                'occaecat cupidatat non proident, sunt in culpa qui officia '
                'deserunt mollit anim id est laborum.'
            ]
        )

    def test_paragraphs_not_common(self):
        """
        Not common lorem ipsum paragraph
        """
        para = paragraphs(1, False)
        self.assertTrue(len(para) > 0)
        self.assertNotEqual(
            para, [
                'Lorem ipsum dolor sit amet, consectetur adipisicing elit, '
                'sed do eiusmod tempor incididunt ut labore et dolore magna '
                'aliqua. Ut enim ad minim veniam, quis nostrud exercitation '
                'ullamco laboris nisi ut aliquip ex ea commodo consequat. '
                'Duis aute irure dolor in reprehenderit in voluptate velit '
                'esse cillum dolore eu fugiat nulla pariatur. Excepteur sint '
                'occaecat cupidatat non proident, sunt in culpa qui officia '
                'deserunt mollit anim id est laborum.'
            ]
        )
