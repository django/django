# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

import os
import sys
import unittest

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.test import override_settings
from django.utils.functional import empty
from django.utils import six

from django.contrib.staticfiles import storage
from django.contrib.staticfiles.management.commands import collectstatic

from .storage import DummyStorage
from .test_base import StaticFilesTestCase, BaseCollectionTestCase


class TestConfiguration(StaticFilesTestCase):
    def test_location_empty(self):
        err = six.StringIO()
        for root in ['', None]:
            with override_settings(STATIC_ROOT=root):
                with six.assertRaisesRegex(
                        self, ImproperlyConfigured,
                        'without having set the STATIC_ROOT setting to a filesystem path'):
                    call_command('collectstatic', interactive=False, verbosity=0, stderr=err)

    def test_local_storage_detection_helper(self):
        staticfiles_storage = storage.staticfiles_storage
        try:
            storage.staticfiles_storage._wrapped = empty
            with override_settings(STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage'):
                command = collectstatic.Command()
                self.assertTrue(command.is_local_storage())

            storage.staticfiles_storage._wrapped = empty
            with override_settings(STATICFILES_STORAGE='staticfiles_tests.storage.DummyStorage'):
                command = collectstatic.Command()
                self.assertFalse(command.is_local_storage())

            collectstatic.staticfiles_storage = storage.FileSystemStorage()
            command = collectstatic.Command()
            self.assertTrue(command.is_local_storage())

            collectstatic.staticfiles_storage = DummyStorage()
            command = collectstatic.Command()
            self.assertFalse(command.is_local_storage())
        finally:
            staticfiles_storage._wrapped = empty
            collectstatic.staticfiles_storage = staticfiles_storage
            storage.staticfiles_storage = staticfiles_storage


class TestTemplateTag(StaticFilesTestCase):

    def test_template_tag(self):
        self.assertStaticRenders("does/not/exist.png", "/static/does/not/exist.png")
        self.assertStaticRenders("testfile.txt", "/static/testfile.txt")


class CustomStaticFilesStorage(storage.StaticFilesStorage):
    """
    Used in TestStaticFilePermissions
    """
    def __init__(self, *args, **kwargs):
        kwargs['file_permissions_mode'] = 0o640
        kwargs['directory_permissions_mode'] = 0o740
        super(CustomStaticFilesStorage, self).__init__(*args, **kwargs)


@unittest.skipIf(sys.platform.startswith('win'),
                 "Windows only partially supports chmod.")
class TestStaticFilePermissions(BaseCollectionTestCase, StaticFilesTestCase):

    command_params = {'interactive': False,
                      'post_process': True,
                      'verbosity': 0,
                      'ignore_patterns': ['*.ignoreme'],
                      'use_default_ignore_patterns': True,
                      'clear': False,
                      'link': False,
                      'dry_run': False}

    def setUp(self):
        self.umask = 0o027
        self.old_umask = os.umask(self.umask)
        super(TestStaticFilePermissions, self).setUp()

    def tearDown(self):
        os.umask(self.old_umask)
        super(TestStaticFilePermissions, self).tearDown()

    # Don't run collectstatic command in this test class.
    def run_collectstatic(self, **kwargs):
        pass

    @override_settings(FILE_UPLOAD_PERMISSIONS=0o655,
                       FILE_UPLOAD_DIRECTORY_PERMISSIONS=0o765)
    def test_collect_static_files_permissions(self):
        collectstatic.Command().execute(**self.command_params)
        test_file = os.path.join(settings.STATIC_ROOT, "test.txt")
        test_dir = os.path.join(settings.STATIC_ROOT, "subdir")
        file_mode = os.stat(test_file)[0] & 0o777
        dir_mode = os.stat(test_dir)[0] & 0o777
        self.assertEqual(file_mode, 0o655)
        self.assertEqual(dir_mode, 0o765)

    @override_settings(FILE_UPLOAD_PERMISSIONS=None,
                       FILE_UPLOAD_DIRECTORY_PERMISSIONS=None)
    def test_collect_static_files_default_permissions(self):
        collectstatic.Command().execute(**self.command_params)
        test_file = os.path.join(settings.STATIC_ROOT, "test.txt")
        test_dir = os.path.join(settings.STATIC_ROOT, "subdir")
        file_mode = os.stat(test_file)[0] & 0o777
        dir_mode = os.stat(test_dir)[0] & 0o777
        self.assertEqual(file_mode, 0o666 & ~self.umask)
        self.assertEqual(dir_mode, 0o777 & ~self.umask)

    @override_settings(FILE_UPLOAD_PERMISSIONS=0o655,
                       FILE_UPLOAD_DIRECTORY_PERMISSIONS=0o765,
                       STATICFILES_STORAGE='staticfiles_tests.tests.CustomStaticFilesStorage')
    def test_collect_static_files_subclass_of_static_storage(self):
        collectstatic.Command().execute(**self.command_params)
        test_file = os.path.join(settings.STATIC_ROOT, "test.txt")
        test_dir = os.path.join(settings.STATIC_ROOT, "subdir")
        file_mode = os.stat(test_file)[0] & 0o777
        dir_mode = os.stat(test_dir)[0] & 0o777
        self.assertEqual(file_mode, 0o640)
        self.assertEqual(dir_mode, 0o740)
