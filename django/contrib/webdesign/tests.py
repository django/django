# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import unittest

from django.template import loader, Context


class WebdesignTest(unittest.TestCase):

    def test_lorem_tag(self):
        t = loader.get_template_from_string("{% load webdesign %}{% lorem 3 w %}")
        self.assertEqual(t.render(Context({})),
                         'lorem ipsum dolor')
