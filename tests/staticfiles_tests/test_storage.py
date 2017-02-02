import os
import shutil
import sys
import tempfile
import unittest
from io import StringIO

from django.conf import settings
from django.contrib.staticfiles import finders, storage
from django.contrib.staticfiles.management.commands.collectstatic import \
    Command as CollectstaticCommand
from django.core.cache.backends.base import BaseCache
from django.core.management import call_command
from django.test import override_settings

from .cases import CollectionTestCase
from .settings import TEST_ROOT


def hashed_file_path(test, path):
    fullpath = test.render_template(test.static_template_snippet(path))
    return fullpath.replace(settings.STATIC_URL, '')


class TestHashedFiles:
    hashed_file_path = hashed_file_path

    def setUp(self):
        self._max_post_process_passes = storage.staticfiles_storage.max_post_process_passes
        super().setUp()

    def tearDown(self):
        # Clear hashed files to avoid side effects among tests.
        storage.staticfiles_storage.hashed_files.clear()
        storage.staticfiles_storage.max_post_process_passes = self._max_post_process_passes

    def assertPostCondition(self):
        """
        Assert post conditions for a test are met. Must be manually called at
        the end of each test.
        """
        pass

    def test_template_tag_return(self):
        """
        Test the CachedStaticFilesStorage backend.
        """
        self.assertStaticRaises(ValueError, "does/not/exist.png", "/static/does/not/exist.png")
        self.assertStaticRenders("test/file.txt", "/static/test/file.dad0999e4f8f.txt")
        self.assertStaticRenders("test/file.txt", "/static/test/file.dad0999e4f8f.txt", asvar=True)
        self.assertStaticRenders("cached/styles.css", "/static/cached/styles.5e0040571e1a.css")
        self.assertStaticRenders("path/", "/static/path/")
        self.assertStaticRenders("path/?query", "/static/path/?query")
        self.assertPostCondition()

    def test_template_tag_simple_content(self):
        relpath = self.hashed_file_path("cached/styles.css")
        self.assertEqual(relpath, "cached/styles.5e0040571e1a.css")
        with storage.staticfiles_storage.open(relpath) as relfile:
            content = relfile.read()
            self.assertNotIn(b"cached/other.css", content)
            self.assertIn(b"other.d41d8cd98f00.css", content)
        self.assertPostCondition()

    def test_path_ignored_completely(self):
        relpath = self.hashed_file_path("cached/css/ignored.css")
        self.assertEqual(relpath, "cached/css/ignored.554da52152af.css")
        with storage.staticfiles_storage.open(relpath) as relfile:
            content = relfile.read()
            self.assertIn(b'#foobar', content)
            self.assertIn(b'http:foobar', content)
            self.assertIn(b'https:foobar', content)
            self.assertIn(b'data:foobar', content)
            self.assertIn(b'chrome:foobar', content)
            self.assertIn(b'//foobar', content)
        self.assertPostCondition()

    def test_path_with_querystring(self):
        relpath = self.hashed_file_path("cached/styles.css?spam=eggs")
        self.assertEqual(relpath, "cached/styles.5e0040571e1a.css?spam=eggs")
        with storage.staticfiles_storage.open("cached/styles.5e0040571e1a.css") as relfile:
            content = relfile.read()
            self.assertNotIn(b"cached/other.css", content)
            self.assertIn(b"other.d41d8cd98f00.css", content)
        self.assertPostCondition()

    def test_path_with_fragment(self):
        relpath = self.hashed_file_path("cached/styles.css#eggs")
        self.assertEqual(relpath, "cached/styles.5e0040571e1a.css#eggs")
        with storage.staticfiles_storage.open("cached/styles.5e0040571e1a.css") as relfile:
            content = relfile.read()
            self.assertNotIn(b"cached/other.css", content)
            self.assertIn(b"other.d41d8cd98f00.css", content)
        self.assertPostCondition()

    def test_path_with_querystring_and_fragment(self):
        relpath = self.hashed_file_path("cached/css/fragments.css")
        self.assertEqual(relpath, "cached/css/fragments.c4e6753b52d3.css")
        with storage.staticfiles_storage.open(relpath) as relfile:
            content = relfile.read()
            self.assertIn(b'fonts/font.a4b0478549d0.eot?#iefix', content)
            self.assertIn(b'fonts/font.b8d603e42714.svg#webfontIyfZbseF', content)
            self.assertIn(b'fonts/font.b8d603e42714.svg#path/to/../../fonts/font.svg', content)
            self.assertIn(b'data:font/woff;charset=utf-8;base64,d09GRgABAAAAADJoAA0AAAAAR2QAAQAAAAAAAAAAAAA', content)
            self.assertIn(b'#default#VML', content)
        self.assertPostCondition()

    def test_template_tag_absolute(self):
        relpath = self.hashed_file_path("cached/absolute.css")
        self.assertEqual(relpath, "cached/absolute.eb04def9f9a4.css")
        with storage.staticfiles_storage.open(relpath) as relfile:
            content = relfile.read()
            self.assertNotIn(b"/static/cached/styles.css", content)
            self.assertIn(b"/static/cached/styles.5e0040571e1a.css", content)
            self.assertNotIn(b"/static/styles_root.css", content)
            self.assertIn(b"/static/styles_root.401f2509a628.css", content)
            self.assertIn(b'/static/cached/img/relative.acae32e4532b.png', content)
        self.assertPostCondition()

    def test_template_tag_absolute_root(self):
        """
        Like test_template_tag_absolute, but for a file in STATIC_ROOT (#26249).
        """
        relpath = self.hashed_file_path("absolute_root.css")
        self.assertEqual(relpath, "absolute_root.f821df1b64f7.css")
        with storage.staticfiles_storage.open(relpath) as relfile:
            content = relfile.read()
            self.assertNotIn(b"/static/styles_root.css", content)
            self.assertIn(b"/static/styles_root.401f2509a628.css", content)
        self.assertPostCondition()

    def test_template_tag_relative(self):
        relpath = self.hashed_file_path("cached/relative.css")
        self.assertEqual(relpath, "cached/relative.c3e9e1ea6f2e.css")
        with storage.staticfiles_storage.open(relpath) as relfile:
            content = relfile.read()
            self.assertNotIn(b"../cached/styles.css", content)
            self.assertNotIn(b'@import "styles.css"', content)
            self.assertNotIn(b'url(img/relative.png)', content)
            self.assertIn(b'url("img/relative.acae32e4532b.png")', content)
            self.assertIn(b"../cached/styles.5e0040571e1a.css", content)
        self.assertPostCondition()

    def test_import_replacement(self):
        "See #18050"
        relpath = self.hashed_file_path("cached/import.css")
        self.assertEqual(relpath, "cached/import.f53576679e5a.css")
        with storage.staticfiles_storage.open(relpath) as relfile:
            self.assertIn(b"""import url("styles.5e0040571e1a.css")""", relfile.read())
        self.assertPostCondition()

    def test_template_tag_deep_relative(self):
        relpath = self.hashed_file_path("cached/css/window.css")
        self.assertEqual(relpath, "cached/css/window.5d5c10836967.css")
        with storage.staticfiles_storage.open(relpath) as relfile:
            content = relfile.read()
            self.assertNotIn(b'url(img/window.png)', content)
            self.assertIn(b'url("img/window.acae32e4532b.png")', content)
        self.assertPostCondition()

    def test_template_tag_url(self):
        relpath = self.hashed_file_path("cached/url.css")
        self.assertEqual(relpath, "cached/url.902310b73412.css")
        with storage.staticfiles_storage.open(relpath) as relfile:
            self.assertIn(b"https://", relfile.read())
        self.assertPostCondition()

    @override_settings(
        STATICFILES_DIRS=[os.path.join(TEST_ROOT, 'project', 'loop')],
        STATICFILES_FINDERS=['django.contrib.staticfiles.finders.FileSystemFinder'],
    )
    def test_import_loop(self):
        finders.get_finder.cache_clear()
        err = StringIO()
        with self.assertRaisesMessage(RuntimeError, 'Max post-process passes exceeded'):
            call_command('collectstatic', interactive=False, verbosity=0, stderr=err)
        self.assertEqual("Post-processing 'All' failed!\n\n", err.getvalue())
        self.assertPostCondition()

    def test_post_processing(self):
        """
        post_processing behaves correctly.

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
        self.assertPostCondition()

    def test_css_import_case_insensitive(self):
        relpath = self.hashed_file_path("cached/styles_insensitive.css")
        self.assertEqual(relpath, "cached/styles_insensitive.3fa427592a53.css")
        with storage.staticfiles_storage.open(relpath) as relfile:
            content = relfile.read()
            self.assertNotIn(b"cached/other.css", content)
            self.assertIn(b"other.d41d8cd98f00.css", content)
        self.assertPostCondition()

    @override_settings(
        STATICFILES_DIRS=[os.path.join(TEST_ROOT, 'project', 'faulty')],
        STATICFILES_FINDERS=['django.contrib.staticfiles.finders.FileSystemFinder'],
    )
    def test_post_processing_failure(self):
        """
        post_processing indicates the origin of the error when it fails.
        """
        finders.get_finder.cache_clear()
        err = StringIO()
        with self.assertRaises(Exception):
            call_command('collectstatic', interactive=False, verbosity=0, stderr=err)
        self.assertEqual("Post-processing 'faulty.css' failed!\n\n", err.getvalue())
        self.assertPostCondition()


@override_settings(
    STATICFILES_STORAGE='django.contrib.staticfiles.storage.CachedStaticFilesStorage',
)
class TestCollectionCachedStorage(TestHashedFiles, CollectionTestCase):
    """
    Tests for the Cache busting storage
    """
    def test_cache_invalidation(self):
        name = "cached/styles.css"
        hashed_name = "cached/styles.5e0040571e1a.css"
        # check if the cache is filled correctly as expected
        cache_key = storage.staticfiles_storage.hash_key(name)
        cached_name = storage.staticfiles_storage.hashed_files.get(cache_key)
        self.assertEqual(self.hashed_file_path(name), cached_name)
        # clearing the cache to make sure we re-set it correctly in the url method
        storage.staticfiles_storage.hashed_files.clear()
        cached_name = storage.staticfiles_storage.hashed_files.get(cache_key)
        self.assertIsNone(cached_name)
        self.assertEqual(self.hashed_file_path(name), hashed_name)
        cached_name = storage.staticfiles_storage.hashed_files.get(cache_key)
        self.assertEqual(cached_name, hashed_name)

        # Check files that had to be hashed multiple times since their content
        # includes other files that were hashed.
        name = 'cached/relative.css'
        hashed_name = 'cached/relative.c3e9e1ea6f2e.css'
        cache_key = storage.staticfiles_storage.hash_key(name)
        cached_name = storage.staticfiles_storage.hashed_files.get(cache_key)
        self.assertIsNone(cached_name)
        self.assertEqual(self.hashed_file_path(name), hashed_name)
        cached_name = storage.staticfiles_storage.hashed_files.get(cache_key)
        self.assertEqual(cached_name, hashed_name)

    def test_cache_key_memcache_validation(self):
        """
        Handle cache key creation correctly, see #17861.
        """
        name = (
            "/some crazy/long filename/ with spaces Here and ?#%#$/other/stuff"
            "/some crazy/long filename/ with spaces Here and ?#%#$/other/stuff"
            "/some crazy/long filename/ with spaces Here and ?#%#$/other/stuff"
            "/some crazy/long filename/ with spaces Here and ?#%#$/other/stuff"
            "/some crazy/long filename/ with spaces Here and ?#%#$/other/stuff"
            "/some crazy/\x16\xb4"
        )
        cache_key = storage.staticfiles_storage.hash_key(name)
        cache_validator = BaseCache({})
        cache_validator.validate_key(cache_key)
        self.assertEqual(cache_key, 'staticfiles:821ea71ef36f95b3922a77f7364670e7')

    def test_corrupt_intermediate_files(self):
        configured_storage = storage.staticfiles_storage
        # Clear cache to force rehashing of the files
        configured_storage.hashed_files.clear()
        # Simulate a corrupt chain of intermediate files by ensuring they don't
        # resolve before the max post-process count, which would normally be
        # high enough.
        configured_storage.max_post_process_passes = 1
        # File without intermediates that can be rehashed without a problem.
        self.hashed_file_path('cached/css/img/window.png')
        # File with too many intermediates to rehash with the low max
        # post-process passes.
        err_msg = "The name 'cached/styles.css' could not be hashed with %r." % (configured_storage._wrapped,)
        with self.assertRaisesMessage(ValueError, err_msg):
            self.hashed_file_path('cached/styles.css')


@override_settings(
    STATICFILES_STORAGE='staticfiles_tests.storage.ExtraPatternsCachedStaticFilesStorage',
)
class TestExtraPatternsCachedStorage(CollectionTestCase):

    def setUp(self):
        storage.staticfiles_storage.hashed_files.clear()  # avoid cache interference
        super().setUp()

    def cached_file_path(self, path):
        fullpath = self.render_template(self.static_template_snippet(path))
        return fullpath.replace(settings.STATIC_URL, '')

    def test_multi_extension_patterns(self):
        """
        With storage classes having several file extension patterns, only the
        files matching a specific file pattern should be affected by the
        substitution (#19670).
        """
        # CSS files shouldn't be touched by JS patterns.
        relpath = self.cached_file_path("cached/import.css")
        self.assertEqual(relpath, "cached/import.f53576679e5a.css")
        with storage.staticfiles_storage.open(relpath) as relfile:
            self.assertIn(b'import url("styles.5e0040571e1a.css")', relfile.read())

        # Confirm JS patterns have been applied to JS files.
        relpath = self.cached_file_path("cached/test.js")
        self.assertEqual(relpath, "cached/test.388d7a790d46.js")
        with storage.staticfiles_storage.open(relpath) as relfile:
            self.assertIn(b'JS_URL("import.f53576679e5a.css")', relfile.read())


@override_settings(
    STATICFILES_STORAGE='django.contrib.staticfiles.storage.ManifestStaticFilesStorage',
)
class TestCollectionManifestStorage(TestHashedFiles, CollectionTestCase):
    """
    Tests for the Cache busting storage
    """
    def setUp(self):
        super().setUp()

        temp_dir = tempfile.mkdtemp()
        os.makedirs(os.path.join(temp_dir, 'test'))
        self._clear_filename = os.path.join(temp_dir, 'test', 'cleared.txt')
        with open(self._clear_filename, 'w') as f:
            f.write('to be deleted in one test')

        self.patched_settings = self.settings(
            STATICFILES_DIRS=settings.STATICFILES_DIRS + [temp_dir])
        self.patched_settings.enable()
        self.addCleanup(shutil.rmtree, temp_dir)
        self._manifest_strict = storage.staticfiles_storage.manifest_strict

    def tearDown(self):
        self.patched_settings.disable()

        if os.path.exists(self._clear_filename):
            os.unlink(self._clear_filename)

        storage.staticfiles_storage.manifest_strict = self._manifest_strict
        super().tearDown()

    def assertPostCondition(self):
        hashed_files = storage.staticfiles_storage.hashed_files
        # The in-memory version of the manifest matches the one on disk
        # since a properly created manifest should cover all filenames.
        if hashed_files:
            manifest = storage.staticfiles_storage.load_manifest()
            self.assertEqual(hashed_files, manifest)

    def test_manifest_exists(self):
        filename = storage.staticfiles_storage.manifest_name
        path = storage.staticfiles_storage.path(filename)
        self.assertTrue(os.path.exists(path))

    def test_loaded_cache(self):
        self.assertNotEqual(storage.staticfiles_storage.hashed_files, {})
        manifest_content = storage.staticfiles_storage.read_manifest()
        self.assertIn(
            '"version": "%s"' % storage.staticfiles_storage.manifest_version,
            manifest_content
        )

    def test_parse_cache(self):
        hashed_files = storage.staticfiles_storage.hashed_files
        manifest = storage.staticfiles_storage.load_manifest()
        self.assertEqual(hashed_files, manifest)

    def test_clear_empties_manifest(self):
        cleared_file_name = storage.staticfiles_storage.clean_name(os.path.join('test', 'cleared.txt'))
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

    def test_missing_entry(self):
        missing_file_name = 'cached/missing.css'
        configured_storage = storage.staticfiles_storage
        self.assertNotIn(missing_file_name, configured_storage.hashed_files)

        # File name not found in manifest
        with self.assertRaisesMessage(ValueError, "Missing staticfiles manifest entry for '%s'" % missing_file_name):
            self.hashed_file_path(missing_file_name)

        configured_storage.manifest_strict = False
        # File doesn't exist on disk
        err_msg = "The file '%s' could not be found with %r." % (missing_file_name, configured_storage._wrapped)
        with self.assertRaisesMessage(ValueError, err_msg):
            self.hashed_file_path(missing_file_name)

        content = StringIO()
        content.write('Found')
        configured_storage.save(missing_file_name, content)
        # File exists on disk
        self.hashed_file_path(missing_file_name)


@override_settings(
    STATICFILES_STORAGE='staticfiles_tests.storage.SimpleCachedStaticFilesStorage',
)
class TestCollectionSimpleCachedStorage(CollectionTestCase):
    """
    Tests for the Cache busting storage
    """
    hashed_file_path = hashed_file_path

    def setUp(self):
        storage.staticfiles_storage.hashed_files.clear()  # avoid cache interference
        super().setUp()

    def test_template_tag_return(self):
        """
        Test the CachedStaticFilesStorage backend.
        """
        self.assertStaticRaises(ValueError, "does/not/exist.png", "/static/does/not/exist.png")
        self.assertStaticRenders("test/file.txt", "/static/test/file.deploy12345.txt")
        self.assertStaticRenders("cached/styles.css", "/static/cached/styles.deploy12345.css")
        self.assertStaticRenders("path/", "/static/path/")
        self.assertStaticRenders("path/?query", "/static/path/?query")

    def test_template_tag_simple_content(self):
        relpath = self.hashed_file_path("cached/styles.css")
        self.assertEqual(relpath, "cached/styles.deploy12345.css")
        with storage.staticfiles_storage.open(relpath) as relfile:
            content = relfile.read()
            self.assertNotIn(b"cached/other.css", content)
            self.assertIn(b"other.deploy12345.css", content)


class CustomStaticFilesStorage(storage.StaticFilesStorage):
    """
    Used in TestStaticFilePermissions
    """
    def __init__(self, *args, **kwargs):
        kwargs['file_permissions_mode'] = 0o640
        kwargs['directory_permissions_mode'] = 0o740
        super().__init__(*args, **kwargs)


@unittest.skipIf(sys.platform.startswith('win'), "Windows only partially supports chmod.")
class TestStaticFilePermissions(CollectionTestCase):

    command_params = {
        'interactive': False,
        'verbosity': 0,
        'ignore_patterns': ['*.ignoreme'],
    }

    def setUp(self):
        self.umask = 0o027
        self.old_umask = os.umask(self.umask)
        super().setUp()

    def tearDown(self):
        os.umask(self.old_umask)
        super().tearDown()

    # Don't run collectstatic command in this test class.
    def run_collectstatic(self, **kwargs):
        pass

    @override_settings(
        FILE_UPLOAD_PERMISSIONS=0o655,
        FILE_UPLOAD_DIRECTORY_PERMISSIONS=0o765,
    )
    def test_collect_static_files_permissions(self):
        call_command('collectstatic', **self.command_params)
        test_file = os.path.join(settings.STATIC_ROOT, "test.txt")
        test_dir = os.path.join(settings.STATIC_ROOT, "subdir")
        file_mode = os.stat(test_file)[0] & 0o777
        dir_mode = os.stat(test_dir)[0] & 0o777
        self.assertEqual(file_mode, 0o655)
        self.assertEqual(dir_mode, 0o765)

    @override_settings(
        FILE_UPLOAD_PERMISSIONS=None,
        FILE_UPLOAD_DIRECTORY_PERMISSIONS=None,
    )
    def test_collect_static_files_default_permissions(self):
        call_command('collectstatic', **self.command_params)
        test_file = os.path.join(settings.STATIC_ROOT, "test.txt")
        test_dir = os.path.join(settings.STATIC_ROOT, "subdir")
        file_mode = os.stat(test_file)[0] & 0o777
        dir_mode = os.stat(test_dir)[0] & 0o777
        self.assertEqual(file_mode, 0o666 & ~self.umask)
        self.assertEqual(dir_mode, 0o777 & ~self.umask)

    @override_settings(
        FILE_UPLOAD_PERMISSIONS=0o655,
        FILE_UPLOAD_DIRECTORY_PERMISSIONS=0o765,
        STATICFILES_STORAGE='staticfiles_tests.test_storage.CustomStaticFilesStorage',
    )
    def test_collect_static_files_subclass_of_static_storage(self):
        call_command('collectstatic', **self.command_params)
        test_file = os.path.join(settings.STATIC_ROOT, "test.txt")
        test_dir = os.path.join(settings.STATIC_ROOT, "subdir")
        file_mode = os.stat(test_file)[0] & 0o777
        dir_mode = os.stat(test_dir)[0] & 0o777
        self.assertEqual(file_mode, 0o640)
        self.assertEqual(dir_mode, 0o740)


@override_settings(
    STATICFILES_STORAGE='django.contrib.staticfiles.storage.CachedStaticFilesStorage',
)
class TestCollectionHashedFilesCache(CollectionTestCase):
    """
    Files referenced from CSS use the correct final hashed name regardless of
    the order in which the files are post-processed.
    """
    hashed_file_path = hashed_file_path

    def setUp(self):
        self.testimage_path = os.path.join(
            TEST_ROOT, 'project', 'documents', 'cached', 'css', 'img', 'window.png'
        )
        with open(self.testimage_path, 'r+b') as f:
            self._orig_image_content = f.read()
        super().setUp()

    def tearDown(self):
        with open(self.testimage_path, 'w+b') as f:
            f.write(self._orig_image_content)
        super().tearDown()

    def test_file_change_after_collectstatic(self):
        finders.get_finder.cache_clear()
        err = StringIO()
        call_command('collectstatic', interactive=False, verbosity=0, stderr=err)
        with open(self.testimage_path, 'w+b') as f:
            f.write(b"new content of png file to change it's hash")

        # Change modification time of self.testimage_path to make sure it gets
        # collected again.
        mtime = os.path.getmtime(self.testimage_path)
        atime = os.path.getatime(self.testimage_path)
        os.utime(self.testimage_path, (mtime + 1, atime + 1))

        call_command('collectstatic', interactive=False, verbosity=0, stderr=err)
        relpath = self.hashed_file_path('cached/css/window.css')
        with storage.staticfiles_storage.open(relpath) as relfile:
            self.assertIn(b'window.a836fe39729e.png', relfile.read())
