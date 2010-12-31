import os
import posixpath
import shutil
import sys
import tempfile
from StringIO import StringIO

from django.conf import settings
from django.contrib.staticfiles import finders, storage
from django.core.exceptions import ImproperlyConfigured
from django.core.files.storage import default_storage
from django.core.management import call_command
from django.db.models.loading import load_app
from django.template import Template, Context
from django.test import TestCase
from django.utils._os import rmtree_errorhandler


TEST_ROOT = os.path.normcase(os.path.dirname(__file__))


class StaticFilesTestCase(TestCase):
    """
    Test case with a couple utility assertions.
    """
    def setUp(self):
        self.old_static_url = settings.STATIC_URL
        self.old_static_root = settings.STATIC_ROOT
        self.old_staticfiles_dirs = settings.STATICFILES_DIRS
        self.old_staticfiles_finders = settings.STATICFILES_FINDERS
        self.old_media_root = settings.MEDIA_ROOT
        self.old_media_url = settings.MEDIA_URL
        self.old_admin_media_prefix = settings.ADMIN_MEDIA_PREFIX
        self.old_debug = settings.DEBUG
        self.old_installed_apps = settings.INSTALLED_APPS

        # We have to load these apps to test staticfiles.
        load_app('regressiontests.staticfiles_tests.apps.test')
        load_app('regressiontests.staticfiles_tests.apps.no_label')
        site_media = os.path.join(TEST_ROOT, 'project', 'site_media')
        settings.DEBUG = True
        settings.MEDIA_ROOT =  os.path.join(site_media, 'media')
        settings.MEDIA_URL = '/media/'
        settings.STATIC_ROOT = os.path.join(site_media, 'static')
        settings.STATIC_URL = '/static/'
        settings.ADMIN_MEDIA_PREFIX = '/static/admin/'
        settings.STATICFILES_DIRS = (
            os.path.join(TEST_ROOT, 'project', 'documents'),
        )
        settings.STATICFILES_FINDERS = (
            'django.contrib.staticfiles.finders.FileSystemFinder',
            'django.contrib.staticfiles.finders.AppDirectoriesFinder',
            'django.contrib.staticfiles.finders.DefaultStorageFinder',
        )
        settings.INSTALLED_APPS = [
            'django.contrib.staticfiles',
            'regressiontests.staticfiles_tests',
        ]

        # Clear the cached default_storage out, this is because when it first
        # gets accessed (by some other test), it evaluates settings.MEDIA_ROOT,
        # since we're planning on changing that we need to clear out the cache.
        default_storage._wrapped = None

    def tearDown(self):
        settings.DEBUG = self.old_debug
        settings.MEDIA_ROOT = self.old_media_root
        settings.MEDIA_URL = self.old_media_url
        settings.ADMIN_MEDIA_PREFIX = self.old_admin_media_prefix
        settings.STATIC_ROOT = self.old_static_root
        settings.STATIC_URL = self.old_static_url
        settings.STATICFILES_DIRS = self.old_staticfiles_dirs
        settings.STATICFILES_FINDERS = self.old_staticfiles_finders
        settings.INSTALLED_APPS = self.old_installed_apps

    def assertFileContains(self, filepath, text):
        self.assertTrue(text in self._get_file(filepath),
                        "'%s' not in '%s'" % (text, filepath))

    def assertFileNotFound(self, filepath):
        self.assertRaises(IOError, self._get_file, filepath)


class BuildStaticTestCase(StaticFilesTestCase):
    """
    Tests shared by all file-resolving features (collectstatic,
    findstatic, and static serve view).

    This relies on the asserts defined in UtilityAssertsTestCase, but
    is separated because some test cases need those asserts without
    all these tests.
    """
    def setUp(self):
        super(BuildStaticTestCase, self).setUp()
        self.old_staticfiles_storage = settings.STATICFILES_STORAGE
        self.old_root = settings.STATIC_ROOT
        settings.STATIC_ROOT = tempfile.mkdtemp()
        self.run_collectstatic()

    def tearDown(self):
        # Use our own error handler that can handle .svn dirs on Windows
        shutil.rmtree(settings.STATIC_ROOT, ignore_errors=True,
                      onerror=rmtree_errorhandler)
        settings.STATIC_ROOT = self.old_root
        super(BuildStaticTestCase, self).tearDown()

    def run_collectstatic(self, **kwargs):
        call_command('collectstatic', interactive=False, verbosity='0',
                     ignore_patterns=['*.ignoreme'], **kwargs)

    def _get_file(self, filepath):
        assert filepath, 'filepath is empty.'
        filepath = os.path.join(settings.STATIC_ROOT, filepath)
        f = open(filepath)
        try:
            return f.read()
        finally:
            f.close()


class TestDefaults(object):
    """
    A few standard test cases.
    """
    def test_staticfiles_dirs(self):
        """
        Can find a file in a STATICFILES_DIRS directory.
        """
        self.assertFileContains('test.txt', 'Can we find')

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
        Can find a file in an app media/ directory.
        """
        self.assertFileContains('test/file1.txt', 'file1 in the app dir')


class TestFindStatic(BuildStaticTestCase, TestDefaults):
    """
    Test ``findstatic`` management command.
    """
    def _get_file(self, filepath):
        _stdout = sys.stdout
        sys.stdout = StringIO()
        try:
            call_command('findstatic', filepath, all=False, verbosity='0')
            sys.stdout.seek(0)
            lines = [l.strip() for l in sys.stdout.readlines()]
            contents = open(lines[1].strip()).read()
        finally:
            sys.stdout = _stdout
        return contents

    def test_all_files(self):
        """
        Test that findstatic returns all candidate files if run without --first.
        """
        _stdout = sys.stdout
        sys.stdout = StringIO()
        try:
            call_command('findstatic', 'test/file.txt', verbosity='0')
            sys.stdout.seek(0)
            lines = [l.strip() for l in sys.stdout.readlines()]
        finally:
            sys.stdout = _stdout
        self.assertEquals(len(lines), 3) # three because there is also the "Found <file> here" line
        self.assertTrue('project' in lines[1])
        self.assertTrue('apps' in lines[2])


class TestBuildStatic(BuildStaticTestCase, TestDefaults):
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


class TestBuildStaticExcludeNoDefaultIgnore(BuildStaticTestCase, TestDefaults):
    """
    Test ``--exclude-dirs`` and ``--no-default-ignore`` options for
    ``collectstatic`` management command.
    """
    def run_collectstatic(self):
        super(TestBuildStaticExcludeNoDefaultIgnore, self).run_collectstatic(
            use_default_ignore_patterns=False)

    def test_no_common_ignore_patterns(self):
        """
        With --no-default-ignore, common ignore patterns (*~, .*, CVS)
        are not ignored.

        """
        self.assertFileContains('test/.hidden', 'should be ignored')
        self.assertFileContains('test/backup~', 'should be ignored')
        self.assertFileContains('test/CVS', 'should be ignored')


class TestBuildStaticDryRun(BuildStaticTestCase):
    """
    Test ``--dry-run`` option for ``collectstatic`` management command.
    """
    def run_collectstatic(self):
        super(TestBuildStaticDryRun, self).run_collectstatic(dry_run=True)

    def test_no_files_created(self):
        """
        With --dry-run, no files created in destination dir.
        """
        self.assertEquals(os.listdir(settings.STATIC_ROOT), [])


if sys.platform != 'win32':
    class TestBuildStaticLinks(BuildStaticTestCase, TestDefaults):
        """
        Test ``--link`` option for ``collectstatic`` management command.

        Note that by inheriting ``TestDefaults`` we repeat all
        the standard file resolving tests here, to make sure using
        ``--link`` does not change the file-selection semantics.
        """
        def run_collectstatic(self):
            super(TestBuildStaticLinks, self).run_collectstatic(link=True)

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
        self.assertEquals(self._response(filepath).status_code, 404)


class TestServeDisabled(TestServeStatic):
    """
    Test serving media from django.contrib.admin.
    """
    def setUp(self):
        super(TestServeDisabled, self).setUp()
        settings.DEBUG = False

    def test_disabled_serving(self):
        self.assertRaisesRegexp(ImproperlyConfigured, 'The view to serve '
            'static files can only be used if the DEBUG setting is True',
            self._response, 'test.txt')


class TestServeStaticWithDefaultURL(TestServeStatic, TestDefaults):
    """
    Test static asset serving view with staticfiles_urlpatterns helper.
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
            posixpath.join(settings.ADMIN_MEDIA_PREFIX, filepath))

    def test_serve_admin_media(self):
        self.assertFileContains('css/base.css', 'body')


class FinderTestCase(object):
    """
    Base finder test mixin
    """
    def test_find_first(self):
        src, dst = self.find_first
        self.assertEquals(self.finder.find(src), dst)

    def test_find_all(self):
        src, dst = self.find_all
        self.assertEquals(self.finder.find(src, all=True), dst)


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
        self.assertTrue(isinstance(finders.get_finder(
            'django.contrib.staticfiles.finders.FileSystemFinder'),
            finders.FileSystemFinder))
        self.assertRaises(ImproperlyConfigured,
            finders.get_finder, 'django.contrib.staticfiles.finders.FooBarFinder')
        self.assertRaises(ImproperlyConfigured,
            finders.get_finder, 'foo.bar.FooBarFinder')
