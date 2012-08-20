# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import unittest

from django.contrib.webdesign.lorem_ipsum import *
from django.template import loader, Context


class WebdesignTest(unittest.TestCase):

    def test_words(self):
        self.assertEqual(words(7), 'lorem ipsum dolor sit amet consectetur adipisicing')

    def test_paragraphs(self):
        self.assertEqual(paragraphs(1),
                         ['Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.'])

    def test_lorem_tag(self):
        t = loader.get_template_from_string("{% load webdesign %}{% lorem 3 w %}")
        self.assertEqual(t.render(Context({})),
                         'lorem ipsum dolor')
