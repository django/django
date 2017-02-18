# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.template import Context, Template
from django.test import SimpleTestCase, modify_settings


@modify_settings(INSTALLED_APPS={'append': 'django.contrib.webdesign'})
class WebdesignTest(SimpleTestCase):

    def test_lorem_tag(self):
        t = Template("{% load webdesign %}{% lorem 3 w %}")
        self.assertEqual(t.render(Context({})),
                         'lorem ipsum dolor')
