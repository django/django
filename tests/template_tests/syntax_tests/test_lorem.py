from django.test import TestCase

from .utils import render, setup


class LoremTagTests(TestCase):

    @setup({'lorem1': '{% lorem 3 w %}'})
    def test_lorem1(self):
        output = render('lorem1')
        self.assertEqual(output, 'lorem ipsum dolor')
