# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

import codecs
import os
import unittest

from django.conf import settings
from django.core.cache.backends.base import BaseCache
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils.encoding import force_text
from django.utils._os import symlinks_supported
from django.utils import six

from django.contrib.staticfiles import storage

from .test_base import (CollectionTestCase, TestDefaults, TEST_SETTINGS, TEST_ROOT, TestHashedFiles,
                        BaseCollectionTestCase, BaseStaticFilesTestCase, hashed_file_path)


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
        searched_locations = ', '.join(lines[4:])
        # AppDirectoriesFinder searched locations
        self.assertIn(os.path.join('staticfiles_tests', 'apps', 'test', 'static'),
                      searched_locations)
        self.assertIn(os.path.join('staticfiles_tests', 'apps', 'no_label', 'static'),
                      searched_locations)
        self.assertIn(os.path.join('django', 'contrib', 'admin', 'static'),
                      searched_locations)
        # FileSystemFinder searched locations
        self.assertIn(TEST_SETTINGS['STATICFILES_DIRS'][1][1], searched_locations)
        self.assertIn(TEST_SETTINGS['STATICFILES_DIRS'][0], searched_locations)
        # DefaultStorageFinder searched locations
        self.assertIn(os.path.join('staticfiles_tests', 'project', 'site_media', 'media'),
                      searched_locations)


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


class TestNoFilesCreated(object):

    def test_no_files_created(self):
        """
        Make sure no files were create in the destination directory.
        """
        self.assertEqual(os.listdir(settings.STATIC_ROOT), [])


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


@override_settings(
    STATICFILES_STORAGE='staticfiles_tests.storage.DummyStorage',
)
class TestCollectionNonLocalStorage(CollectionTestCase, TestNoFilesCreated):
    """
    Tests for #15035
    """
    pass


# we set DEBUG to False here since the template tag wouldn't work otherwise
@override_settings(**dict(
    TEST_SETTINGS,
    STATICFILES_STORAGE='django.contrib.staticfiles.storage.CachedStaticFilesStorage',
    DEBUG=False,
))
class TestCollectionCachedStorage(TestHashedFiles, BaseCollectionTestCase,
        BaseStaticFilesTestCase, TestCase):
    """
    Tests for the Cache busting storage
    """
    def test_cache_invalidation(self):
        name = "cached/styles.css"
        hashed_name = "cached/styles.bb84a0240107.css"
        # check if the cache is filled correctly as expected
        cache_key = storage.staticfiles_storage.hash_key(name)
        cached_name = storage.staticfiles_storage.hashed_files.get(cache_key)
        self.assertEqual(self.hashed_file_path(name), cached_name)
        # clearing the cache to make sure we re-set it correctly in the url method
        storage.staticfiles_storage.hashed_files.clear()
        cached_name = storage.staticfiles_storage.hashed_files.get(cache_key)
        self.assertEqual(cached_name, None)
        self.assertEqual(self.hashed_file_path(name), hashed_name)
        cached_name = storage.staticfiles_storage.hashed_files.get(cache_key)
        self.assertEqual(cached_name, hashed_name)

    def test_cache_key_memcache_validation(self):
        """
        Handle cache key creation correctly, see #17861.
        """
        name = "/some crazy/long filename/ with spaces Here and ?#%#$/other/stuff/some crazy/long filename/ with spaces Here and ?#%#$/other/stuff/some crazy/long filename/ with spaces Here and ?#%#$/other/stuff/some crazy/long filename/ with spaces Here and ?#%#$/other/stuff/some crazy/long filename/ with spaces Here and ?#%#$/other/stuff/some crazy/" + "\x16" + "\xb4"
        cache_key = storage.staticfiles_storage.hash_key(name)
        cache_validator = BaseCache({})
        cache_validator.validate_key(cache_key)
        self.assertEqual(cache_key, 'staticfiles:821ea71ef36f95b3922a77f7364670e7')


# we set DEBUG to False here since the template tag wouldn't work otherwise
@override_settings(**dict(
    TEST_SETTINGS,
    STATICFILES_STORAGE='django.contrib.staticfiles.storage.ManifestStaticFilesStorage',
    DEBUG=False,
))
class TestCollectionManifestStorage(TestHashedFiles, BaseCollectionTestCase,
        BaseStaticFilesTestCase, TestCase):
    """
    Tests for the Cache busting storage
    """

    def setUp(self):
        super(TestCollectionManifestStorage, self).setUp()

        self._clear_filename = os.path.join(self.testfiles_path, 'cleared.txt')
        with open(self._clear_filename, 'w') as f:
            f.write('to be deleted in one test')

    def tearDown(self):
        super(TestCollectionManifestStorage, self).tearDown()
        if os.path.exists(self._clear_filename):
            os.unlink(self._clear_filename)

    def test_manifest_exists(self):
        filename = storage.staticfiles_storage.manifest_name
        path = storage.staticfiles_storage.path(filename)
        self.assertTrue(os.path.exists(path))

    def test_loaded_cache(self):
        self.assertNotEqual(storage.staticfiles_storage.hashed_files, {})
        manifest_content = storage.staticfiles_storage.read_manifest()
        self.assertIn('"version": "%s"' %
                      storage.staticfiles_storage.manifest_version,
                      force_text(manifest_content))

    def test_parse_cache(self):
        hashed_files = storage.staticfiles_storage.hashed_files
        manifest = storage.staticfiles_storage.load_manifest()
        self.assertEqual(hashed_files, manifest)

    def test_clear_empties_manifest(self):
        cleared_file_name = os.path.join('test', 'cleared.txt')
        # collect the additional file
        self.run_collectstatic()

        hashed_files = storage.staticfiles_storage.hashed_files
        self.assertIn(cleared_file_name, hashed_files)

        manifest_content = storage.staticfiles_storage.load_manifest()
        self.assertIn(cleared_file_name, manifest_content)

        original_path = storage.staticfiles_storage.path(cleared_file_name)
        self.assertTrue(os.path.exists(original_path))

        # delete the original file form the app, collect with clear
        os.unlink(self._clear_filename)
        self.run_collectstatic(clear=True)

        self.assertFileNotFound(original_path)

        hashed_files = storage.staticfiles_storage.hashed_files
        self.assertNotIn(cleared_file_name, hashed_files)

        manifest_content = storage.staticfiles_storage.load_manifest()
        self.assertNotIn(cleared_file_name, manifest_content)


# we set DEBUG to False here since the template tag wouldn't work otherwise
@override_settings(**dict(
    TEST_SETTINGS,
    STATICFILES_STORAGE='staticfiles_tests.storage.SimpleCachedStaticFilesStorage',
    DEBUG=False,
))
class TestCollectionSimpleCachedStorage(BaseCollectionTestCase,
        BaseStaticFilesTestCase, TestCase):
    """
    Tests for the Cache busting storage
    """
    hashed_file_path = hashed_file_path

    def test_template_tag_return(self):
        """
        Test the CachedStaticFilesStorage backend.
        """
        self.assertStaticRaises(ValueError,
                                "does/not/exist.png",
                                "/static/does/not/exist.png")
        self.assertStaticRenders("test/file.txt",
                                 "/static/test/file.deploy12345.txt")
        self.assertStaticRenders("cached/styles.css",
                                 "/static/cached/styles.deploy12345.css")
        self.assertStaticRenders("path/",
                                 "/static/path/")
        self.assertStaticRenders("path/?query",
                                 "/static/path/?query")

    def test_template_tag_simple_content(self):
        relpath = self.hashed_file_path("cached/styles.css")
        self.assertEqual(relpath, "cached/styles.deploy12345.css")
        with storage.staticfiles_storage.open(relpath) as relfile:
            content = relfile.read()
            self.assertNotIn(b"cached/other.css", content)
            self.assertIn(b"other.deploy12345.css", content)


@unittest.skipUnless(symlinks_supported(),
                     "Must be able to symlink to run this test.")
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
