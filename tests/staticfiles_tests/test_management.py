from __future__ import unicode_literals

import codecs
import os
import shutil
import tempfile
import unittest

from admin_scripts.tests import AdminScriptTestCase

from django.conf import settings
from django.contrib.staticfiles import storage
from django.contrib.staticfiles.management.commands import collectstatic
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.test import override_settings
from django.test.utils import extend_sys_path
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


class TestFindStatic(TestDefaults, CollectionTestCase):
    """
    Test ``findstatic`` management command.
    """
    def _get_file(self, filepath):
        path = call_command('findstatic', filepath, all=False, verbosity=0, stdout=six.StringIO())
        with codecs.open(force_text(path), "r", "utf-8") as f:
            return f.read()

    def test_all_files(self):
        """
        Test that findstatic returns all candidate files if run without --first and -v1.
        """
        result = call_command('findstatic', 'test/file.txt', verbosity=1, stdout=six.StringIO())
        lines = [l.strip() for l in result.split('\n')]
        self.assertEqual(len(lines), 3)  # three because there is also the "Found <file> here" line
        self.assertIn('project', force_text(lines[1]))
        self.assertIn('apps', force_text(lines[2]))

    def test_all_files_less_verbose(self):
        """
        Test that findstatic returns all candidate files if run without --first and -v0.
        """
        result = call_command('findstatic', 'test/file.txt', verbosity=0, stdout=six.StringIO())
        lines = [l.strip() for l in result.split('\n')]
        self.assertEqual(len(lines), 2)
        self.assertIn('project', force_text(lines[0]))
        self.assertIn('apps', force_text(lines[1]))

    def test_all_files_more_verbose(self):
        """
        Test that findstatic returns all candidate files if run without --first and -v2.
        Also, test that findstatic returns the searched locations with -v2.
        """
        result = call_command('findstatic', 'test/file.txt', verbosity=2, stdout=six.StringIO())
        lines = [l.strip() for l in result.split('\n')]
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
        msg = 'without having set the STATIC_ROOT setting to a filesystem path'
        err = six.StringIO()
        for root in ['', None]:
            with override_settings(STATIC_ROOT=root):
                with self.assertRaisesMessage(ImproperlyConfigured, msg):
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


class TestCollectionHelpSubcommand(AdminScriptTestCase):
    @override_settings(STATIC_ROOT=None)
    def test_missing_settings_dont_prevent_help(self):
        """
        Even if the STATIC_ROOT setting is not set, one can still call the
        `manage.py help collectstatic` command.
        """
        self.write_settings('settings.py', apps=['django.contrib.staticfiles'])
        out, err = self.run_manage(['help', 'collectstatic'])
        self.assertNoOutput(err)


class TestCollection(TestDefaults, CollectionTestCase):
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

    @override_settings(STATICFILES_STORAGE='staticfiles_tests.storage.PathNotImplementedStorage')
    def test_handle_path_notimplemented(self):
        self.run_collectstatic()
        self.assertFileNotFound('cleared.txt')


class TestCollectionExcludeNoDefaultIgnore(TestDefaults, CollectionTestCase):
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


@override_settings(INSTALLED_APPS=[
    'staticfiles_tests.apps.staticfiles_config.IgnorePatternsAppConfig',
    'staticfiles_tests.apps.test',
])
class TestCollectionCustomIgnorePatterns(CollectionTestCase):
    def test_custom_ignore_patterns(self):
        """
        A custom ignore_patterns list, ['*.css'] in this case, can be specified
        in an AppConfig definition.
        """
        self.assertFileNotFound('test/nonascii.css')
        self.assertFileContains('test/.hidden', 'should be ignored')


class TestCollectionDryRun(TestNoFilesCreated, CollectionTestCase):
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
        'staticfiles_test_app',
        'staticfiles_tests.apps.no_label',
    """
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.temp_dir)

        # get modification and access times for no_label/static/file2.txt
        self.orig_path = os.path.join(TEST_ROOT, 'apps', 'no_label', 'static', 'file2.txt')
        self.orig_mtime = os.path.getmtime(self.orig_path)
        self.orig_atime = os.path.getatime(self.orig_path)

        # prepare duplicate of file2.txt from a temporary app
        # this file will have modification time older than no_label/static/file2.txt
        # anyway it should be taken to STATIC_ROOT because the temporary app is before
        # 'no_label' app in installed apps
        self.temp_app_path = os.path.join(self.temp_dir, 'staticfiles_test_app')
        self.testfile_path = os.path.join(self.temp_app_path, 'static', 'file2.txt')

        os.makedirs(self.temp_app_path)
        with open(os.path.join(self.temp_app_path, '__init__.py'), 'w+'):
            pass

        os.makedirs(os.path.dirname(self.testfile_path))
        with open(self.testfile_path, 'w+') as f:
            f.write('duplicate of file2.txt')

        os.utime(self.testfile_path, (self.orig_atime - 1, self.orig_mtime - 1))

        self.settings_with_test_app = self.modify_settings(
            INSTALLED_APPS={'prepend': 'staticfiles_test_app'})
        with extend_sys_path(self.temp_dir):
            self.settings_with_test_app.enable()

        super(TestCollectionFilesOverride, self).setUp()

    def tearDown(self):
        super(TestCollectionFilesOverride, self).tearDown()
        self.settings_with_test_app.disable()

    def test_ordering_override(self):
        """
        Test if collectstatic takes files in proper order
        """
        self.assertFileContains('file2.txt', 'duplicate of file2.txt')

        # run collectstatic again
        self.run_collectstatic()

        self.assertFileContains('file2.txt', 'duplicate of file2.txt')


# The collectstatic test suite already has conflicting files since both
# project/test/file.txt and apps/test/static/test/file.txt are collected. To
# properly test for the warning not happening unless we tell it to explicitly,
# we remove the project directory and will add back a conflicting file later.
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
        return force_text(out.getvalue())

    def test_no_warning(self):
        """
        There isn't a warning if there isn't a duplicate destination.
        """
        output = self._collectstatic_output(clear=True)
        self.assertNotIn(self.warning_string, output)

    def test_warning(self):
        """
        There is a warning when there are duplicate destinations.
        """
        static_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, static_dir)

        duplicate = os.path.join(static_dir, 'test', 'file.txt')
        os.mkdir(os.path.dirname(duplicate))
        with open(duplicate, 'w+') as f:
            f.write('duplicate of file.txt')

        with self.settings(STATICFILES_DIRS=[static_dir]):
            output = self._collectstatic_output(clear=True)
        self.assertIn(self.warning_string, output)

        os.remove(duplicate)

        # Make sure the warning went away again.
        with self.settings(STATICFILES_DIRS=[static_dir]):
            output = self._collectstatic_output(clear=True)
        self.assertNotIn(self.warning_string, output)


@override_settings(STATICFILES_STORAGE='staticfiles_tests.storage.DummyStorage')
class TestCollectionNonLocalStorage(TestNoFilesCreated, CollectionTestCase):
    """
    Tests for #15035
    """
    pass


@unittest.skipUnless(symlinks_supported(), "Must be able to symlink to run this test.")
class TestCollectionLinks(TestDefaults, CollectionTestCase):
    """
    Test ``--link`` option for ``collectstatic`` management command.

    Note that by inheriting ``TestDefaults`` we repeat all
    the standard file resolving tests here, to make sure using
    ``--link`` does not change the file-selection semantics.
    """
    def run_collectstatic(self, clear=False):
        super(TestCollectionLinks, self).run_collectstatic(link=True, clear=clear)

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

    def test_clear_broken_symlink(self):
        """
        With ``--clear``, broken symbolic links are deleted.
        """
        nonexistent_file_path = os.path.join(settings.STATIC_ROOT, 'nonexistent.txt')
        broken_symlink_path = os.path.join(settings.STATIC_ROOT, 'symlink.txt')
        os.symlink(nonexistent_file_path, broken_symlink_path)
        self.run_collectstatic(clear=True)
        self.assertFalse(os.path.lexists(broken_symlink_path))
