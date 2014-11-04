# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.core.urlresolvers import set_script_prefix, clear_script_prefix
from django.contrib.flatpages.models import FlatPage
from django.test import TestCase
from django.test import override_settings

class FlatpageModelTests(TestCase):

    def test_get_absolute_url_urlencodes(self):
        pf = FlatPage(title="Café!", url='/café/')
        self.assertEqual(pf.get_absolute_url(), '/caf%C3%A9/')

    def test_get_absolute_url_honors_script_prefix(self):
        pf = FlatPage(title="Tea!", url='/tea/')
        set_script_prefix('/beverages/')
        try:
            self.assertEqual(pf.get_absolute_url(), '/beverages/tea/')
        finally:
            clear_script_prefix()

    @override_settings(
        ROOT_URLCONF='django.contrib.flatpages.tests.urls',
    )
    def test_get_absolute_url_with_include_prefix_no_slash(self):
        pf = FlatPage(title="TestUrlWithIncludePrefix", url=r"/test_url/")
        # Note: We expect the url to NOT have a slash, because the URL_CONF is defined without a slash.
        self.assertEqual(pf.get_absolute_url(), r'/flatpage_roottest_url/')

    @override_settings(
        ROOT_URLCONF='django.contrib.flatpages.tests.flatpage_test_urls_prefix_slash',
    )
    def test_get_absolute_url_with_include_prefix_slash(self):
        pf = FlatPage(title="TestUrlWithIncludePrefix", url=r"/test_url/")
        # Note: We expect the url to NOT have a slash, because the URL_CONF is defined without a slash.
        self.assertEqual(pf.get_absolute_url(), r'/flatpage/test_url/')

    @override_settings(
        ROOT_URLCONF='django.contrib.flatpages.tests.flatpage_test_urls_absolute',
    )
    def test_get_absolute_url_set_with_absolute_url(self):
        pf = FlatPage(title="TestHardCodedUrl", url=r"/hard_coded_url/")
        self.assertEqual(pf.get_absolute_url(), r'/flatpage/')

    @override_settings(
        MIDDLEWARE_CLASSES=('django.contrib.flatpages.middleware.FlatpageFallbackMiddleware',),
    )
    def test_get_absolute_url_with_middleware(self):
        pf = FlatPage(title="TestMiddlewareWorkingUrl", url=r"/url_for_middleware/")
        self.assertEqual(pf.get_absolute_url(), r'/url_for_middleware/')
    
    @override_settings(
        MIDDLEWARE_CLASSES=('django.contrib.flatpages.middleware.FlatpageFallbackMiddleware',),
    )
    def test_get_absolute_url_cant_find_random_url_with_middleware(self):
        pf = FlatPage(title="TestMiddlewareNotWorkingUrl", url=r"/url_for_middleware/")
        self.assertNotEqual(pf.get_absolute_url(), r'/random_url/')
    

