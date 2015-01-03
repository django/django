# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import unittest

from django.template import Context, Template


class WebdesignTest(unittest.TestCase):

    def test_lorem_tag(self):
        t = Template("{% load webdesign %}{% lorem 3 w %}")
        self.assertEqual(t.render(Context({})),
                         'lorem ipsum dolor')
