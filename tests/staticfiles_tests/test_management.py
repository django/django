from __future__ import unicode_literals

import codecs
import os
import shutil
import unittest

from django.conf import settings
from django.contrib.staticfiles import storage
from django.contrib.staticfiles.management.commands import collectstatic
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.test import override_settings
from django.utils import six
from django.utils._os import symlinks_supported
from django.utils.encoding import force_text
from django.utils.functional import empty

from .cases import CollectionTestCase, StaticFilesTestCase, TestDefaults
from .settings import TEST_ROOT, TEST_SETTINGS
from .storage import DummyStorage


class TestNoFilesCreated(object):

    def test_no_files_created(self):
        """
        Make sure no files were create in the destination directory.
        """
        self.assertEqual(os.listdir(settings.STATIC_ROOT), [])


class TestFindStatic(CollectionTestCase, TestDefaults):
    """
    Test ``findstatic`` management command.
    """
    def _get_file(self, filepath):
        out = six.StringIO()
        call_command('findstatic', filepath, all=False, verbosity=0, stdout=out)
        out.seek(0)
        lines = [l.strip() for l in out.readlines()]
        with codecs.open(force_text(lines[0].strip()), "r", "utf-8") as f:
            return f.read()

    def test_all_files(self):
        """
        Test that findstatic returns all candidate files if run without --first and -v1.
        """
        out = six.StringIO()
        call_command('findstatic', 'test/file.txt', verbosity=1, stdout=out)
        out.seek(0)
        lines = [l.strip() for l in out.readlines()]
        self.assertEqual(len(lines), 3)  # three because there is also the "Found <file> here" line
        self.assertIn('project', force_text(lines[1]))
        self.assertIn('apps', force_text(lines[2]))

    def test_all_files_less_verbose(self):
        """
        Test that findstatic returns all candidate files if run without --first and -v0.
        """
        out = six.StringIO()
        call_command('findstatic', 'test/file.txt', verbosity=0, stdout=out)
        out.seek(0)
        lines = [l.strip() for l in out.readlines()]
        self.assertEqual(len(lines), 2)
        self.assertIn('project', force_text(lines[0]))
        self.assertIn('apps', force_text(lines[1]))

    def test_all_files_more_verbose(self):
        """
        Test that findstatic returns all candidate files if run without --first and -v2.
        Also, test that findstatic returns the searched locations with -v2.
        """
        out = six.StringIO()
        call_command('findstatic', 'test/file.txt', verbosity=2, stdout=out)
        out.seek(0)
        lines = [l.strip() for l in out.readlines()]
        self.assertIn('project', force_text(lines[1]))
        self.assertIn('apps', force_text(lines[2]))
        self.assertIn("Looking in the following locations:", force_text(lines[3]))
        searched_locations = ', '.join(force_text(x) for x in lines[4:])
        # AppDirectoriesFinder searched locations
        self.assertIn(os.path.join('staticfiles_tests', 'apps', 'test', 'static'), searched_locations)
        self.assertIn(os.path.join('staticfiles_tests', 'apps', 'no_label', 'static'), searched_locations)
        # FileSystemFinder searched locations
        self.assertIn(TEST_SETTINGS['STATICFILES_DIRS'][1][1], searched_locations)
        self.assertIn(TEST_SETTINGS['STATICFILES_DIRS'][0], searched_locations)
        # DefaultStorageFinder searched locations
        self.assertIn(
            os.path.join('staticfiles_tests', 'project', 'site_media', 'media'),
            searched_locations
        )


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
            with self.settings(STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage'):
                command = collectstatic.Command()
                self.assertTrue(command.is_local_storage())

            storage.staticfiles_storage._wrapped = empty
            with self.settings(STATICFILES_STORAGE='staticfiles_tests.storage.DummyStorage'):
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


class TestCollection(CollectionTestCase, TestDefaults):
    """
    Test ``collectstatic`` management command.
    """
    def test_ignore(self):
        """
        Test that -i patterns are ignored.
        """
        self.assertFileNotFound('test/test.ignoreme')

    def test_common_ignore_patterns(self):
        """
        Common ignore patterns (*~, .*, CVS) are ignored.
        """
        self.assertFileNotFound('test/.hidden')
        self.assertFileNotFound('test/backup~')
        self.assertFileNotFound('test/CVS')


class TestCollectionClear(CollectionTestCase):
    """
    Test the ``--clear`` option of the ``collectstatic`` management command.
    """
    def run_collectstatic(self, **kwargs):
        clear_filepath = os.path.join(settings.STATIC_ROOT, 'cleared.txt')
        with open(clear_filepath, 'w') as f:
            f.write('should be cleared')
        super(TestCollectionClear, self).run_collectstatic(clear=True)

    def test_cleared_not_found(self):
        self.assertFileNotFound('cleared.txt')

    def test_dir_not_exists(self, **kwargs):
        shutil.rmtree(six.text_type(settings.STATIC_ROOT))
        super(TestCollectionClear, self).run_collectstatic(clear=True)


class TestCollectionExcludeNoDefaultIgnore(CollectionTestCase, TestDefaults):
    """
    Test ``--exclude-dirs`` and ``--no-default-ignore`` options of the
    ``collectstatic`` management command.
    """
    def run_collectstatic(self):
        super(TestCollectionExcludeNoDefaultIgnore, self).run_collectstatic(
            use_default_ignore_patterns=False)

    def test_no_common_ignore_patterns(self):
        """
        With --no-default-ignore, common ignore patterns (*~, .*, CVS)
        are not ignored.
        """
        self.assertFileContains('test/.hidden', 'should be ignored')
        self.assertFileContains('test/backup~', 'should be ignored')
        self.assertFileContains('test/CVS', 'should be ignored')


class TestCollectionDryRun(CollectionTestCase, TestNoFilesCreated):
    """
    Test ``--dry-run`` option for ``collectstatic`` management command.
    """
    def run_collectstatic(self):
        super(TestCollectionDryRun, self).run_collectstatic(dry_run=True)


class TestCollectionFilesOverride(CollectionTestCase):
    """
    Test overriding duplicated files by ``collectstatic`` management command.
    Check for proper handling of apps order in installed apps even if file modification
    dates are in different order:
        'staticfiles_tests.apps.test',
        'staticfiles_tests.apps.no_label',
    """
    def setUp(self):
        self.orig_path = os.path.join(TEST_ROOT, 'apps', 'no_label', 'static', 'file2.txt')
        # get modification and access times for no_label/static/file2.txt
        self.orig_mtime = os.path.getmtime(self.orig_path)
        self.orig_atime = os.path.getatime(self.orig_path)

        # prepare duplicate of file2.txt from no_label app
        # this file will have modification time older than no_label/static/file2.txt
        # anyway it should be taken to STATIC_ROOT because 'test' app is before
        # 'no_label' app in installed apps
        self.testfile_path = os.path.join(TEST_ROOT, 'apps', 'test', 'static', 'file2.txt')
        with open(self.testfile_path, 'w+') as f:
            f.write('duplicate of file2.txt')
        os.utime(self.testfile_path, (self.orig_atime - 1, self.orig_mtime - 1))
        super(TestCollectionFilesOverride, self).setUp()

    def tearDown(self):
        if os.path.exists(self.testfile_path):
            os.unlink(self.testfile_path)
        # set back original modification time
        os.utime(self.orig_path, (self.orig_atime, self.orig_mtime))
        super(TestCollectionFilesOverride, self).tearDown()

    def test_ordering_override(self):
        """
        Test if collectstatic takes files in proper order
        """
        self.assertFileContains('file2.txt', 'duplicate of file2.txt')

        # run collectstatic again
        self.run_collectstatic()

        self.assertFileContains('file2.txt', 'duplicate of file2.txt')

        # and now change modification time of no_label/static/file2.txt
        # test app is first in installed apps so file2.txt should remain unmodified
        mtime = os.path.getmtime(self.testfile_path)
        atime = os.path.getatime(self.testfile_path)
        os.utime(self.orig_path, (mtime + 1, atime + 1))

        # run collectstatic again
        self.run_collectstatic()

        self.assertFileContains('file2.txt', 'duplicate of file2.txt')


# The collectstatic test suite already has conflicting files since both
# project/test/file.txt and apps/test/static/test/file.txt are collected. To
# properly test for the warning not happening unless we tell it to explicitly,
# we only include static files from the default finders.
@override_settings(STATICFILES_DIRS=[])
class TestCollectionOverwriteWarning(CollectionTestCase):
    """
    Test warning in ``collectstatic`` output when a file is skipped because a
    previous file was already written to the same path.
    """
    # If this string is in the collectstatic output, it means the warning we're
    # looking for was emitted.
    warning_string = 'Found another file'

    def _collectstatic_output(self, **kwargs):
        """
        Run collectstatic, and capture and return the output. We want to run
        the command at highest verbosity, which is why we can't
        just call e.g. BaseCollectionTestCase.run_collectstatic()
        """
        out = six.StringIO()
        call_command('collectstatic', interactive=False, verbosity=3, stdout=out, **kwargs)
        out.seek(0)
        return out.read()

    def test_no_warning(self):
        """
        There isn't a warning if there isn't a duplicate destination.
        """
        output = self._collectstatic_output(clear=True)
        self.assertNotIn(self.warning_string, force_text(output))

    def test_warning(self):
        """
        There is a warning when there are duplicate destinations.
        """
        # Create new file in the no_label app that also exists in the test app.
        test_dir = os.path.join(TEST_ROOT, 'apps', 'no_label', 'static', 'test')
        if not os.path.exists(test_dir):
            os.mkdir(test_dir)

        try:
            duplicate_path = os.path.join(test_dir, 'file.txt')
            with open(duplicate_path, 'w+') as f:
                f.write('duplicate of file.txt')
            output = self._collectstatic_output(clear=True)
            self.assertIn(self.warning_string, force_text(output))
        finally:
            if os.path.exists(duplicate_path):
                os.unlink(duplicate_path)

        if os.path.exists(test_dir):
            os.rmdir(test_dir)

        # Make sure the warning went away again.
        output = self._collectstatic_output(clear=True)
        self.assertNotIn(self.warning_string, force_text(output))


@override_settings(STATICFILES_STORAGE='staticfiles_tests.storage.DummyStorage')
class TestCollectionNonLocalStorage(CollectionTestCase, TestNoFilesCreated):
    """
    Tests for #15035
    """
    pass


@unittest.skipUnless(symlinks_supported(), "Must be able to symlink to run this test.")
class TestCollectionLinks(CollectionTestCase, TestDefaults):
    """
    Test ``--link`` option for ``collectstatic`` management command.

    Note that by inheriting ``TestDefaults`` we repeat all
    the standard file resolving tests here, to make sure using
    ``--link`` does not change the file-selection semantics.
    """
    def run_collectstatic(self):
        super(TestCollectionLinks, self).run_collectstatic(link=True)

    def test_links_created(self):
        """
        With ``--link``, symbolic links are created.
        """
        self.assertTrue(os.path.islink(os.path.join(settings.STATIC_ROOT, 'test.txt')))

    def test_broken_symlink(self):
        """
        Test broken symlink gets deleted.
        """
        path = os.path.join(settings.STATIC_ROOT, 'test.txt')
        os.unlink(path)
        self.run_collectstatic()
        self.assertTrue(os.path.islink(path))
