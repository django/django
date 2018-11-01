import unittest
from unittest import mock

from django.utils.lorem_ipsum import paragraph, paragraphs, sentence, words


class LoremIpsumTests(unittest.TestCase):
    def test_negative_words(self):
        """words(n) returns n + 19 words, even if n is negative."""
        self.assertEqual(
            words(-5),
            'lorem ipsum dolor sit amet consectetur adipisicing elit sed do '
            'eiusmod tempor incididunt ut'
        )

    def test_same_or_less_common_words(self):
        """words(n) for n < 19."""
        self.assertEqual(words(7), 'lorem ipsum dolor sit amet consectetur adipisicing')

    def test_common_words_in_string(self):
        """words(n) starts with the 19 standard lorem ipsum words for n > 19."""
        self.assertTrue(
            words(25).startswith(
                'lorem ipsum dolor sit amet consectetur adipisicing elit sed '
                'do eiusmod tempor incididunt ut labore et dolore magna aliqua'
            )
        )

    def test_more_words_than_common(self):
        """words(n) returns n words for n > 19."""
        self.assertEqual(len(words(25).split()), 25)

    def test_common_large_number_of_words(self):
        """words(n) has n words when n is greater than len(WORDS)."""
        self.assertEqual(len(words(500).split()), 500)

    @mock.patch('django.utils.lorem_ipsum.random.sample')
    def test_not_common_words(self, mock_sample):
        """words(n, common=False) returns random words."""
        mock_sample.return_value = ['exercitationem', 'perferendis']
        self.assertEqual(words(2, common=False), 'exercitationem perferendis')

    def test_sentence_starts_with_capital(self):
        """A sentence starts with a capital letter."""
        self.assertTrue(sentence()[0].isupper())

    @mock.patch('django.utils.lorem_ipsum.random.sample')
    @mock.patch('django.utils.lorem_ipsum.random.choice')
    @mock.patch('django.utils.lorem_ipsum.random.randint')
    def test_sentence(self, mock_randint, mock_choice, mock_sample):
        """
        Sentences are built using some number of phrases and a set of words.
        """
        mock_randint.return_value = 2  # Use two phrases.
        mock_sample.return_value = ['exercitationem', 'perferendis']
        mock_choice.return_value = '?'
        value = sentence()
        self.assertEqual(mock_randint.call_count, 3)
        self.assertEqual(mock_sample.call_count, 2)
        self.assertEqual(mock_choice.call_count, 1)
        self.assertEqual(value, 'Exercitationem perferendis, exercitationem perferendis?')

    @mock.patch('django.utils.lorem_ipsum.random.choice')
    def test_sentence_ending(self, mock_choice):
        """Sentences end with a question mark or a period."""
        mock_choice.return_value = '?'
        self.assertIn(sentence()[-1], '?')
        mock_choice.return_value = '.'
        self.assertIn(sentence()[-1], '.')

    @mock.patch('django.utils.lorem_ipsum.random.sample')
    @mock.patch('django.utils.lorem_ipsum.random.choice')
    @mock.patch('django.utils.lorem_ipsum.random.randint')
    def test_paragraph(self, mock_paragraph_randint, mock_choice, mock_sample):
        """paragraph() generates a single paragraph."""
        # Make creating 2 sentences use 2 phrases.
        mock_paragraph_randint.return_value = 2
        mock_sample.return_value = ['exercitationem', 'perferendis']
        mock_choice.return_value = '.'
        value = paragraph()
        self.assertEqual(mock_paragraph_randint.call_count, 7)
        self.assertEqual(value, (
            'Exercitationem perferendis, exercitationem perferendis. '
            'Exercitationem perferendis, exercitationem perferendis.'
        ))

    @mock.patch('django.utils.lorem_ipsum.random.sample')
    @mock.patch('django.utils.lorem_ipsum.random.choice')
    @mock.patch('django.utils.lorem_ipsum.random.randint')
    def test_paragraphs_not_common(self, mock_randint, mock_choice, mock_sample):
        """
        paragraphs(1, common=False) generating one paragraph that's not the
        COMMON_P paragraph.
        """
        # Make creating 2 sentences use 2 phrases.
        mock_randint.return_value = 2
        mock_sample.return_value = ['exercitationem', 'perferendis']
        mock_choice.return_value = '.'
        self.assertEqual(
            paragraphs(1, common=False),
            [
                'Exercitationem perferendis, exercitationem perferendis. '
                'Exercitationem perferendis, exercitationem perferendis.'
            ]
        )
        self.assertEqual(mock_randint.call_count, 7)

    def test_paragraphs(self):
        """paragraphs(1) uses the COMMON_P paragraph."""
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
