from django.test import SimpleTestCase

from ..utils import render, setup


class TitleTests(SimpleTestCase):

    @setup({'title1': '{{ a|title }}'})
    def test_title1(self):
        output = render('title1', {'a': 'JOE\'S CRAB SHACK'})
        self.assertEqual(output, 'Joe&#39;s Crab Shack')

    @setup({'title2': '{{ a|title }}'})
    def test_title2(self):
        output = render('title2', {'a': '555 WEST 53RD STREET'})
        self.assertEqual(output, '555 West 53rd Street')
