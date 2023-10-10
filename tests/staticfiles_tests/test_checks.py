from pathlib import Path
from unittest import mock

from django.conf import DEFAULT_STORAGE_ALIAS, STATICFILES_STORAGE_ALIAS, settings
from django.contrib.staticfiles.checks import E005, check_finders, check_storages
from django.contrib.staticfiles.finders import BaseFinder, get_finder
from django.core.checks import Error, Warning
from django.test import SimpleTestCase, override_settings

from .cases import CollectionTestCase
from .settings import TEST_ROOT


class FindersCheckTests(CollectionTestCase):
    run_collectstatic_in_setUp = False

    def test_base_finder_check_not_implemented(self):
        finder = BaseFinder()
        msg = (
            "subclasses may provide a check() method to verify the finder is "
            "configured correctly."
        )
        with self.assertRaisesMessage(NotImplementedError, msg):
            finder.check()

    def test_check_finders(self):
        """check_finders() concatenates all errors."""
        error1 = Error("1")
        error2 = Error("2")
        error3 = Error("3")

        def get_finders():
            class Finder1(BaseFinder):
                def check(self, **kwargs):
                    return [error1]

            class Finder2(BaseFinder):
                def check(self, **kwargs):
                    return []

            class Finder3(BaseFinder):
                def check(self, **kwargs):
                    return [error2, error3]

            class Finder4(BaseFinder):
                pass

            return [Finder1(), Finder2(), Finder3(), Finder4()]

        with mock.patch("django.contrib.staticfiles.checks.get_finders", get_finders):
            errors = check_finders(None)
            self.assertEqual(errors, [error1, error2, error3])

    def test_no_errors_with_test_settings(self):
        self.assertEqual(check_finders(None), [])

    @override_settings(STATICFILES_DIRS="a string")
    def test_dirs_not_tuple_or_list(self):
        self.assertEqual(
            check_finders(None),
            [
                Error(
                    "The STATICFILES_DIRS setting is not a tuple or list.",
                    hint="Perhaps you forgot a trailing comma?",
                    id="staticfiles.E001",
                )
            ],
        )

    def test_dirs_contains_static_root(self):
        with self.settings(STATICFILES_DIRS=[settings.STATIC_ROOT]):
            self.assertEqual(
                check_finders(None),
                [
                    Error(
                        "The STATICFILES_DIRS setting should not contain the "
                        "STATIC_ROOT setting.",
                        id="staticfiles.E002",
                    )
                ],
            )

    def test_dirs_contains_static_root_in_tuple(self):
        with self.settings(STATICFILES_DIRS=[("prefix", settings.STATIC_ROOT)]):
            self.assertEqual(
                check_finders(None),
                [
                    Error(
                        "The STATICFILES_DIRS setting should not contain the "
                        "STATIC_ROOT setting.",
                        id="staticfiles.E002",
                    )
                ],
            )

    def test_prefix_contains_trailing_slash(self):
        static_dir = Path(TEST_ROOT) / "project" / "documents"
        with self.settings(STATICFILES_DIRS=[("prefix/", static_dir)]):
            self.assertEqual(
                check_finders(None),
                [
                    Error(
                        "The prefix 'prefix/' in the STATICFILES_DIRS setting must "
                        "not end with a slash.",
                        id="staticfiles.E003",
                    ),
                ],
            )

    def test_nonexistent_directories(self):
        with self.settings(
            STATICFILES_DIRS=[
                "/fake/path",
                ("prefix", "/fake/prefixed/path"),
            ]
        ):
            self.assertEqual(
                check_finders(None),
                [
                    Warning(
                        "The directory '/fake/path' in the STATICFILES_DIRS "
                        "setting does not exist.",
                        id="staticfiles.W004",
                    ),
                    Warning(
                        "The directory '/fake/prefixed/path' in the "
                        "STATICFILES_DIRS setting does not exist.",
                        id="staticfiles.W004",
                    ),
                ],
            )
            # Nonexistent directories are skipped.
            finder = get_finder("django.contrib.staticfiles.finders.FileSystemFinder")
            self.assertEqual(list(finder.list(None)), [])


class StoragesCheckTests(SimpleTestCase):
    @override_settings(STORAGES={})
    def test_error_empty_storages(self):
        errors = check_storages(None)
        self.assertEqual(errors, [E005])

    @override_settings(
        STORAGES={
            DEFAULT_STORAGE_ALIAS: {
                "BACKEND": "django.core.files.storage.FileSystemStorage",
            },
            "example": {
                "BACKEND": "ignore.me",
            },
        }
    )
    def test_error_missing_staticfiles(self):
        errors = check_storages(None)
        self.assertEqual(errors, [E005])

    @override_settings(
        STORAGES={
            STATICFILES_STORAGE_ALIAS: {
                "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
            },
        }
    )
    def test_staticfiles_no_errors(self):
        errors = check_storages(None)
        self.assertEqual(errors, [])
