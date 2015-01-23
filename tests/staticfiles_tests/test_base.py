# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

import codecs
import os
import shutil
import tempfile

from django.template import Context, Template
from django.conf import settings
from django.core.management import call_command
from django.test import TestCase, override_settings
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
    'INSTALLED_APPS': (
        'django.contrib.contenttypes',
        'django.contrib.auth',
        'django.contrib.admin.apps.SimpleAdminConfig',
        'django.contrib.staticfiles',
        'staticfiles_tests',
        'staticfiles_tests.apps.test',
        'staticfiles_tests.apps.no_label',
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
        finders.get_finder.cache_clear()

        self.testfiles_path = os.path.join(TEST_ROOT, 'apps', 'test', 'static', 'test')
        # To make sure SVN doesn't hangs itself with the non-ASCII characters
        # during checkout, we actually create one file dynamically.
        self._nonascii_filepath = os.path.join(self.testfiles_path, '\u2297.txt')
        with codecs.open(self._nonascii_filepath, 'w', 'utf-8') as f:
            f.write("\u2297 in the app dir")
        # And also create the magic hidden file to trick the setup.py's
        # package data handling.
        self._hidden_filepath = os.path.join(self.testfiles_path, '.hidden')
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
