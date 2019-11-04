from django.test import SimpleTestCase
from django.utils.lorem_ipsum import WORDS

from ..utils import setup


class LoremTagTests(SimpleTestCase):

    @setup({'lorem1': '{% lorem 3 w %}'})
    def test_lorem1(self):
        output = self.engine.render_to_string('lorem1')
        self.assertEqual(output, 'lorem ipsum dolor')

    @setup({'lorem_random': '{% lorem 3 w random %}'})
    def test_lorem_random(self):
        output = self.engine.render_to_string('lorem_random')
        words = output.split(' ')
        self.assertEqual(len(words), 3)
        for word in words:
            self.assertIn(word, WORDS)
