import gettext as gettext_module
import os
import stat
import unittest
from io import StringIO
from pathlib import Path
from subprocess import run
from unittest import mock

from django.core.management import CommandError, call_command, execute_from_command_line
from django.core.management.utils import find_command
from django.test import SimpleTestCase, override_settings
from django.test.utils import captured_stderr, captured_stdout
from django.utils import translation
from django.utils.translation import gettext

from .utils import RunInTmpDirMixin, copytree

has_msgfmt = find_command("msgfmt")


@unittest.skipUnless(has_msgfmt, "msgfmt is mandatory for compilation tests")
class MessageCompilationTests(RunInTmpDirMixin, SimpleTestCase):
    work_subdir = "commands"


class PoFileTests(MessageCompilationTests):
    LOCALE = "es_AR"
    MO_FILE = "locale/%s/LC_MESSAGES/django.mo" % LOCALE
    MO_FILE_EN = "locale/en/LC_MESSAGES/django.mo"

    def test_bom_rejection(self):
        stderr = StringIO()
        with self.assertRaisesMessage(
            CommandError, "compilemessages generated one or more errors."
        ):
            call_command(
                "compilemessages", locale=[self.LOCALE], verbosity=0, stderr=stderr
            )
        self.assertIn("file has a BOM (Byte Order Mark)", stderr.getvalue())
        self.assertFalse(os.path.exists(self.MO_FILE))

    def test_no_write_access(self):
        mo_file_en = Path(self.MO_FILE_EN)
        err_buffer = StringIO()
        # Put parent directory in read-only mode.
        old_mode = mo_file_en.parent.stat().st_mode
        mo_file_en.parent.chmod(stat.S_IRUSR | stat.S_IXUSR)
        # Ensure .po file is more recent than .mo file.
        mo_file_en.with_suffix(".po").touch()
        try:
            with self.assertRaisesMessage(
                CommandError, "compilemessages generated one or more errors."
            ):
                call_command(
                    "compilemessages", locale=["en"], stderr=err_buffer, verbosity=0
                )
            self.assertIn("not writable location", err_buffer.getvalue())
        finally:
            mo_file_en.parent.chmod(old_mode)

    def test_no_compile_when_unneeded(self):
        mo_file_en = Path(self.MO_FILE_EN)
        mo_file_en.touch()
        stdout = StringIO()
        call_command("compilemessages", locale=["en"], stdout=stdout, verbosity=1)
        msg = "%s” is already compiled and up to date." % mo_file_en.with_suffix(".po")
        self.assertIn(msg, stdout.getvalue())


class PoFileContentsTests(MessageCompilationTests):
    # Ticket #11240

    LOCALE = "fr"
    MO_FILE = "locale/%s/LC_MESSAGES/django.mo" % LOCALE

    def test_percent_symbol_in_po_file(self):
        call_command("compilemessages", locale=[self.LOCALE], verbosity=0)
        self.assertTrue(os.path.exists(self.MO_FILE))


class MultipleLocaleCompilationTests(MessageCompilationTests):
    MO_FILE_HR = None
    MO_FILE_FR = None

    def setUp(self):
        super().setUp()
        localedir = os.path.join(self.test_dir, "locale")
        self.MO_FILE_HR = os.path.join(localedir, "hr/LC_MESSAGES/django.mo")
        self.MO_FILE_FR = os.path.join(localedir, "fr/LC_MESSAGES/django.mo")

    def test_one_locale(self):
        with override_settings(LOCALE_PATHS=[os.path.join(self.test_dir, "locale")]):
            call_command("compilemessages", locale=["hr"], verbosity=0)

            self.assertTrue(os.path.exists(self.MO_FILE_HR))

    def test_multiple_locales(self):
        with override_settings(LOCALE_PATHS=[os.path.join(self.test_dir, "locale")]):
            call_command("compilemessages", locale=["hr", "fr"], verbosity=0)

            self.assertTrue(os.path.exists(self.MO_FILE_HR))
            self.assertTrue(os.path.exists(self.MO_FILE_FR))


class ExcludedLocaleCompilationTests(MessageCompilationTests):
    work_subdir = "exclude"

    MO_FILE = "locale/%s/LC_MESSAGES/django.mo"

    def setUp(self):
        super().setUp()
        copytree("canned_locale", "locale")

    def test_command_help(self):
        with captured_stdout(), captured_stderr():
            # `call_command` bypasses the parser; by calling
            # `execute_from_command_line` with the help subcommand we
            # ensure that there are no issues with the parser itself.
            execute_from_command_line(["django-admin", "help", "compilemessages"])

    def test_one_locale_excluded(self):
        call_command("compilemessages", exclude=["it"], verbosity=0)
        self.assertTrue(os.path.exists(self.MO_FILE % "en"))
        self.assertTrue(os.path.exists(self.MO_FILE % "fr"))
        self.assertFalse(os.path.exists(self.MO_FILE % "it"))

    def test_multiple_locales_excluded(self):
        call_command("compilemessages", exclude=["it", "fr"], verbosity=0)
        self.assertTrue(os.path.exists(self.MO_FILE % "en"))
        self.assertFalse(os.path.exists(self.MO_FILE % "fr"))
        self.assertFalse(os.path.exists(self.MO_FILE % "it"))

    def test_one_locale_excluded_with_locale(self):
        call_command(
            "compilemessages", locale=["en", "fr"], exclude=["fr"], verbosity=0
        )
        self.assertTrue(os.path.exists(self.MO_FILE % "en"))
        self.assertFalse(os.path.exists(self.MO_FILE % "fr"))
        self.assertFalse(os.path.exists(self.MO_FILE % "it"))

    def test_multiple_locales_excluded_with_locale(self):
        call_command(
            "compilemessages",
            locale=["en", "fr", "it"],
            exclude=["fr", "it"],
            verbosity=0,
        )
        self.assertTrue(os.path.exists(self.MO_FILE % "en"))
        self.assertFalse(os.path.exists(self.MO_FILE % "fr"))
        self.assertFalse(os.path.exists(self.MO_FILE % "it"))


class IgnoreDirectoryCompilationTests(MessageCompilationTests):
    # Reuse the exclude directory since it contains some locale fixtures.
    work_subdir = "exclude"
    MO_FILE = "%s/%s/LC_MESSAGES/django.mo"
    CACHE_DIR = Path("cache") / "locale"
    NESTED_DIR = Path("outdated") / "v1" / "locale"

    def setUp(self):
        super().setUp()
        copytree("canned_locale", "locale")
        copytree("canned_locale", self.CACHE_DIR)
        copytree("canned_locale", self.NESTED_DIR)

    def assertAllExist(self, dir, langs):
        self.assertTrue(
            all(Path(self.MO_FILE % (dir, lang)).exists() for lang in langs)
        )

    def assertNoneExist(self, dir, langs):
        self.assertTrue(
            all(Path(self.MO_FILE % (dir, lang)).exists() is False for lang in langs)
        )

    def test_one_locale_dir_ignored(self):
        call_command("compilemessages", ignore=["cache"], verbosity=0)
        self.assertAllExist("locale", ["en", "fr", "it"])
        self.assertNoneExist(self.CACHE_DIR, ["en", "fr", "it"])
        self.assertAllExist(self.NESTED_DIR, ["en", "fr", "it"])

    def test_multiple_locale_dirs_ignored(self):
        call_command(
            "compilemessages", ignore=["cache/locale", "outdated"], verbosity=0
        )
        self.assertAllExist("locale", ["en", "fr", "it"])
        self.assertNoneExist(self.CACHE_DIR, ["en", "fr", "it"])
        self.assertNoneExist(self.NESTED_DIR, ["en", "fr", "it"])

    def test_ignores_based_on_pattern(self):
        call_command("compilemessages", ignore=["*/locale"], verbosity=0)
        self.assertAllExist("locale", ["en", "fr", "it"])
        self.assertNoneExist(self.CACHE_DIR, ["en", "fr", "it"])
        self.assertNoneExist(self.NESTED_DIR, ["en", "fr", "it"])

    def test_no_dirs_accidentally_skipped(self):
        os_walk_results = [
            # To discover .po filepaths, compilemessages uses with a starting list of
            # basedirs to inspect, which in this scenario are:
            #   ["conf/locale", "locale"]
            # Then os.walk is used to discover other locale dirs, ignoring dirs matching
            # `ignore_patterns`. Mock the results to place an ignored directory directly
            # before and after a directory named "locale".
            [("somedir", ["ignore", "locale", "ignore"], [])],
            # This will result in three basedirs discovered:
            #   ["conf/locale", "locale", "somedir/locale"]
            # os.walk is called for each locale in each basedir looking for .po files.
            # In this scenario, we need to mock os.walk results for "en", "fr", and "it"
            # locales for each basedir:
            [("exclude/locale/LC_MESSAGES", [], ["en.po"])],
            [("exclude/locale/LC_MESSAGES", [], ["fr.po"])],
            [("exclude/locale/LC_MESSAGES", [], ["it.po"])],
            [("exclude/conf/locale/LC_MESSAGES", [], ["en.po"])],
            [("exclude/conf/locale/LC_MESSAGES", [], ["fr.po"])],
            [("exclude/conf/locale/LC_MESSAGES", [], ["it.po"])],
            [("exclude/somedir/locale/LC_MESSAGES", [], ["en.po"])],
            [("exclude/somedir/locale/LC_MESSAGES", [], ["fr.po"])],
            [("exclude/somedir/locale/LC_MESSAGES", [], ["it.po"])],
        ]

        module_path = "django.core.management.commands.compilemessages"
        with mock.patch(f"{module_path}.os.walk", side_effect=os_walk_results):
            with mock.patch(f"{module_path}.os.path.isdir", return_value=True):
                with mock.patch(
                    f"{module_path}.Command.compile_messages"
                ) as mock_compile_messages:
                    call_command("compilemessages", ignore=["ignore"], verbosity=4)

        expected = [
            (
                [
                    ("exclude/locale/LC_MESSAGES", "en.po"),
                    ("exclude/locale/LC_MESSAGES", "fr.po"),
                    ("exclude/locale/LC_MESSAGES", "it.po"),
                ],
            ),
            (
                [
                    ("exclude/conf/locale/LC_MESSAGES", "en.po"),
                    ("exclude/conf/locale/LC_MESSAGES", "fr.po"),
                    ("exclude/conf/locale/LC_MESSAGES", "it.po"),
                ],
            ),
            (
                [
                    ("exclude/somedir/locale/LC_MESSAGES", "en.po"),
                    ("exclude/somedir/locale/LC_MESSAGES", "fr.po"),
                    ("exclude/somedir/locale/LC_MESSAGES", "it.po"),
                ],
            ),
        ]
        self.assertEqual([c.args for c in mock_compile_messages.mock_calls], expected)


class CompilationErrorHandling(MessageCompilationTests):
    def test_error_reported_by_msgfmt(self):
        # po file contains wrong po formatting.
        with self.assertRaises(CommandError):
            call_command("compilemessages", locale=["ja"], verbosity=0)
        # It should still fail a second time.
        with self.assertRaises(CommandError):
            call_command("compilemessages", locale=["ja"], verbosity=0)

    def test_msgfmt_error_including_non_ascii(self):
        # po file contains invalid msgstr content (triggers non-ascii error content).
        # Make sure the output of msgfmt is unaffected by the current locale.
        env = os.environ.copy()
        env.update({"LC_ALL": "C"})
        with mock.patch(
            "django.core.management.utils.run",
            lambda *args, **kwargs: run(*args, env=env, **kwargs),
        ):
            stderr = StringIO()
            with self.assertRaisesMessage(
                CommandError, "compilemessages generated one or more errors"
            ):
                call_command(
                    "compilemessages", locale=["ko"], stdout=StringIO(), stderr=stderr
                )
            self.assertIn("' cannot start a field name", stderr.getvalue())


class ProjectAndAppTests(MessageCompilationTests):
    LOCALE = "ru"
    PROJECT_MO_FILE = "locale/%s/LC_MESSAGES/django.mo" % LOCALE
    APP_MO_FILE = "app_with_locale/locale/%s/LC_MESSAGES/django.mo" % LOCALE


class FuzzyTranslationTest(ProjectAndAppTests):
    def setUp(self):
        super().setUp()
        gettext_module._translations = {}  # flush cache or test will be useless

    def test_nofuzzy_compiling(self):
        with override_settings(LOCALE_PATHS=[os.path.join(self.test_dir, "locale")]):
            call_command("compilemessages", locale=[self.LOCALE], verbosity=0)
            with translation.override(self.LOCALE):
                self.assertEqual(gettext("Lenin"), "Ленин")
                self.assertEqual(gettext("Vodka"), "Vodka")

    def test_fuzzy_compiling(self):
        with override_settings(LOCALE_PATHS=[os.path.join(self.test_dir, "locale")]):
            call_command(
                "compilemessages", locale=[self.LOCALE], fuzzy=True, verbosity=0
            )
            with translation.override(self.LOCALE):
                self.assertEqual(gettext("Lenin"), "Ленин")
                self.assertEqual(gettext("Vodka"), "Водка")


class AppCompilationTest(ProjectAndAppTests):
    def test_app_locale_compiled(self):
        call_command("compilemessages", locale=[self.LOCALE], verbosity=0)
        self.assertTrue(os.path.exists(self.PROJECT_MO_FILE))
        self.assertTrue(os.path.exists(self.APP_MO_FILE))


class PathLibLocaleCompilationTests(MessageCompilationTests):
    work_subdir = "exclude"

    def test_locale_paths_pathlib(self):
        with override_settings(LOCALE_PATHS=[Path(self.test_dir) / "canned_locale"]):
            call_command("compilemessages", locale=["fr"], verbosity=0)
            self.assertTrue(os.path.exists("canned_locale/fr/LC_MESSAGES/django.mo"))
