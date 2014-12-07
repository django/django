# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.template.defaultfilters import title
from django.test import SimpleTestCase

from ..utils import setup


class TitleTests(SimpleTestCase):

    @setup({'title1': '{{ a|title }}'})
    def test_title1(self):
        output = self.engine.render_to_string('title1', {'a': 'JOE\'S CRAB SHACK'})
        self.assertEqual(output, 'Joe&#39;s Crab Shack')

    @setup({'title2': '{{ a|title }}'})
    def test_title2(self):
        output = self.engine.render_to_string('title2', {'a': '555 WEST 53RD STREET'})
        self.assertEqual(output, '555 West 53rd Street')


class FunctionTests(SimpleTestCase):

    def test_title(self):
        self.assertEqual(title('a nice title, isn\'t it?'), "A Nice Title, Isn't It?")

    def test_unicode(self):
        self.assertEqual(title('discoth\xe8que'), 'Discoth\xe8que')

    def test_non_string_input(self):
        self.assertEqual(title(123), '123')
