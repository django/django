# coding: utf-8

from __future__ import unicode_literals

from django.contrib.flatpages.models import FlatPage
from django.test import TestCase


class FlatpageModelTests(TestCase):

    def test_get_absolute_url_urlencodes(self):
        pf = FlatPage(title="Café!", url='/café/')
        self.assertEqual(pf.get_absolute_url(), '/caf%C3%A9/')


