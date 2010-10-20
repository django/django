"""
Tests for django.core.servers.
"""

import os

import django
from django.test import TestCase
from django.core.handlers.wsgi import WSGIHandler
from django.core.servers.basehttp import AdminMediaHandler

from django.conf import settings

class AdminMediaHandlerTests(TestCase):

    def setUp(self):
        self.admin_media_file_path = os.path.abspath(
            os.path.join(django.__path__[0], 'contrib', 'admin', 'media')
        )
        self.handler = AdminMediaHandler(WSGIHandler())

    def test_media_urls(self):
        """
        Tests that URLs that look like absolute file paths after the
        settings.ADMIN_MEDIA_PREFIX don't turn into absolute file paths.
        """
        # Cases that should work on all platforms.
        data = (
            ('%scss/base.css' % settings.ADMIN_MEDIA_PREFIX, ('css', 'base.css')),
        )
        # Cases that should raise an exception.
        bad_data = ()

        # Add platform-specific cases.
        if os.sep == '/':
            data += (
                # URL, tuple of relative path parts.
                ('%s\\css/base.css' % settings.ADMIN_MEDIA_PREFIX, ('\\css', 'base.css')),
            )
            bad_data += (
                '%s/css/base.css' % settings.ADMIN_MEDIA_PREFIX,
                '%s///css/base.css' % settings.ADMIN_MEDIA_PREFIX,
                '%s../css/base.css' % settings.ADMIN_MEDIA_PREFIX,
            )
        elif os.sep == '\\':
            bad_data += (
                '%sC:\css/base.css' % settings.ADMIN_MEDIA_PREFIX,
                '%s/\\css/base.css' % settings.ADMIN_MEDIA_PREFIX,
                '%s\\css/base.css' % settings.ADMIN_MEDIA_PREFIX,
                '%s\\\\css/base.css' % settings.ADMIN_MEDIA_PREFIX
            )
        for url, path_tuple in data:
            try:
                output = self.handler.file_path(url)
            except ValueError:
                self.fail("Got a ValueError exception, but wasn't expecting"
                          " one. URL was: %s" % url)
            rel_path = os.path.join(*path_tuple)
            desired = os.path.normcase(
                os.path.join(self.admin_media_file_path, rel_path))
            self.assertEqual(output, desired,
                "Got: %s, Expected: %s, URL was: %s" % (output, desired, url))
        for url in bad_data:
            try:
                output = self.handler.file_path(url)
            except ValueError:
                continue
            self.fail('URL: %s should have caused a ValueError exception.'
                      % url)
