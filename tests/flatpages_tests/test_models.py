# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.contrib.flatpages.models import FlatPage
from django.test import SimpleTestCase
from django.test.utils import override_script_prefix


class FlatpageModelTests(SimpleTestCase):

    def test_get_absolute_url_urlencodes(self):
        pf = FlatPage(title="Café!", url='/café/')
        self.assertEqual(pf.get_absolute_url(), '/caf%C3%A9/')

    @override_script_prefix('/beverages/')
    def test_get_absolute_url_honors_script_prefix(self):
        pf = FlatPage(title="Tea!", url='/tea/')
        self.assertEqual(pf.get_absolute_url(), '/beverages/tea/')
