# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

import codecs
import os
import posixpath
import shutil
import sys
import tempfile
import unittest

from django.conf import settings
from django.contrib.staticfiles import finders, storage
from django.contrib.staticfiles.management.commands import collectstatic
from django.contrib.staticfiles.management.commands.collectstatic import \
    Command as CollectstaticCommand
from django.core.cache.backends.base import BaseCache
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.template import Context, Template
from django.test import TestCase, override_settings
from django.utils import six
from django.utils._os import rmtree_errorhandler, symlinks_supported, upath
from django.utils.encoding import force_text
from django.utils.functional import empty

from .storage import DummyStorage

TEST_ROOT = os.path.dirname(upath(__file__))

TESTFILES_PATH = os.path.join(TEST_ROOT, 'apps', 'test', 'static', 'test')

TEST_SETTINGS = {
    'DEBUG': True,
    'MEDIA_URL': '/media/',
    'STATIC_URL': '/static/',
    'MEDIA_ROOT': os.path.join(TEST_ROOT, 'project', 'site_media', 'media'),
    'STATIC_ROOT': os.path.join(TEST_ROOT, 'project', 'site_media', 'static'),
    'STATICFILES_DIRS': (
        os.path.join(TEST_ROOT, 'project', 'documents'),
        ('prefix', os.path.join(TEST_ROOT, 'project', 'prefixed')),
    ),
    'STATICFILES_FINDERS': (
        'django.contrib.staticfiles.finders.FileSystemFinder',
        'django.contrib.staticfiles.finders.AppDirectoriesFinder',
        'django.contrib.staticfiles.finders.DefaultStorageFinder',
    ),
    'INSTALLED_APPS': (
        'django.contrib.staticfiles',
        'staticfiles_tests',
        'staticfiles_tests.apps.test',
        'staticfiles_tests.apps.no_label',
    ),
}


class BaseStaticFilesTestCase(object):
    """
    Test case with a couple utility assertions.
    """

    def assertFileContains(self, filepath, text):
        self.assertIn(text, self._get_file(force_text(filepath)),
                      "'%s' not in '%s'" % (text, filepath))

    def assertFileNotFound(self, filepath):
        self.assertRaises(IOError, self._get_file, filepath)

    def render_template(self, template, **kwargs):
        if isinstance(template, six.string_types):
            template = Template(template)
        return template.render(Context(kwargs)).strip()

    def static_template_snippet(self, path, asvar=False):
        if asvar:
            return "{%% load static from staticfiles %%}{%% static '%s' as var %%}{{ var }}" % path
        return "{%% load static from staticfiles %%}{%% static '%s' %%}" % path

    def assertStaticRenders(self, path, result, asvar=False, **kwargs):
        template = self.static_template_snippet(path, asvar)
        self.assertEqual(self.render_template(template, **kwargs), result)

    def assertStaticRaises(self, exc, path, result, asvar=False, **kwargs):
        self.assertRaises(exc, self.assertStaticRenders, path, result, **kwargs)


@override_settings(**TEST_SETTINGS)
class StaticFilesTestCase(BaseStaticFilesTestCase, TestCase):
    pass


class BaseCollectionTestCase(BaseStaticFilesTestCase):
    """
    Tests shared by all file finding features (collectstatic,
    findstatic, and static serve view).

    This relies on the asserts defined in BaseStaticFilesTestCase, but
    is separated because some test cases need those asserts without
    all these tests.
    """
    def setUp(self):
        super(BaseCollectionTestCase, self).setUp()
        temp_dir = tempfile.mkdtemp()
        # Override the STATIC_ROOT for all tests from setUp to tearDown
        # rather than as a context manager
        self.patched_settings = self.settings(STATIC_ROOT=temp_dir)
        self.patched_settings.enable()
        self.run_collectstatic()
        # Use our own error handler that can handle .svn dirs on Windows
        self.addCleanup(shutil.rmtree, temp_dir,
                        ignore_errors=True, onerror=rmtree_errorhandler)

    def tearDown(self):
        self.patched_settings.disable()
        super(BaseCollectionTestCase, self).tearDown()

    def run_collectstatic(self, **kwargs):
        call_command('collectstatic', interactive=False, verbosity=0,
                     ignore_patterns=['*.ignoreme'], **kwargs)

    def _get_file(self, filepath):
        assert filepath, 'filepath is empty.'
        filepath = os.path.join(settings.STATIC_ROOT, filepath)
        with codecs.open(filepath, "r", "utf-8") as f:
            return f.read()


class CollectionTestCase(BaseCollectionTestCase, StaticFilesTestCase):
    pass


class TestDefaults(object):
    """
    A few standard test cases.
    """
    def test_staticfiles_dirs(self):
        """
        Can find a file in a STATICFILES_DIRS directory.
        """
        self.assertFileContains('test.txt', 'Can we find')
        self.assertFileContains(os.path.join('prefix', 'test.txt'), 'Prefix')

    def test_staticfiles_dirs_subdir(self):
        """
        Can find a file in a subdirectory of a STATICFILES_DIRS
        directory.
        """
        self.assertFileContains('subdir/test.txt', 'Can we find')

    def test_staticfiles_dirs_priority(self):
        """
        File in STATICFILES_DIRS has priority over file in app.
        """
        self.assertFileContains('test/file.txt', 'STATICFILES_DIRS')

    def test_app_files(self):
        """
        Can find a file in an app static/ directory.
        """
        self.assertFileContains('test/file1.txt', 'file1 in the app dir')

    def test_nonascii_filenames(self):
        """
        Can find a file with non-ASCII character in an app static/ directory.
        """
        self.assertFileContains('test/⊗.txt', '⊗ in the app dir')

    def test_camelcase_filenames(self):
        """
        Can find a file with capital letters.
        """
        self.assertFileContains('test/camelCase.txt', 'camelCase')


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
        self.assertIn(os.path.join('staticfiles_tests', 'apps', 'test', 'static'),
                      searched_locations)
        self.assertIn(os.path.join('staticfiles_tests', 'apps', 'no_label', 'static'),
                      searched_locations)
        # FileSystemFinder searched locations
        self.assertIn(TEST_SETTINGS['STATICFILES_DIRS'][1][1], searched_locations)
        self.assertIn(TEST_SETTINGS['STATICFILES_DIRS'][0], searched_locations)
        # DefaultStorageFinder searched locations
        self.assertIn(os.path.join('staticfiles_tests', 'project', 'site_media', 'media'),
                      searched_locations)


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


def hashed_file_path(test, path):
    fullpath = test.render_template(test.static_template_snippet(path))
    return fullpath.replace(settings.STATIC_URL, '')


class TestHashedFiles(object):
    hashed_file_path = hashed_file_path

    def tearDown(self):
        # Clear hashed files to avoid side effects among tests.
        storage.staticfiles_storage.hashed_files.clear()

    def test_template_tag_return(self):
        """
        Test the CachedStaticFilesStorage backend.
        """
        self.assertStaticRaises(ValueError,
                                "does/not/exist.png",
                                "/static/does/not/exist.png")
        self.assertStaticRenders("test/file.txt",
                                 "/static/test/file.dad0999e4f8f.txt")
        self.assertStaticRenders("test/file.txt",
                                 "/static/test/file.dad0999e4f8f.txt", asvar=True)
        self.assertStaticRenders("cached/styles.css",
                                 "/static/cached/styles.bb84a0240107.css")
        self.assertStaticRenders("path/",
                                 "/static/path/")
        self.assertStaticRenders("path/?query",
                                 "/static/path/?query")

    def test_template_tag_simple_content(self):
        relpath = self.hashed_file_path("cached/styles.css")
        self.assertEqual(relpath, "cached/styles.bb84a0240107.css")
        with storage.staticfiles_storage.open(relpath) as relfile:
            content = relfile.read()
            self.assertNotIn(b"cached/other.css", content)
            self.assertIn(b"other.d41d8cd98f00.css", content)

    def test_path_ignored_completely(self):
        relpath = self.hashed_file_path("cached/css/ignored.css")
        self.assertEqual(relpath, "cached/css/ignored.6c77f2643390.css")
        with storage.staticfiles_storage.open(relpath) as relfile:
            content = relfile.read()
            self.assertIn(b'#foobar', content)
            self.assertIn(b'http:foobar', content)
            self.assertIn(b'https:foobar', content)
            self.assertIn(b'data:foobar', content)
            self.assertIn(b'//foobar', content)

    def test_path_with_querystring(self):
        relpath = self.hashed_file_path("cached/styles.css?spam=eggs")
        self.assertEqual(relpath,
                         "cached/styles.bb84a0240107.css?spam=eggs")
        with storage.staticfiles_storage.open(
                "cached/styles.bb84a0240107.css") as relfile:
            content = relfile.read()
            self.assertNotIn(b"cached/other.css", content)
            self.assertIn(b"other.d41d8cd98f00.css", content)

    def test_path_with_fragment(self):
        relpath = self.hashed_file_path("cached/styles.css#eggs")
        self.assertEqual(relpath, "cached/styles.bb84a0240107.css#eggs")
        with storage.staticfiles_storage.open(
                "cached/styles.bb84a0240107.css") as relfile:
            content = relfile.read()
            self.assertNotIn(b"cached/other.css", content)
            self.assertIn(b"other.d41d8cd98f00.css", content)

    def test_path_with_querystring_and_fragment(self):
        relpath = self.hashed_file_path("cached/css/fragments.css")
        self.assertEqual(relpath, "cached/css/fragments.75433540b096.css")
        with storage.staticfiles_storage.open(relpath) as relfile:
            content = relfile.read()
            self.assertIn(b'fonts/font.a4b0478549d0.eot?#iefix', content)
            self.assertIn(b'fonts/font.b8d603e42714.svg#webfontIyfZbseF', content)
            self.assertIn(b'data:font/woff;charset=utf-8;base64,d09GRgABAAAAADJoAA0AAAAAR2QAAQAAAAAAAAAAAAA', content)
            self.assertIn(b'#default#VML', content)

    def test_template_tag_absolute(self):
        relpath = self.hashed_file_path("cached/absolute.css")
        self.assertEqual(relpath, "cached/absolute.ae9ef2716fe3.css")
        with storage.staticfiles_storage.open(relpath) as relfile:
            content = relfile.read()
            self.assertNotIn(b"/static/cached/styles.css", content)
            self.assertIn(b"/static/cached/styles.bb84a0240107.css", content)
            self.assertIn(b'/static/cached/img/relative.acae32e4532b.png', content)

    def test_template_tag_denorm(self):
        relpath = self.hashed_file_path("cached/denorm.css")
        self.assertEqual(relpath, "cached/denorm.c5bd139ad821.css")
        with storage.staticfiles_storage.open(relpath) as relfile:
            content = relfile.read()
            self.assertNotIn(b"..//cached///styles.css", content)
            self.assertIn(b"../cached/styles.bb84a0240107.css", content)
            self.assertNotIn(b"url(img/relative.png )", content)
            self.assertIn(b'url("img/relative.acae32e4532b.png', content)

    def test_template_tag_relative(self):
        relpath = self.hashed_file_path("cached/relative.css")
        self.assertEqual(relpath, "cached/relative.b0375bd89156.css")
        with storage.staticfiles_storage.open(relpath) as relfile:
            content = relfile.read()
            self.assertNotIn(b"../cached/styles.css", content)
            self.assertNotIn(b'@import "styles.css"', content)
            self.assertNotIn(b'url(img/relative.png)', content)
            self.assertIn(b'url("img/relative.acae32e4532b.png")', content)
            self.assertIn(b"../cached/styles.bb84a0240107.css", content)

    def test_import_replacement(self):
        "See #18050"
        relpath = self.hashed_file_path("cached/import.css")
        self.assertEqual(relpath, "cached/import.2b1d40b0bbd4.css")
        with storage.staticfiles_storage.open(relpath) as relfile:
            self.assertIn(b"""import url("styles.bb84a0240107.css")""", relfile.read())

    def test_template_tag_deep_relative(self):
        relpath = self.hashed_file_path("cached/css/window.css")
        self.assertEqual(relpath, "cached/css/window.3906afbb5a17.css")
        with storage.staticfiles_storage.open(relpath) as relfile:
            content = relfile.read()
            self.assertNotIn(b'url(img/window.png)', content)
            self.assertIn(b'url("img/window.acae32e4532b.png")', content)

    def test_template_tag_url(self):
        relpath = self.hashed_file_path("cached/url.css")
        self.assertEqual(relpath, "cached/url.902310b73412.css")
        with storage.staticfiles_storage.open(relpath) as relfile:
            self.assertIn(b"https://", relfile.read())

    def test_post_processing(self):
        """Test that post_processing behaves correctly.

        Files that are alterable should always be post-processed; files that
        aren't should be skipped.

        collectstatic has already been called once in setUp() for this testcase,
        therefore we check by verifying behavior on a second run.
        """
        collectstatic_args = {
            'interactive': False,
            'verbosity': 0,
            'link': False,
            'clear': False,
            'dry_run': False,
            'post_process': True,
            'use_default_ignore_patterns': True,
            'ignore_patterns': ['*.ignoreme'],
        }

        collectstatic_cmd = CollectstaticCommand()
        collectstatic_cmd.set_options(**collectstatic_args)
        stats = collectstatic_cmd.collect()
        self.assertIn(os.path.join('cached', 'css', 'window.css'), stats['post_processed'])
        self.assertIn(os.path.join('cached', 'css', 'img', 'window.png'), stats['unmodified'])
        self.assertIn(os.path.join('test', 'nonascii.css'), stats['post_processed'])

    def test_css_import_case_insensitive(self):
        relpath = self.hashed_file_path("cached/styles_insensitive.css")
        self.assertEqual(relpath, "cached/styles_insensitive.c609562b6d3c.css")
        with storage.staticfiles_storage.open(relpath) as relfile:
            content = relfile.read()
            self.assertNotIn(b"cached/other.css", content)
            self.assertIn(b"other.d41d8cd98f00.css", content)

    @override_settings(
        STATICFILES_DIRS=(os.path.join(TEST_ROOT, 'project', 'faulty'),),
        STATICFILES_FINDERS=('django.contrib.staticfiles.finders.FileSystemFinder',),
    )
    def test_post_processing_failure(self):
        """
        Test that post_processing indicates the origin of the error when it
        fails. Regression test for #18986.
        """
        finders.get_finder.cache_clear()
        err = six.StringIO()
        with self.assertRaises(Exception):
            call_command('collectstatic', interactive=False, verbosity=0, stderr=err)
        self.assertEqual("Post-processing 'faulty.css' failed!\n\n", err.getvalue())


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

        self._clear_filename = os.path.join(TESTFILES_PATH, 'cleared.txt')
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


@override_settings(ROOT_URLCONF='staticfiles_tests.urls.default')
class TestServeStatic(StaticFilesTestCase):
    """
    Test static asset serving view.
    """

    def _response(self, filepath):
        return self.client.get(
            posixpath.join(settings.STATIC_URL, filepath))

    def assertFileContains(self, filepath, text):
        self.assertContains(self._response(filepath), text)

    def assertFileNotFound(self, filepath):
        self.assertEqual(self._response(filepath).status_code, 404)


@override_settings(DEBUG=False)
class TestServeDisabled(TestServeStatic):
    """
    Test serving static files disabled when DEBUG is False.
    """
    def test_disabled_serving(self):
        self.assertFileNotFound('test.txt')


class TestServeStaticWithDefaultURL(TestServeStatic, TestDefaults):
    """
    Test static asset serving view with manually configured URLconf.
    """
    pass


@override_settings(ROOT_URLCONF='staticfiles_tests.urls.helper')
class TestServeStaticWithURLHelper(TestServeStatic, TestDefaults):
    """
    Test static asset serving view with staticfiles_urlpatterns helper.
    """


class FinderTestCase(object):
    """
    Base finder test mixin.

    On Windows, sometimes the case of the path we ask the finders for and the
    path(s) they find can differ. Compare them using os.path.normcase() to
    avoid false negatives.
    """
    def test_find_first(self):
        src, dst = self.find_first
        found = self.finder.find(src)
        self.assertEqual(os.path.normcase(found), os.path.normcase(dst))

    def test_find_all(self):
        src, dst = self.find_all
        found = self.finder.find(src, all=True)
        found = [os.path.normcase(f) for f in found]
        dst = [os.path.normcase(d) for d in dst]
        self.assertEqual(found, dst)


class TestFileSystemFinder(StaticFilesTestCase, FinderTestCase):
    """
    Test FileSystemFinder.
    """
    def setUp(self):
        super(TestFileSystemFinder, self).setUp()
        self.finder = finders.FileSystemFinder()
        test_file_path = os.path.join(TEST_ROOT, 'project', 'documents', 'test', 'file.txt')
        self.find_first = (os.path.join('test', 'file.txt'), test_file_path)
        self.find_all = (os.path.join('test', 'file.txt'), [test_file_path])


class TestAppDirectoriesFinder(StaticFilesTestCase, FinderTestCase):
    """
    Test AppDirectoriesFinder.
    """
    def setUp(self):
        super(TestAppDirectoriesFinder, self).setUp()
        self.finder = finders.AppDirectoriesFinder()
        test_file_path = os.path.join(TEST_ROOT, 'apps', 'test', 'static', 'test', 'file1.txt')
        self.find_first = (os.path.join('test', 'file1.txt'), test_file_path)
        self.find_all = (os.path.join('test', 'file1.txt'), [test_file_path])


class TestDefaultStorageFinder(StaticFilesTestCase, FinderTestCase):
    """
    Test DefaultStorageFinder.
    """
    def setUp(self):
        super(TestDefaultStorageFinder, self).setUp()
        self.finder = finders.DefaultStorageFinder(
            storage=storage.StaticFilesStorage(location=settings.MEDIA_ROOT))
        test_file_path = os.path.join(settings.MEDIA_ROOT, 'media-file.txt')
        self.find_first = ('media-file.txt', test_file_path)
        self.find_all = ('media-file.txt', [test_file_path])


@override_settings(
    STATICFILES_FINDERS=('django.contrib.staticfiles.finders.FileSystemFinder',),
    STATICFILES_DIRS=[os.path.join(TEST_ROOT, 'project', 'documents')],
)
class TestMiscFinder(TestCase):
    """
    A few misc finder tests.
    """
    def test_get_finder(self):
        self.assertIsInstance(finders.get_finder(
            'django.contrib.staticfiles.finders.FileSystemFinder'),
            finders.FileSystemFinder)

    def test_get_finder_bad_classname(self):
        self.assertRaises(ImportError, finders.get_finder,
                          'django.contrib.staticfiles.finders.FooBarFinder')

    def test_get_finder_bad_module(self):
        self.assertRaises(ImportError,
            finders.get_finder, 'foo.bar.FooBarFinder')

    def test_cache(self):
        finders.get_finder.cache_clear()
        for n in range(10):
            finders.get_finder(
                'django.contrib.staticfiles.finders.FileSystemFinder')
        cache_info = finders.get_finder.cache_info()
        self.assertEqual(cache_info.hits, 9)
        self.assertEqual(cache_info.currsize, 1)

    def test_searched_locations(self):
        finders.find('spam')
        self.assertEqual(finders.searched_locations,
                         [os.path.join(TEST_ROOT, 'project', 'documents')])

    @override_settings(STATICFILES_DIRS='a string')
    def test_non_tuple_raises_exception(self):
        """
        We can't determine if STATICFILES_DIRS is set correctly just by
        looking at the type, but we can determine if it's definitely wrong.
        """
        self.assertRaises(ImproperlyConfigured, finders.FileSystemFinder)

    @override_settings(MEDIA_ROOT='')
    def test_location_empty(self):
        self.assertRaises(ImproperlyConfigured, finders.DefaultStorageFinder)


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
