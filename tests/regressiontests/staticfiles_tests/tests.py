# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

import codecs
import os
import posixpath
import shutil
import sys
import tempfile

from django.template import loader, Context
from django.conf import settings
from django.core.cache.backends.base import BaseCache
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.test import TestCase
from django.test.utils import override_settings
from django.utils.encoding import force_text
from django.utils.functional import empty
from django.utils._os import rmtree_errorhandler, upath
from django.utils import six

from django.contrib.staticfiles import finders, storage

TEST_ROOT = os.path.dirname(upath(__file__))
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
}
from django.contrib.staticfiles.management.commands.collectstatic import Command as CollectstaticCommand


class BaseStaticFilesTestCase(object):
    """
    Test case with a couple utility assertions.
    """
    def setUp(self):
        # Clear the cached staticfiles_storage out, this is because when it first
        # gets accessed (by some other test), it evaluates settings.STATIC_ROOT,
        # since we're planning on changing that we need to clear out the cache.
        storage.staticfiles_storage._wrapped = empty
        # Clear the cached staticfile finders, so they are reinitialized every
        # run and pick up changes in settings.STATICFILES_DIRS.
        finders._finders.clear()

        testfiles_path = os.path.join(TEST_ROOT, 'apps', 'test', 'static', 'test')
        # To make sure SVN doesn't hangs itself with the non-ASCII characters
        # during checkout, we actually create one file dynamically.
        self._nonascii_filepath = os.path.join(testfiles_path, '\u2297.txt')
        with codecs.open(self._nonascii_filepath, 'w', 'utf-8') as f:
            f.write("\u2297 in the app dir")
        # And also create the stupid hidden file to dwarf the setup.py's
        # package data handling.
        self._hidden_filepath = os.path.join(testfiles_path, '.hidden')
        with codecs.open(self._hidden_filepath, 'w', 'utf-8') as f:
            f.write("should be ignored")
        self._backup_filepath = os.path.join(
            TEST_ROOT, 'project', 'documents', 'test', 'backup~')
        with codecs.open(self._backup_filepath, 'w', 'utf-8') as f:
            f.write("should be ignored")

    def tearDown(self):
        os.unlink(self._nonascii_filepath)
        os.unlink(self._hidden_filepath)
        os.unlink(self._backup_filepath)

    def assertFileContains(self, filepath, text):
        self.assertIn(text, self._get_file(force_text(filepath)),
                        "'%s' not in '%s'" % (text, filepath))

    def assertFileNotFound(self, filepath):
        self.assertRaises(IOError, self._get_file, filepath)

    def render_template(self, template, **kwargs):
        if isinstance(template, six.string_types):
            template = loader.get_template_from_string(template)
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
        self.old_root = settings.STATIC_ROOT
        settings.STATIC_ROOT = tempfile.mkdtemp(dir=os.environ['DJANGO_TEST_TEMP_DIR'])
        self.run_collectstatic()
        # Use our own error handler that can handle .svn dirs on Windows
        self.addCleanup(shutil.rmtree, settings.STATIC_ROOT,
                        ignore_errors=True, onerror=rmtree_errorhandler)

    def tearDown(self):
        settings.STATIC_ROOT = self.old_root
        super(BaseCollectionTestCase, self).tearDown()

    def run_collectstatic(self, **kwargs):
        call_command('collectstatic', interactive=False, verbosity='0',
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
        with codecs.open(force_text(lines[1].strip()), "r", "utf-8") as f:
            return f.read()

    def test_all_files(self):
        """
        Test that findstatic returns all candidate files if run without --first.
        """
        out = six.StringIO()
        call_command('findstatic', 'test/file.txt', verbosity=0, stdout=out)
        out.seek(0)
        lines = [l.strip() for l in out.readlines()]
        self.assertEqual(len(lines), 3)  # three because there is also the "Found <file> here" line
        self.assertIn('project', force_text(lines[1]))
        self.assertIn('apps', force_text(lines[2]))


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
    Test the ``--clear`` option of the ``collectstatic`` managemenet command.
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
    Check for proper handling of apps order in INSTALLED_APPS even if file modification
    dates are in different order:

        'regressiontests.staticfiles_tests.apps.test',
        'regressiontests.staticfiles_tests.apps.no_label',

    """
    def setUp(self):
        self.orig_path = os.path.join(TEST_ROOT, 'apps', 'no_label', 'static', 'file2.txt')
        # get modification and access times for no_label/static/file2.txt
        self.orig_mtime = os.path.getmtime(self.orig_path)
        self.orig_atime = os.path.getatime(self.orig_path)

        # prepare duplicate of file2.txt from no_label app
        # this file will have modification time older than no_label/static/file2.txt
        # anyway it should be taken to STATIC_ROOT because 'test' app is before
        # 'no_label' app in INSTALLED_APPS
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
        # test app is first in INSTALLED_APPS so file2.txt should remain unmodified
        mtime = os.path.getmtime(self.testfile_path)
        atime = os.path.getatime(self.testfile_path)
        os.utime(self.orig_path, (mtime + 1, atime + 1))

        # run collectstatic again
        self.run_collectstatic()

        self.assertFileContains('file2.txt', 'duplicate of file2.txt')


@override_settings(
    STATICFILES_STORAGE='regressiontests.staticfiles_tests.storage.DummyStorage',
)
class TestCollectionNonLocalStorage(CollectionTestCase, TestNoFilesCreated):
    """
    Tests for #15035
    """
    pass


# we set DEBUG to False here since the template tag wouldn't work otherwise
@override_settings(**dict(TEST_SETTINGS,
    STATICFILES_STORAGE='django.contrib.staticfiles.storage.CachedStaticFilesStorage',
    DEBUG=False,
))
class TestCollectionCachedStorage(BaseCollectionTestCase,
        BaseStaticFilesTestCase, TestCase):
    """
    Tests for the Cache busting storage
    """
    def cached_file_path(self, path):
        fullpath = self.render_template(self.static_template_snippet(path))
        return fullpath.replace(settings.STATIC_URL, '')

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
                                 "/static/cached/styles.93b1147e8552.css")
        self.assertStaticRenders("path/",
                                 "/static/path/")
        self.assertStaticRenders("path/?query",
                                 "/static/path/?query")

    def test_template_tag_simple_content(self):
        relpath = self.cached_file_path("cached/styles.css")
        self.assertEqual(relpath, "cached/styles.93b1147e8552.css")
        with storage.staticfiles_storage.open(relpath) as relfile:
            content = relfile.read()
            self.assertNotIn(b"cached/other.css", content)
            self.assertIn(b"other.d41d8cd98f00.css", content)

    def test_path_ignored_completely(self):
        relpath = self.cached_file_path("cached/css/ignored.css")
        self.assertEqual(relpath, "cached/css/ignored.6c77f2643390.css")
        with storage.staticfiles_storage.open(relpath) as relfile:
            content = relfile.read()
            self.assertIn(b'#foobar', content)
            self.assertIn(b'http:foobar', content)
            self.assertIn(b'https:foobar', content)
            self.assertIn(b'data:foobar', content)
            self.assertIn(b'//foobar', content)

    def test_path_with_querystring(self):
        relpath = self.cached_file_path("cached/styles.css?spam=eggs")
        self.assertEqual(relpath,
                         "cached/styles.93b1147e8552.css?spam=eggs")
        with storage.staticfiles_storage.open(
                "cached/styles.93b1147e8552.css") as relfile:
            content = relfile.read()
            self.assertNotIn(b"cached/other.css", content)
            self.assertIn(b"other.d41d8cd98f00.css", content)

    def test_path_with_fragment(self):
        relpath = self.cached_file_path("cached/styles.css#eggs")
        self.assertEqual(relpath, "cached/styles.93b1147e8552.css#eggs")
        with storage.staticfiles_storage.open(
                "cached/styles.93b1147e8552.css") as relfile:
            content = relfile.read()
            self.assertNotIn(b"cached/other.css", content)
            self.assertIn(b"other.d41d8cd98f00.css", content)

    def test_path_with_querystring_and_fragment(self):
        relpath = self.cached_file_path("cached/css/fragments.css")
        self.assertEqual(relpath, "cached/css/fragments.75433540b096.css")
        with storage.staticfiles_storage.open(relpath) as relfile:
            content = relfile.read()
            self.assertIn(b'fonts/font.a4b0478549d0.eot?#iefix', content)
            self.assertIn(b'fonts/font.b8d603e42714.svg#webfontIyfZbseF', content)
            self.assertIn(b'data:font/woff;charset=utf-8;base64,d09GRgABAAAAADJoAA0AAAAAR2QAAQAAAAAAAAAAAAA', content)
            self.assertIn(b'#default#VML', content)

    def test_template_tag_absolute(self):
        relpath = self.cached_file_path("cached/absolute.css")
        self.assertEqual(relpath, "cached/absolute.23f087ad823a.css")
        with storage.staticfiles_storage.open(relpath) as relfile:
            content = relfile.read()
            self.assertNotIn(b"/static/cached/styles.css", content)
            self.assertIn(b"/static/cached/styles.93b1147e8552.css", content)
            self.assertIn(b'/static/cached/img/relative.acae32e4532b.png', content)

    def test_template_tag_denorm(self):
        relpath = self.cached_file_path("cached/denorm.css")
        self.assertEqual(relpath, "cached/denorm.c5bd139ad821.css")
        with storage.staticfiles_storage.open(relpath) as relfile:
            content = relfile.read()
            self.assertNotIn(b"..//cached///styles.css", content)
            self.assertIn(b"../cached/styles.93b1147e8552.css", content)
            self.assertNotIn(b"url(img/relative.png )", content)
            self.assertIn(b'url("img/relative.acae32e4532b.png', content)

    def test_template_tag_relative(self):
        relpath = self.cached_file_path("cached/relative.css")
        self.assertEqual(relpath, "cached/relative.2217ea7273c2.css")
        with storage.staticfiles_storage.open(relpath) as relfile:
            content = relfile.read()
            self.assertNotIn(b"../cached/styles.css", content)
            self.assertNotIn(b'@import "styles.css"', content)
            self.assertNotIn(b'url(img/relative.png)', content)
            self.assertIn(b'url("img/relative.acae32e4532b.png")', content)
            self.assertIn(b"../cached/styles.93b1147e8552.css", content)

    def test_import_replacement(self):
        "See #18050"
        relpath = self.cached_file_path("cached/import.css")
        self.assertEqual(relpath, "cached/import.2b1d40b0bbd4.css")
        with storage.staticfiles_storage.open(relpath) as relfile:
            self.assertIn(b"""import url("styles.93b1147e8552.css")""", relfile.read())

    def test_template_tag_deep_relative(self):
        relpath = self.cached_file_path("cached/css/window.css")
        self.assertEqual(relpath, "cached/css/window.9db38d5169f3.css")
        with storage.staticfiles_storage.open(relpath) as relfile:
            content = relfile.read()
            self.assertNotIn(b'url(img/window.png)', content)
            self.assertIn(b'url("img/window.acae32e4532b.png")', content)

    def test_template_tag_url(self):
        relpath = self.cached_file_path("cached/url.css")
        self.assertEqual(relpath, "cached/url.615e21601e4b.css")
        with storage.staticfiles_storage.open(relpath) as relfile:
            self.assertIn(b"https://", relfile.read())

    def test_cache_invalidation(self):
        name = "cached/styles.css"
        hashed_name = "cached/styles.93b1147e8552.css"
        # check if the cache is filled correctly as expected
        cache_key = storage.staticfiles_storage.cache_key(name)
        cached_name = storage.staticfiles_storage.cache.get(cache_key)
        self.assertEqual(self.cached_file_path(name), cached_name)
        # clearing the cache to make sure we re-set it correctly in the url method
        storage.staticfiles_storage.cache.clear()
        cached_name = storage.staticfiles_storage.cache.get(cache_key)
        self.assertEqual(cached_name, None)
        self.assertEqual(self.cached_file_path(name), hashed_name)
        cached_name = storage.staticfiles_storage.cache.get(cache_key)
        self.assertEqual(cached_name, hashed_name)

    def test_post_processing(self):
        """Test that post_processing behaves correctly.

        Files that are alterable should always be post-processed; files that
        aren't should be skipped.

        collectstatic has already been called once in setUp() for this testcase,
        therefore we check by verifying behavior on a second run.
        """
        collectstatic_args = {
            'interactive': False,
            'verbosity': '0',
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

    def test_cache_key_memcache_validation(self):
        """
        Handle cache key creation correctly, see #17861.
        """
        name = "/some crazy/long filename/ with spaces Here and ?#%#$/other/stuff/some crazy/long filename/ with spaces Here and ?#%#$/other/stuff/some crazy/long filename/ with spaces Here and ?#%#$/other/stuff/some crazy/long filename/ with spaces Here and ?#%#$/other/stuff/some crazy/long filename/ with spaces Here and ?#%#$/other/stuff/some crazy/" + "\x16" + "\xb4"
        cache_key = storage.staticfiles_storage.cache_key(name)
        cache_validator = BaseCache({})
        cache_validator.validate_key(cache_key)
        self.assertEqual(cache_key, 'staticfiles:821ea71ef36f95b3922a77f7364670e7')


# we set DEBUG to False here since the template tag wouldn't work otherwise
@override_settings(**dict(TEST_SETTINGS,
    STATICFILES_STORAGE='regressiontests.staticfiles_tests.storage.SimpleCachedStaticFilesStorage',
    DEBUG=False,
))
class TestCollectionSimpleCachedStorage(BaseCollectionTestCase,
        BaseStaticFilesTestCase, TestCase):
    """
    Tests for the Cache busting storage
    """
    def cached_file_path(self, path):
        fullpath = self.render_template(self.static_template_snippet(path))
        return fullpath.replace(settings.STATIC_URL, '')

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
        relpath = self.cached_file_path("cached/styles.css")
        self.assertEqual(relpath, "cached/styles.deploy12345.css")
        with storage.staticfiles_storage.open(relpath) as relfile:
            content = relfile.read()
            self.assertNotIn(b"cached/other.css", content)
            self.assertIn(b"other.deploy12345.css", content)

if sys.platform != 'win32':

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


class TestServeStatic(StaticFilesTestCase):
    """
    Test static asset serving view.
    """
    urls = 'regressiontests.staticfiles_tests.urls.default'

    def _response(self, filepath):
        return self.client.get(
            posixpath.join(settings.STATIC_URL, filepath))

    def assertFileContains(self, filepath, text):
        self.assertContains(self._response(filepath), text)

    def assertFileNotFound(self, filepath):
        self.assertEqual(self._response(filepath).status_code, 404)


class TestServeDisabled(TestServeStatic):
    """
    Test serving static files disabled when DEBUG is False.
    """
    def setUp(self):
        super(TestServeDisabled, self).setUp()
        settings.DEBUG = False

    def test_disabled_serving(self):
        six.assertRaisesRegex(self, ImproperlyConfigured, 'The staticfiles view '
            'can only be used in debug mode ', self._response, 'test.txt')


class TestServeStaticWithDefaultURL(TestServeStatic, TestDefaults):
    """
    Test static asset serving view with manually configured URLconf.
    """
    pass


class TestServeStaticWithURLHelper(TestServeStatic, TestDefaults):
    """
    Test static asset serving view with staticfiles_urlpatterns helper.
    """
    urls = 'regressiontests.staticfiles_tests.urls.helper'


class TestServeAdminMedia(TestServeStatic):
    """
    Test serving media from django.contrib.admin.
    """
    def _response(self, filepath):
        return self.client.get(
            posixpath.join(settings.STATIC_URL, 'admin/', filepath))

    def test_serve_admin_media(self):
        self.assertFileContains('css/base.css', 'body')


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


class TestMiscFinder(TestCase):
    """
    A few misc finder tests.
    """
    def test_get_finder(self):
        self.assertIsInstance(finders.get_finder(
            'django.contrib.staticfiles.finders.FileSystemFinder'),
            finders.FileSystemFinder)

    def test_get_finder_bad_classname(self):
        self.assertRaises(ImproperlyConfigured, finders.get_finder,
                          'django.contrib.staticfiles.finders.FooBarFinder')

    def test_get_finder_bad_module(self):
        self.assertRaises(ImproperlyConfigured,
            finders.get_finder, 'foo.bar.FooBarFinder')

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
        self.assertStaticRenders("does/not/exist.png",
                                   "/static/does/not/exist.png")
        self.assertStaticRenders("testfile.txt", "/static/testfile.txt")
