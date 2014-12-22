from django.test import SimpleTestCase

from ..utils import render, setup


class LoremTagTests(SimpleTestCase):

    @setup({'lorem1': '{% lorem 3 w %}'})
    def test_lorem1(self):
        output = render('lorem1')
        self.assertEqual(output, 'lorem ipsum dolor')
