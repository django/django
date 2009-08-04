"""
Tests for django.core.servers.
"""

import os

import django
from django.test import TestCase
from django.core.handlers.wsgi import WSGIHandler
from django.core.servers.basehttp import AdminMediaHandler


class AdminMediaHandlerTests(TestCase):

    def setUp(self):
        self.admin_media_file_path = \
            os.path.join(django.__path__[0], 'contrib', 'admin', 'media')
        self.handler = AdminMediaHandler(WSGIHandler())

    def test_media_urls(self):
        """
        Tests that URLs that look like absolute file paths after the
        settings.ADMIN_MEDIA_PREFIX don't turn into absolute file paths.
        """
        # Cases that should work on all platforms.
        data = (
            ('/media/css/base.css', ('css', 'base.css')),
        )
        # Cases that should raise an exception.
        bad_data = ()

        # Add platform-specific cases.
        if os.sep == '/':
            data += (
                # URL, tuple of relative path parts.
                ('/media/\\css/base.css', ('\\css', 'base.css')),
            )
            bad_data += (
                '/media//css/base.css',
                '/media////css/base.css',
                '/media/../css/base.css',
            )
        elif os.sep == '\\':
            bad_data += (
                '/media/C:\css/base.css',
                '/media//\\css/base.css',
                '/media/\\css/base.css',
                '/media/\\\\css/base.css'
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
