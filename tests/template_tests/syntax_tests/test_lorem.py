from django.template.base import TemplateSyntaxError
from django.test import SimpleTestCase
from django.utils.lorem_ipsum import COMMON_P, WORDS

from ..utils import setup


class LoremTagTests(SimpleTestCase):
    @setup({"lorem1": "{% lorem 3 w %}"})
    def test_lorem1(self):
        output = self.engine.render_to_string("lorem1")
        self.assertEqual(output, "lorem ipsum dolor")

    @setup({"lorem_random": "{% lorem 3 w random %}"})
    def test_lorem_random(self):
        output = self.engine.render_to_string("lorem_random")
        words = output.split(" ")
        self.assertEqual(len(words), 3)
        for word in words:
            self.assertIn(word, WORDS)

    @setup({"lorem_default": "{% lorem %}"})
    def test_lorem_default(self):
        output = self.engine.render_to_string("lorem_default")
        self.assertEqual(output, COMMON_P)

    @setup({"lorem_syntax_error": "{% lorem 1 2 3 4 %}"})
    def test_lorem_syntax(self):
        msg = "Incorrect format for 'lorem' tag"
        with self.assertRaisesMessage(TemplateSyntaxError, msg):
            self.engine.render_to_string("lorem_syntax_error")

    @setup({"lorem_multiple_paragraphs": "{% lorem 2 p %}"})
    def test_lorem_multiple_paragraphs(self):
        output = self.engine.render_to_string("lorem_multiple_paragraphs")
        self.assertEqual(output.count("<p>"), 2)

    @setup({"lorem_incorrect_count": "{% lorem two p %}"})
    def test_lorem_incorrect_count(self):
        output = self.engine.render_to_string("lorem_incorrect_count")
        self.assertEqual(output.count("<p>"), 1)
