import json
import os
import re
import shutil
import sys
import tempfile
import textwrap
import unittest
from io import StringIO
from pathlib import Path
from unittest import mock

from django.conf import STATICFILES_STORAGE_ALIAS, settings
from django.contrib.staticfiles import finders, storage
from django.contrib.staticfiles.management.commands.collectstatic import (
    Command as CollectstaticCommand,
)
from django.core.management import call_command
from django.test import SimpleTestCase, override_settings

from .cases import CollectionTestCase
from .settings import TEST_ROOT


def hashed_file_path(test, path):
    fullpath = test.render_template(test.static_template_snippet(path))
    return fullpath.removeprefix(settings.STATIC_URL)


class TestHashedFiles:
    hashed_file_path = hashed_file_path

    def tearDown(self):
        # Clear hashed files to avoid side effects among tests.
        storage.staticfiles_storage.hashed_files.clear()

    def assertPostCondition(self):
        """
        Assert post conditions for a test are met. Must be manually called at
        the end of each test.
        """
        pass

    def test_template_tag_return(self):
        self.assertStaticRaises(
            ValueError, "does/not/exist.png", "/static/does/not/exist.png"
        )
        self.assertStaticRenders("test/file.txt", "/static/test/file.dad0999e4f8f.txt")
        self.assertStaticRenders(
            "test/file.txt", "/static/test/file.dad0999e4f8f.txt", asvar=True
        )
        self.assertStaticRenders(
            "cached/styles.css", "/static/cached/styles.5e0040571e1a.css"
        )
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
        self.assertEqual(relpath, "cached/css/ignored.55e7c226dda1.css")
        with storage.staticfiles_storage.open(relpath) as relfile:
            content = relfile.read()
            self.assertIn(b"#foobar", content)
            self.assertIn(b"http:foobar", content)
            self.assertIn(b"https:foobar", content)
            self.assertIn(b"data:foobar", content)
            self.assertIn(b"chrome:foobar", content)
            self.assertIn(b"//foobar", content)
            self.assertIn(b"url()", content)
        self.assertPostCondition()

    def test_path_with_querystring(self):
        relpath = self.hashed_file_path("cached/styles.css?spam=eggs")
        self.assertEqual(relpath, "cached/styles.5e0040571e1a.css?spam=eggs")
        with storage.staticfiles_storage.open(
            "cached/styles.5e0040571e1a.css"
        ) as relfile:
            content = relfile.read()
            self.assertNotIn(b"cached/other.css", content)
            self.assertIn(b"other.d41d8cd98f00.css", content)
        self.assertPostCondition()

    def test_path_with_fragment(self):
        relpath = self.hashed_file_path("cached/styles.css#eggs")
        self.assertEqual(relpath, "cached/styles.5e0040571e1a.css#eggs")
        with storage.staticfiles_storage.open(
            "cached/styles.5e0040571e1a.css"
        ) as relfile:
            content = relfile.read()
            self.assertNotIn(b"cached/other.css", content)
            self.assertIn(b"other.d41d8cd98f00.css", content)
        self.assertPostCondition()

    def test_path_with_querystring_and_fragment(self):
        relpath = self.hashed_file_path("cached/css/fragments.css")
        self.assertEqual(relpath, "cached/css/fragments.f79c9b1f7afb.css")
        with storage.staticfiles_storage.open(relpath) as relfile:
            content = relfile.read()
            self.assertIn(b"fonts/font.b9b105392eb8.eot?#iefix", content)
            self.assertIn(b"fonts/font.b8d603e42714.svg#webfontIyfZbseF", content)
            self.assertIn(
                b"fonts/font.b8d603e42714.svg#path/to/../../fonts/font.svg", content
            )
            self.assertIn(
                b"data:font/woff;charset=utf-8;"
                b"base64,d09GRgABAAAAADJoAA0AAAAAR2QAAQAAAAAAAAAAAAA",
                content,
            )
            self.assertIn(b"#default#VML", content)
        self.assertPostCondition()

    def test_template_tag_absolute(self):
        relpath = self.hashed_file_path("cached/absolute.css")
        self.assertEqual(relpath, "cached/absolute.8f5d0e644e9a.css")
        with storage.staticfiles_storage.open(relpath) as relfile:
            content = relfile.read()
            self.assertNotIn(b"/static/cached/styles.css", content)
            self.assertIn(b"/static/cached/styles.5e0040571e1a.css", content)
            self.assertNotIn(b"/static/styles_root.css", content)
            self.assertIn(b"/static/styles_root.401f2509a628.css", content)
            self.assertIn(b"/static/cached/img/relative.acae32e4532b.png", content)
        self.assertPostCondition()

    def test_template_tag_absolute_root(self):
        """
        Like test_template_tag_absolute, but for a file in STATIC_ROOT
        (#26249).
        """
        relpath = self.hashed_file_path("absolute_root.css")
        self.assertEqual(relpath, "absolute_root.f821df1b64f7.css")
        with storage.staticfiles_storage.open(relpath) as relfile:
            content = relfile.read()
            self.assertNotIn(b"/static/styles_root.css", content)
            self.assertIn(b"/static/styles_root.401f2509a628.css", content)
        self.assertPostCondition()

    def test_template_tag_relative(self):
        relpath = self.hashed_file_path("cached/other.css")
        self.assertEqual(relpath, "cached/other.d41d8cd98f00.css")
        relpath = self.hashed_file_path("cached/styles.css")
        with storage.staticfiles_storage.open(relpath) as relfile:
            content = relfile.read()
            self.assertIn(b'@import url("other.d41d8cd98f00.css");', content)

        self.assertEqual(relpath, "cached/styles.5e0040571e1a.css")
        relpath = self.hashed_file_path("cached/relative.css")
        self.assertEqual(relpath, "cached/relative.34327b3618b2.css")
        with storage.staticfiles_storage.open(relpath) as relfile:
            content = relfile.read()
            self.assertNotIn(b"../cached/styles.css", content)
            self.assertNotIn(b'@import "styles.css"', content)
            self.assertNotIn(b"url(img/relative.png)", content)
            self.assertIn(b"url(img/relative.acae32e4532b.png)", content)
            self.assertIn(b"../cached/styles.5e0040571e1a.css", content)
        self.assertPostCondition()

    def test_import_replacement(self):
        "See #18050"
        relpath = self.hashed_file_path("cached/import.css")
        self.assertEqual(relpath, "cached/import.43b91f9f84d7.css")
        with storage.staticfiles_storage.open(relpath) as relfile:
            content = relfile.read()
            self.assertIn(b"""@import 'styles.5e0040571e1a.css'""", content)
            self.assertIn(
                b"""@import url("/static/styles_root.401f2509a628.css");""", content
            )
            self.assertIn(
                b"""@import url(styles.5e0040571e1a.css) layer(default);""", content
            )
            self.assertIn(
                b'@import url("styles.5e0040571e1a.css") screen and '
                b"(orientation: landscape);",
                content,
            )
            self.assertIn(
                b"""@import url("styles.5e0040571e1a.css") supports""", content
            )
            self.assertIn(b"""/* @import url("/static/m/css/base.css"); */""", content)
            self.assertIn(b"""/* @import url("m/css/base.css"); */""", content)
        self.assertPostCondition()

    def test_template_tag_deep_relative(self):
        relpath = self.hashed_file_path("cached/css/window.css")
        self.assertEqual(relpath, "cached/css/window.5d5c10836967.css")
        with storage.staticfiles_storage.open(relpath) as relfile:
            content = relfile.read()
            self.assertNotIn(b"url(img/window.png)", content)
            self.assertIn(b'url("img/window.acae32e4532b.png")', content)
        self.assertPostCondition()

    def test_template_tag_url(self):
        relpath = self.hashed_file_path("cached/url.css")
        self.assertEqual(relpath, "cached/url.902310b73412.css")
        with storage.staticfiles_storage.open(relpath) as relfile:
            self.assertIn(b"https://", relfile.read())
        self.assertPostCondition()

    def test_import_loop(self):
        relpath = self.hashed_file_path("loop/bar.css")
        self.assertEqual(relpath, "loop/bar.0dff9359c324.css")
        with storage.staticfiles_storage.open(relpath) as relfile:
            content = relfile.read()
            self.assertIn(b"foo.0dff9359c324.css", content)
            self.assertIn(b"baz.f67a7bd3d4b0.css", content)

        relpath = self.hashed_file_path("loop/foo.css")
        self.assertEqual(relpath, "loop/foo.0dff9359c324.css")
        with storage.staticfiles_storage.open(relpath) as relfile:
            content = relfile.read()
            self.assertIn(b"bar.0dff9359c324.css", content)
        self.assertPostCondition()

    def test_post_processing(self):
        """
        post_processing behaves correctly.

        Files that are alterable should always be post-processed; files that
        aren't should be skipped.

        collectstatic has already been called once in setUp() for this
        testcase, therefore we check by verifying behavior on a second run.
        """
        collectstatic_args = {
            "interactive": False,
            "verbosity": 0,
            "link": False,
            "clear": False,
            "dry_run": False,
            "post_process": True,
            "use_default_ignore_patterns": True,
            "ignore_patterns": ["*.ignoreme"],
        }

        collectstatic_cmd = CollectstaticCommand()
        collectstatic_cmd.set_options(**collectstatic_args)
        stats = collectstatic_cmd.collect()
        self.assertIn(
            os.path.join("cached", "css", "window.css"), stats["post_processed"]
        )
        self.assertIn(
            os.path.join("cached", "css", "img", "window.png"), stats["unmodified"]
        )
        self.assertIn(os.path.join("test", "nonascii.css"), stats["post_processed"])
        # No file should be yielded twice.
        self.assertCountEqual(stats["post_processed"], set(stats["post_processed"]))
        self.assertPostCondition()

    def test_css_import_case_insensitive(self):
        relpath = self.hashed_file_path("cached/styles_insensitive.css")
        self.assertEqual(relpath, "cached/styles_insensitive.b76e982a2972.css")
        with storage.staticfiles_storage.open(relpath) as relfile:
            content = relfile.read()
            self.assertNotIn(b"cached/other.css", content)
            self.assertIn(b"other.d41d8cd98f00.css", content)
        self.assertPostCondition()

    def test_css_data_uri_with_nested_url(self):
        relpath = self.hashed_file_path("cached/data_uri_with_nested_url.css")
        with storage.staticfiles_storage.open(relpath) as relfile:
            content = relfile.read()
            self.assertIn(b'url("data:image/svg+xml,url(%23b) url(%23c)")', content)
        self.assertPostCondition()

    def test_css_source_map(self):
        relpath = self.hashed_file_path("cached/source_map.css")
        self.assertEqual(relpath, "cached/source_map.71fc17082a18.css")
        with storage.staticfiles_storage.open(relpath) as relfile:
            content = relfile.read()
            self.assertNotIn(b"/*# sourceMappingURL=source_map.css.map*/", content)
            self.assertIn(
                b"/*# sourceMappingURL=source_map.css.99914b932bd3.map*/",
                content,
            )
        self.assertPostCondition()

    def test_css_source_map_tabs(self):
        relpath = self.hashed_file_path("cached/source_map_tabs.css")
        self.assertEqual(relpath, "cached/source_map_tabs.3cfab363b8cc.css")
        with storage.staticfiles_storage.open(relpath) as relfile:
            content = relfile.read()
            self.assertNotIn(b"/*#\tsourceMappingURL=source_map.css.map\t*/", content)
            self.assertIn(
                b"/*#\tsourceMappingURL=source_map.css.99914b932bd3.map\t*/",
                content,
            )
        self.assertPostCondition()

    def test_css_source_map_sensitive(self):
        relpath = self.hashed_file_path("cached/source_map_sensitive.css")
        self.assertEqual(relpath, "cached/source_map_sensitive.456683f2106f.css")
        with storage.staticfiles_storage.open(relpath) as relfile:
            content = relfile.read()
            self.assertIn(b"/*# sOuRcEMaPpInGURL=source_map.css.map */", content)
            self.assertNotIn(
                b"/*# sourceMappingURL=source_map.css.99914b932bd3.map */",
                content,
            )
        self.assertPostCondition()

    def test_css_source_map_data_uri(self):
        relpath = self.hashed_file_path("cached/source_map_data_uri.css")
        self.assertEqual(relpath, "cached/source_map_data_uri.3166be10260d.css")
        with storage.staticfiles_storage.open(relpath) as relfile:
            content = relfile.read()
            source_map_data_uri = (
                b"/*# sourceMappingURL=data:application/json;charset=utf8;base64,"
                b"eyJ2ZXJzaW9uIjozLCJzb3VyY2VzIjpbIl9zcmMv*/"
            )
            self.assertIn(source_map_data_uri, content)
        self.assertPostCondition()

    def test_js_source_map(self):
        relpath = self.hashed_file_path("cached/source_map.js")
        self.assertEqual(relpath, "cached/source_map.cd45b8534a87.js")
        with storage.staticfiles_storage.open(relpath) as relfile:
            content = relfile.read()
            self.assertNotIn(b"//# sourceMappingURL=source_map.js.map", content)
            self.assertIn(
                b"//# sourceMappingURL=source_map.js.99914b932bd3.map",
                content,
            )
        self.assertPostCondition()

    def test_js_source_map_trailing_whitespace(self):
        relpath = self.hashed_file_path("cached/source_map_trailing_whitespace.js")
        self.assertEqual(
            relpath, "cached/source_map_trailing_whitespace.223547dfd723.js"
        )
        with storage.staticfiles_storage.open(relpath) as relfile:
            content = relfile.read()
            self.assertNotIn(b"//# sourceMappingURL=source_map.js.map\t ", content)
            self.assertIn(
                b"//# sourceMappingURL=source_map.js.99914b932bd3.map\t",
                content,
            )
        self.assertPostCondition()

    def test_js_source_map_sensitive(self):
        relpath = self.hashed_file_path("cached/source_map_sensitive.js")
        self.assertEqual(relpath, "cached/source_map_sensitive.5da96fdd3cb3.js")
        with storage.staticfiles_storage.open(relpath) as relfile:
            content = relfile.read()
            self.assertIn(b"//# sOuRcEMaPpInGURL=source_map.js.map", content)
            self.assertNotIn(
                b"//# sourceMappingURL=source_map.js.99914b932bd3.map",
                content,
            )
        self.assertPostCondition()

    def test_js_source_map_data_uri(self):
        relpath = self.hashed_file_path("cached/source_map_data_uri.js")
        self.assertEqual(relpath, "cached/source_map_data_uri.a68d23cbf6dd.js")
        with storage.staticfiles_storage.open(relpath) as relfile:
            content = relfile.read()
            source_map_data_uri = (
                b"//# sourceMappingURL=data:application/json;charset=utf8;base64,"
                b"eyJ2ZXJzaW9uIjozLCJzb3VyY2VzIjpbIl9zcmMv"
            )
            self.assertIn(source_map_data_uri, content)
        self.assertPostCondition()

    @override_settings(
        STATICFILES_DIRS=[os.path.join(TEST_ROOT, "project", "faulty")],
        STATICFILES_FINDERS=["django.contrib.staticfiles.finders.FileSystemFinder"],
    )
    def test_post_processing_failure(self):
        """
        post_processing indicates the origin of the error when it fails.
        """
        finders.get_finder.cache_clear()
        err = StringIO()
        with self.assertRaises(Exception):
            call_command("collectstatic", interactive=False, verbosity=0, stderr=err)
        self.assertEqual("Post-processing 'faulty.css' failed!\n\n", err.getvalue())
        self.assertPostCondition()

    @override_settings(
        STATICFILES_DIRS=[os.path.join(TEST_ROOT, "project", "nonutf8")],
        STATICFILES_FINDERS=["django.contrib.staticfiles.finders.FileSystemFinder"],
    )
    def test_post_processing_nonutf8(self):
        finders.get_finder.cache_clear()
        err = StringIO()
        with self.assertRaises(UnicodeDecodeError):
            call_command("collectstatic", interactive=False, verbosity=0, stderr=err)
        self.assertEqual("Post-processing 'nonutf8.css' failed!\n\n", err.getvalue())
        self.assertPostCondition()


@override_settings(
    STORAGES={
        **settings.STORAGES,
        STATICFILES_STORAGE_ALIAS: {
            "BACKEND": "django.contrib.staticfiles.storage.ManifestStaticFilesStorage",
        },
    }
)
class TestCollectionManifestStorage(TestHashedFiles, CollectionTestCase):
    """
    Tests for the Cache busting storage
    """

    def setUp(self):
        super().setUp()

        temp_dir = tempfile.mkdtemp()
        os.makedirs(os.path.join(temp_dir, "test"))
        self._clear_filename = os.path.join(temp_dir, "test", "cleared.txt")
        with open(self._clear_filename, "w") as f:
            f.write("to be deleted in one test")

        patched_settings = self.settings(
            STATICFILES_DIRS=settings.STATICFILES_DIRS + [temp_dir],
        )
        patched_settings.enable()
        self.addCleanup(patched_settings.disable)
        self.addCleanup(shutil.rmtree, temp_dir)
        self._manifest_strict = storage.staticfiles_storage.manifest_strict

    def tearDown(self):
        if os.path.exists(self._clear_filename):
            os.unlink(self._clear_filename)

        storage.staticfiles_storage.manifest_strict = self._manifest_strict
        super().tearDown()

    def assertPostCondition(self):
        hashed_files = storage.staticfiles_storage.hashed_files
        # The in-memory version of the manifest matches the one on disk
        # since a properly created manifest should cover all filenames.
        if hashed_files:
            manifest, _ = storage.staticfiles_storage.load_manifest()
            self.assertEqual(hashed_files, manifest)

    def test_manifest_exists(self):
        filename = storage.staticfiles_storage.manifest_name
        path = storage.staticfiles_storage.path(filename)
        self.assertTrue(os.path.exists(path))

    def test_manifest_does_not_exist(self):
        storage.staticfiles_storage.manifest_name = "does.not.exist.json"
        self.assertIsNone(storage.staticfiles_storage.read_manifest())

    def test_manifest_does_not_ignore_permission_error(self):
        with mock.patch("builtins.open", side_effect=PermissionError):
            with self.assertRaises(PermissionError):
                storage.staticfiles_storage.read_manifest()

    def test_loaded_cache(self):
        self.assertNotEqual(storage.staticfiles_storage.hashed_files, {})
        manifest_content = storage.staticfiles_storage.read_manifest()
        self.assertIn(
            '"version": "%s"' % storage.staticfiles_storage.manifest_version,
            manifest_content,
        )

    def test_parse_cache(self):
        hashed_files = storage.staticfiles_storage.hashed_files
        manifest, _ = storage.staticfiles_storage.load_manifest()
        self.assertEqual(hashed_files, manifest)

    def test_clear_empties_manifest(self):
        cleared_file_name = storage.staticfiles_storage.clean_name(
            os.path.join("test", "cleared.txt")
        )
        # collect the additional file
        self.run_collectstatic()

        hashed_files = storage.staticfiles_storage.hashed_files
        self.assertIn(cleared_file_name, hashed_files)

        manifest_content, _ = storage.staticfiles_storage.load_manifest()
        self.assertIn(cleared_file_name, manifest_content)

        original_path = storage.staticfiles_storage.path(cleared_file_name)
        self.assertTrue(os.path.exists(original_path))

        # delete the original file form the app, collect with clear
        os.unlink(self._clear_filename)
        self.run_collectstatic(clear=True)

        self.assertFileNotFound(original_path)

        hashed_files = storage.staticfiles_storage.hashed_files
        self.assertNotIn(cleared_file_name, hashed_files)

        manifest_content, _ = storage.staticfiles_storage.load_manifest()
        self.assertNotIn(cleared_file_name, manifest_content)

    def test_missing_entry(self):
        missing_file_name = "cached/missing.css"
        configured_storage = storage.staticfiles_storage
        self.assertNotIn(missing_file_name, configured_storage.hashed_files)

        # File name not found in manifest
        with self.assertRaisesMessage(
            ValueError,
            "Missing staticfiles manifest entry for '%s'" % missing_file_name,
        ):
            self.hashed_file_path(missing_file_name)

        configured_storage.manifest_strict = False
        # File doesn't exist on disk
        err_msg = "The file '%s' could not be found with %r." % (
            missing_file_name,
            configured_storage._wrapped,
        )
        with self.assertRaisesMessage(ValueError, err_msg):
            self.hashed_file_path(missing_file_name)

        content = StringIO()
        content.write("Found")
        configured_storage.save(missing_file_name, content)
        # File exists on disk
        self.hashed_file_path(missing_file_name)

    def test_intermediate_files(self):
        cached_files = os.listdir(os.path.join(settings.STATIC_ROOT, "cached"))
        # Intermediate files shouldn't be created for reference.
        self.assertEqual(
            len(
                [
                    cached_file
                    for cached_file in cached_files
                    if cached_file.startswith("relative.")
                ]
            ),
            2,
        )

    def test_manifest_hash(self):
        # Collect the additional file.
        self.run_collectstatic()

        _, manifest_hash_orig = storage.staticfiles_storage.load_manifest()
        self.assertNotEqual(manifest_hash_orig, "")
        self.assertEqual(storage.staticfiles_storage.manifest_hash, manifest_hash_orig)
        # Saving doesn't change the hash.
        storage.staticfiles_storage.save_manifest()
        self.assertEqual(storage.staticfiles_storage.manifest_hash, manifest_hash_orig)
        # Delete the original file from the app, collect with clear.
        os.unlink(self._clear_filename)
        self.run_collectstatic(clear=True)
        # Hash is changed.
        _, manifest_hash = storage.staticfiles_storage.load_manifest()
        self.assertNotEqual(manifest_hash, manifest_hash_orig)

    def test_manifest_hash_v1(self):
        storage.staticfiles_storage.manifest_name = "staticfiles_v1.json"
        manifest_content, manifest_hash = storage.staticfiles_storage.load_manifest()
        self.assertEqual(manifest_hash, "")
        self.assertEqual(manifest_content, {"dummy.txt": "dummy.txt"})

    def test_manifest_file_consistent_content(self):
        original_manifest_content = storage.staticfiles_storage.read_manifest()
        hashed_files = storage.staticfiles_storage.hashed_files
        # Force a change in the order of the hashed files.
        with mock.patch.object(
            storage.staticfiles_storage,
            "hashed_files",
            dict(reversed(hashed_files.items())),
        ):
            storage.staticfiles_storage.save_manifest()
        manifest_file_content = storage.staticfiles_storage.read_manifest()
        # The manifest file content should not change.
        self.assertEqual(original_manifest_content, manifest_file_content)


@override_settings(
    STATIC_URL="/",
    STORAGES={
        **settings.STORAGES,
        STATICFILES_STORAGE_ALIAS: {
            "BACKEND": "django.contrib.staticfiles.storage.ManifestStaticFilesStorage",
        },
    },
)
class TestCollectionManifestStorageStaticUrlSlash(CollectionTestCase):
    run_collectstatic_in_setUp = False
    hashed_file_path = hashed_file_path

    def test_protocol_relative_url_ignored(self):
        with override_settings(
            STATICFILES_DIRS=[os.path.join(TEST_ROOT, "project", "static_url_slash")],
            STATICFILES_FINDERS=["django.contrib.staticfiles.finders.FileSystemFinder"],
        ):
            self.run_collectstatic()
        relpath = self.hashed_file_path("ignored.css")
        self.assertEqual(relpath, "ignored.61707f5f4942.css")
        with storage.staticfiles_storage.open(relpath) as relfile:
            content = relfile.read()
            self.assertIn(b"//foobar", content)


@override_settings(
    STORAGES={
        **settings.STORAGES,
        STATICFILES_STORAGE_ALIAS: {
            "BACKEND": "staticfiles_tests.storage.NoneHashStorage",
        },
    }
)
class TestCollectionNoneHashStorage(CollectionTestCase):
    hashed_file_path = hashed_file_path

    def test_hashed_name(self):
        relpath = self.hashed_file_path("cached/styles.css")
        self.assertEqual(relpath, "cached/styles.css")


@override_settings(
    STORAGES={
        **settings.STORAGES,
        STATICFILES_STORAGE_ALIAS: {
            "BACKEND": "staticfiles_tests.storage.SimpleStorage",
        },
    }
)
class TestCollectionSimpleStorage(CollectionTestCase):
    hashed_file_path = hashed_file_path

    def setUp(self):
        storage.staticfiles_storage.hashed_files.clear()  # avoid cache interference
        super().setUp()

    def test_template_tag_return(self):
        self.assertStaticRaises(
            ValueError, "does/not/exist.png", "/static/does/not/exist.png"
        )
        self.assertStaticRenders("test/file.txt", "/static/test/file.deploy12345.txt")
        self.assertStaticRenders(
            "cached/styles.css", "/static/cached/styles.deploy12345.css"
        )
        self.assertStaticRenders("path/", "/static/path/")
        self.assertStaticRenders("path/?query", "/static/path/?query")

    def test_template_tag_simple_content(self):
        relpath = self.hashed_file_path("cached/styles.css")
        self.assertEqual(relpath, "cached/styles.deploy12345.css")
        with storage.staticfiles_storage.open(relpath) as relfile:
            content = relfile.read()
            self.assertNotIn(b"cached/other.css", content)
            self.assertIn(b"other.deploy12345.css", content)


class JSModuleImportAggregationManifestStorage(storage.ManifestStaticFilesStorage):
    support_js_module_import_aggregation = True


@override_settings(
    STORAGES={
        **settings.STORAGES,
        STATICFILES_STORAGE_ALIAS: {
            "BACKEND": (
                "staticfiles_tests.test_storage."
                "JSModuleImportAggregationManifestStorage"
            ),
        },
    }
)
class TestCollectionJSModuleImportAggregationManifestStorage(CollectionTestCase):
    hashed_file_path = hashed_file_path

    def _get_filename_path(self, filename):
        return os.path.join(self._temp_dir, "test", filename)

    def setUp(self):
        super().setUp()
        self._temp_dir = temp_dir = tempfile.mkdtemp()
        os.makedirs(os.path.join(temp_dir, "test"))
        self.addCleanup(shutil.rmtree, temp_dir)

    def test_module_import(self):
        relpath = self.hashed_file_path("cached/module.js")
        self.assertEqual(relpath, "cached/module.5960f712d6bb.js")
        tests = [
            # Relative imports.
            b'import testConst from "./module_test.477bbebe77f0.js";',
            b'import relativeModule from "../nested/js/nested.866475c46bb4.js";',
            b'import { firstConst, secondConst } from "./module_test.477bbebe77f0.js";',
            # Absolute import.
            b'import rootConst from "/static/absolute_root.5586327fe78c.js";',
            # Dynamic import.
            b'const dynamicModule = import("./module_test.477bbebe77f0.js");',
            b"const dynamicModule = import('./module_test.477bbebe77f0.js');",
            b"const dynamicModule = import(`./module_test.477bbebe77f0.js`);",
            # Creating a module object.
            b'import * as NewModule from "./module_test.477bbebe77f0.js";',
            # Creating a minified module object.
            b'import*as m from "./module_test.477bbebe77f0.js";',
            b'import* as m from "./module_test.477bbebe77f0.js";',
            b'import *as m from "./module_test.477bbebe77f0.js";',
            b'import*  as  m from "./module_test.477bbebe77f0.js";',
            # Aliases.
            b'import { testConst as alias } from "./module_test.477bbebe77f0.js";',
            b"import {\n"
            b"    firstVar1 as firstVarAlias,\n"
            b"    $second_var_2 as secondVarAlias\n"
            b'} from "./module_test.477bbebe77f0.js";',
            # With Assert
            b'import k from"./other.d41d8cd98f00.css"assert{type:"css"};',
            # Unprocessed
            b'// @returns {import("./non-existent-1").something}',
            b'/* @returns {import("./non-existent-2").something} */',
            b"'import(\"./non-existent-3\")'",
            b"\"import('./non-existent-4')\"",
            b'`import("./non-existent-5")`',
            b"r = /import/;",
            b"/**\n"
            b" * @param {HTMLElement} elt\n"
            b' * @returns {import("./htmx").HtmxTriggerSpecification[]}\n'
            b" */",
        ]
        with storage.staticfiles_storage.open(relpath) as relfile:
            content = relfile.read()
            for module_import in tests:
                with self.subTest(module_import=module_import):
                    self.assertIn(module_import, content)

    def test_aggregating_modules(self):
        relpath = self.hashed_file_path("cached/module.js")
        self.assertEqual(relpath, "cached/module.5960f712d6bb.js")
        tests = [
            b'export * from "./module_test.477bbebe77f0.js";',
            b'export { testConst } from "./module_test.477bbebe77f0.js";',
            b"export {\n"
            b"    firstVar as firstVarAlias,\n"
            b"    secondVar as secondVarAlias\n"
            b'} from "./module_test.477bbebe77f0.js";',
        ]
        with storage.staticfiles_storage.open(relpath) as relfile:
            content = relfile.read()
            for module_import in tests:
                with self.subTest(module_import=module_import):
                    self.assertIn(module_import, content)

    def test_template_literal_with_variables(self):
        """
        Test that template literals with variables raise an appropriate error.
        """
        # Create initial static files.
        file_contents = (
            ("dynamic_import.js", "import(`./${module_name}`);"),
            ("module.js", "this"),
        )
        for filename, content in file_contents:
            with open(self._get_filename_path(filename), "w") as f:
                f.write(content)

        with self.modify_settings(STATICFILES_DIRS={"append": self._temp_dir}):
            finders.get_finder.cache_clear()
            err = StringIO()
            # Expect ValueError with message about template literals
            error_message = "Found a template literal with a variable: ./${module_name}"

            with self.assertRaisesMessage(ValueError, error_message):
                call_command(
                    "collectstatic", interactive=False, verbosity=0, stderr=err
                )


class CustomExtractorStorage(storage.ManifestStaticFilesStorage):
    """Test storage that extracts custom JS_URL() patterns."""

    def _extract_txt_urls(self, name, content):
        urls = []
        for match in re.finditer(r'JS_URL\(["\']([^"\']+)["\']\)', content):
            urls.append((match.group(1), match.start(1)))
        return urls

    @property
    def url_finders(self):
        return {
            **super().url_finders,
            "*.txt": [self._extract_txt_urls],
        }


@override_settings(
    STORAGES={
        **settings.STORAGES,
        STATICFILES_STORAGE_ALIAS: {
            "BACKEND": "staticfiles_tests.test_storage.CustomExtractorStorage",
        },
    }
)
class TestCustomExtractorStorage(CollectionTestCase):
    """Test the url_finders property for custom URL extraction."""

    hashed_file_path = hashed_file_path

    def _get_filename_path(self, filename):
        return os.path.join(self._temp_dir, "test", filename)

    def setUp(self):
        super().setUp()
        self._temp_dir = temp_dir = tempfile.mkdtemp()
        os.makedirs(os.path.join(temp_dir, "test"))
        self.addCleanup(shutil.rmtree, temp_dir)

    def test_custom_extractor(self):
        """Test that custom URL extractors work correctly."""
        file_contents = (
            ("image.png", "fake image content"),
            ("config.txt", 'var icon = JS_URL("image.png");'),
        )
        for filename, content in file_contents:
            with open(self._get_filename_path(filename), "w") as f:
                f.write(content)

        with self.modify_settings(STATICFILES_DIRS={"append": self._temp_dir}):
            finders.get_finder.cache_clear()
            call_command("collectstatic", interactive=False, verbosity=0)

            # Verify the custom pattern was processed
            relpath = self.hashed_file_path("test/config.txt")
            with storage.staticfiles_storage.open(relpath) as relfile:
                content = relfile.read()
                # Should contain hashed image reference
                self.assertIn(b"image.", content)
                self.assertIn(b".png", content)
                self.assertNotIn(b'JS_URL("image.png")', content)


class CustomManifestStorage(storage.ManifestStaticFilesStorage):
    def __init__(self, *args, manifest_storage=None, **kwargs):
        manifest_storage = storage.StaticFilesStorage(
            location=kwargs.pop("manifest_location"),
        )
        super().__init__(*args, manifest_storage=manifest_storage, **kwargs)


class TestCustomManifestStorage(SimpleTestCase):
    def setUp(self):
        manifest_path = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, manifest_path)

        self.staticfiles_storage = CustomManifestStorage(
            manifest_location=manifest_path,
        )
        self.manifest_file = manifest_path / self.staticfiles_storage.manifest_name
        # Manifest without paths.
        self.manifest = {"version": self.staticfiles_storage.manifest_version}
        with self.manifest_file.open("w") as manifest_file:
            json.dump(self.manifest, manifest_file)

    def test_read_manifest(self):
        self.assertEqual(
            self.staticfiles_storage.read_manifest(),
            json.dumps(self.manifest),
        )

    def test_read_manifest_nonexistent(self):
        os.remove(self.manifest_file)
        self.assertIsNone(self.staticfiles_storage.read_manifest())

    def test_save_manifest_override(self):
        self.assertIs(self.manifest_file.exists(), True)
        self.staticfiles_storage.save_manifest()
        self.assertIs(self.manifest_file.exists(), True)
        new_manifest = json.loads(self.staticfiles_storage.read_manifest())
        self.assertIn("paths", new_manifest)
        self.assertNotEqual(new_manifest, self.manifest)

    def test_save_manifest_create(self):
        os.remove(self.manifest_file)
        self.staticfiles_storage.save_manifest()
        self.assertIs(self.manifest_file.exists(), True)
        new_manifest = json.loads(self.staticfiles_storage.read_manifest())
        self.assertIn("paths", new_manifest)
        self.assertNotEqual(new_manifest, self.manifest)


class CustomStaticFilesStorage(storage.StaticFilesStorage):
    """
    Used in TestStaticFilePermissions
    """

    def __init__(self, *args, **kwargs):
        kwargs["file_permissions_mode"] = 0o640
        kwargs["directory_permissions_mode"] = 0o740
        super().__init__(*args, **kwargs)


@unittest.skipIf(sys.platform == "win32", "Windows only partially supports chmod.")
class TestStaticFilePermissions(CollectionTestCase):
    command_params = {
        "interactive": False,
        "verbosity": 0,
        "ignore_patterns": ["*.ignoreme"],
    }

    def setUp(self):
        self.umask = 0o027
        old_umask = os.umask(self.umask)
        self.addCleanup(os.umask, old_umask)
        super().setUp()

    # Don't run collectstatic command in this test class.
    def run_collectstatic(self, **kwargs):
        pass

    @override_settings(
        FILE_UPLOAD_PERMISSIONS=0o655,
        FILE_UPLOAD_DIRECTORY_PERMISSIONS=0o765,
    )
    def test_collect_static_files_permissions(self):
        call_command("collectstatic", **self.command_params)
        static_root = Path(settings.STATIC_ROOT)
        test_file = static_root / "test.txt"
        file_mode = test_file.stat().st_mode & 0o777
        self.assertEqual(file_mode, 0o655)
        tests = [
            static_root / "subdir",
            static_root / "nested",
            static_root / "nested" / "css",
        ]
        for directory in tests:
            with self.subTest(directory=directory):
                dir_mode = directory.stat().st_mode & 0o777
                self.assertEqual(dir_mode, 0o765)

    @override_settings(
        FILE_UPLOAD_PERMISSIONS=None,
        FILE_UPLOAD_DIRECTORY_PERMISSIONS=None,
    )
    def test_collect_static_files_default_permissions(self):
        call_command("collectstatic", **self.command_params)
        static_root = Path(settings.STATIC_ROOT)
        test_file = static_root / "test.txt"
        file_mode = test_file.stat().st_mode & 0o777
        self.assertEqual(file_mode, 0o666 & ~self.umask)
        tests = [
            static_root / "subdir",
            static_root / "nested",
            static_root / "nested" / "css",
        ]
        for directory in tests:
            with self.subTest(directory=directory):
                dir_mode = directory.stat().st_mode & 0o777
                self.assertEqual(dir_mode, 0o777 & ~self.umask)

    @override_settings(
        FILE_UPLOAD_PERMISSIONS=0o655,
        FILE_UPLOAD_DIRECTORY_PERMISSIONS=0o765,
        STORAGES={
            **settings.STORAGES,
            STATICFILES_STORAGE_ALIAS: {
                "BACKEND": "staticfiles_tests.test_storage.CustomStaticFilesStorage",
            },
        },
    )
    def test_collect_static_files_subclass_of_static_storage(self):
        call_command("collectstatic", **self.command_params)
        static_root = Path(settings.STATIC_ROOT)
        test_file = static_root / "test.txt"
        file_mode = test_file.stat().st_mode & 0o777
        self.assertEqual(file_mode, 0o640)
        tests = [
            static_root / "subdir",
            static_root / "nested",
            static_root / "nested" / "css",
        ]
        for directory in tests:
            with self.subTest(directory=directory):
                dir_mode = directory.stat().st_mode & 0o777
                self.assertEqual(dir_mode, 0o740)


@override_settings(
    STORAGES={
        **settings.STORAGES,
        STATICFILES_STORAGE_ALIAS: {
            "BACKEND": "django.contrib.staticfiles.storage.ManifestStaticFilesStorage",
        },
    }
)
class TestCollectionHashedFilesCache(CollectionTestCase):
    """
    Files referenced from CSS use the correct final hashed name regardless of
    the order in which the files are post-processed.
    """

    hashed_file_path = hashed_file_path

    def setUp(self):
        super().setUp()
        self._temp_dir = temp_dir = tempfile.mkdtemp()
        os.makedirs(os.path.join(temp_dir, "test"))
        self.addCleanup(shutil.rmtree, temp_dir)

    def _get_filename_path(self, filename):
        return os.path.join(self._temp_dir, "test", filename)

    def test_file_change_after_collectstatic(self):
        # Create initial static files.
        file_contents = (
            ("foo.png", "foo"),
            (
                "bar.css",
                'div{background:url("foo.png");}span{background:url("xyz.png");}',
            ),
            ("xyz.png", "xyz"),
        )
        for filename, content in file_contents:
            with open(self._get_filename_path(filename), "w") as f:
                f.write(content)

        with self.modify_settings(STATICFILES_DIRS={"append": self._temp_dir}):
            finders.get_finder.cache_clear()
            err = StringIO()
            # First collectstatic run.
            call_command("collectstatic", interactive=False, verbosity=0, stderr=err)
            relpath = self.hashed_file_path("test/bar.css")
            with storage.staticfiles_storage.open(relpath) as relfile:
                content = relfile.read()
                self.assertIn(b"foo.acbd18db4cc2.png", content)
                self.assertIn(b"xyz.d16fb36f0911.png", content)

            # Change the contents of the png files.
            for filename in ("foo.png", "xyz.png"):
                with open(self._get_filename_path(filename), "w+b") as f:
                    f.write(b"new content of file to change its hash")

            # The hashes of the png files in the CSS file are updated after
            # a second collectstatic.
            call_command("collectstatic", interactive=False, verbosity=0, stderr=err)
            relpath = self.hashed_file_path("test/bar.css")
            with storage.staticfiles_storage.open(relpath) as relfile:
                content = relfile.read()
                self.assertIn(b"foo.57a5cb9ba68d.png", content)
                self.assertIn(b"xyz.57a5cb9ba68d.png", content)

    def test_file_missing_during_collectstatic(self):
        # Create initial static files.
        file_contents = (
            ("foo.png", "foo"),
            (
                "bar.css",
                'div{background:url("foo.png");}span{background:url("xyz.png");}',
            ),
        )
        for filename, content in file_contents:
            with open(self._get_filename_path(filename), "w") as f:
                f.write(content)

        with self.modify_settings(STATICFILES_DIRS={"append": self._temp_dir}):
            finders.get_finder.cache_clear()
            err = StringIO()
            configured_storage = storage.staticfiles_storage
            _expected_error_msg = textwrap.dedent(
                """\
                The file '{missing}' could not be found with {storage}.

                The {ext} file '{filename}' references a file which could not be found:
                  {missing}

                Please check the URL references in this {ext} file, particularly any
                relative paths which might be pointing to the wrong location.
                """
            )
            err_msg = _expected_error_msg.format(
                missing="test/xyz.png",
                storage=configured_storage._wrapped,
                filename=os.path.join("test", "bar.css"),
                ext="CSS",
                url="xyz.png",
            )
            with self.assertRaisesMessage(ValueError, err_msg):
                call_command(
                    "collectstatic", interactive=False, verbosity=0, stderr=err
                )

    def test_circular_dependencies(self):
        """
        Test handling of circular dependencies between CSS files with changes
        """
        # Create initial static files with circular dependencies
        file_contents = (
            ("style1.css", "@import url('style2.css');\n.style1 { color: red; }"),
            (
                "style2.css",
                "@import url('style1.css');\n@import url('common.css');\n"
                ".style2 { color: blue; }",
            ),
            ("common.css", ".common { color: green; }"),
        )

        for filename, content in file_contents:
            with open(self._get_filename_path(filename), "w") as f:
                f.write(content)

        with self.modify_settings(STATICFILES_DIRS={"append": self._temp_dir}):
            finders.get_finder.cache_clear()
            err = StringIO()

            call_command("collectstatic", interactive=False, verbosity=0, stderr=err)

            # Get the hashed paths for the files
            style1_path = self.hashed_file_path("test/style1.css")
            style2_path = self.hashed_file_path("test/style2.css")
            common_path = self.hashed_file_path("test/common.css")

            # Extract hash parts from the filenames
            style1_hash = style1_path.split(".")[-2]
            style2_hash = style2_path.split(".")[-2]
            common_hash = common_path.split(".")[-2]

            # 1. Verify that style1.css and style2.css have the same hash
            self.assertEqual(
                style1_hash,
                style2_hash,
                "Files with circular dependencies should have the same hash",
            )

            # 2. style1.css references the hashed version of style2.css
            with storage.staticfiles_storage.open(style1_path) as relfile:
                content = relfile.read()
                self.assertIn(f"style2.{style2_hash}.css".encode(), content)

            # 3. style2.css references the hashed versions style1 & common.css
            with storage.staticfiles_storage.open(style2_path) as relfile:
                content = relfile.read()
                self.assertIn(f"style1.{style1_hash}.css".encode(), content)

                # 4. style2.css correctly references common.css
                self.assertIn(f"common.{common_hash}.css".encode(), content)

            # Update the content of common.css
            with open(self._get_filename_path("common.css"), "w+b") as f:
                f.write(b".common { color: black; }")

            # a second collectstatic.
            call_command("collectstatic", interactive=False, verbosity=0, stderr=err)
            style1_path = self.hashed_file_path("test/style1.css")
            style2_path = self.hashed_file_path("test/style2.css")
            common_path = self.hashed_file_path("test/common.css")

            style1_hash_changed = style1_path.split(".")[-2]
            style2_hash_changed = style2_path.split(".")[-2]
            common_hash_changed = common_path.split(".")[-2]

            # hashes should all have changed
            self.assertNotEqual(style1_hash, style1_hash_changed)
            self.assertNotEqual(style2_hash, style2_hash_changed)
            self.assertNotEqual(common_hash, common_hash_changed)

            with storage.staticfiles_storage.open(style1_path) as relfile:
                content = relfile.read()
                self.assertIn(f"style2.{style2_hash_changed}.css".encode(), content)

            # 3. style2.css references the hashed versions style1 & common.css
            with storage.staticfiles_storage.open(style2_path) as relfile:
                content = relfile.read()
                self.assertIn(f"style1.{style1_hash_changed}.css".encode(), content)

                # 4. style2.css correctly references common.css
                self.assertIn(f"common.{common_hash_changed}.css".encode(), content)
