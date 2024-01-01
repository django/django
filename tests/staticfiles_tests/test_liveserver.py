"""
A subset of the tests in tests/servers/tests exercising
django.contrib.staticfiles.testing.StaticLiveServerTestCase instead of
django.test.LiveServerTestCase.
"""

import os
from urllib.request import urlopen

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.core.exceptions import ImproperlyConfigured
from django.test import modify_settings, override_settings

TEST_ROOT = os.path.dirname(__file__)
TEST_SETTINGS = {
    "MEDIA_URL": "media/",
    "STATIC_URL": "static/",
    "MEDIA_ROOT": os.path.join(TEST_ROOT, "project", "site_media", "media"),
    "STATIC_ROOT": os.path.join(TEST_ROOT, "project", "site_media", "static"),
}


class LiveServerBase(StaticLiveServerTestCase):
    available_apps = []

    @classmethod
    def setUpClass(cls):
        # Override settings
        cls.settings_override = override_settings(**TEST_SETTINGS)
        cls.settings_override.enable()
        cls.addClassCleanup(cls.settings_override.disable)
        super().setUpClass()


class StaticLiveServerChecks(LiveServerBase):
    @classmethod
    def setUpClass(cls):
        # If contrib.staticfiles isn't configured properly, the exception
        # should bubble up to the main thread.
        old_STATIC_URL = TEST_SETTINGS["STATIC_URL"]
        TEST_SETTINGS["STATIC_URL"] = None
        try:
            cls.raises_exception()
        finally:
            TEST_SETTINGS["STATIC_URL"] = old_STATIC_URL

    @classmethod
    def tearDownClass(cls):
        # skip it, as setUpClass doesn't call its parent either
        pass

    @classmethod
    def raises_exception(cls):
        try:
            super().setUpClass()
        except ImproperlyConfigured:
            # This raises ImproperlyConfigured("You're using the staticfiles
            # app without having set the required STATIC_URL setting.")
            pass
        else:
            raise Exception("setUpClass() should have raised an exception.")

    def test_test_test(self):
        # Intentionally empty method so that the test is picked up by the
        # test runner and the overridden setUpClass() method is executed.
        pass


class StaticLiveServerView(LiveServerBase):
    def urlopen(self, url):
        return urlopen(self.live_server_url + url)

    # The test is going to access a static file stored in this application.
    @modify_settings(INSTALLED_APPS={"append": "staticfiles_tests.apps.test"})
    def test_collectstatic_emulation(self):
        """
        StaticLiveServerTestCase use of staticfiles' serve() allows it
        to discover app's static assets without having to collectstatic first.
        """
        with self.urlopen("/static/test/file.txt") as f:
            self.assertEqual(f.read().rstrip(b"\r\n"), b"In static directory.")
