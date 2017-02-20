import unittest

from django.utils.lorem_ipsum import paragraphs, words


class WebdesignTest(unittest.TestCase):

    def test_words(self):
        self.assertEqual(words(7), 'lorem ipsum dolor sit amet consectetur adipisicing')

    def test_paragraphs(self):
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
