import gettext as gettext_module
import os
import stat
import unittest
from io import StringIO
from subprocess import Popen
from unittest import mock

from django.core.management import (
    CommandError, call_command, execute_from_command_line,
)
from django.core.management.commands.makemessages import (
    Command as MakeMessagesCommand,
)
from django.core.management.utils import find_command
from django.test import SimpleTestCase, override_settings
from django.test.utils import captured_stderr, captured_stdout
from django.utils import translation
from django.utils.translation import gettext

from .utils import RunInTmpDirMixin, copytree

has_msgfmt = find_command('msgfmt')


@unittest.skipUnless(has_msgfmt, 'msgfmt is mandatory for compilation tests')
class MessageCompilationTests(RunInTmpDirMixin, SimpleTestCase):

    work_subdir = 'commands'


class PoFileTests(MessageCompilationTests):

    LOCALE = 'es_AR'
    MO_FILE = 'locale/%s/LC_MESSAGES/django.mo' % LOCALE

    def test_bom_rejection(self):
        with self.assertRaises(CommandError) as cm:
            call_command('compilemessages', locale=[self.LOCALE], stdout=StringIO())
        self.assertIn("file has a BOM (Byte Order Mark)", cm.exception.args[0])
        self.assertFalse(os.path.exists(self.MO_FILE))

    def test_no_write_access(self):
        mo_file_en = 'locale/en/LC_MESSAGES/django.mo'
        err_buffer = StringIO()
        # put file in read-only mode
        old_mode = os.stat(mo_file_en).st_mode
        os.chmod(mo_file_en, stat.S_IREAD)
        try:
            call_command('compilemessages', locale=['en'], stderr=err_buffer, verbosity=0)
            err = err_buffer.getvalue()
            self.assertIn("not writable location", err)
        finally:
            os.chmod(mo_file_en, old_mode)


class PoFileContentsTests(MessageCompilationTests):
    # Ticket #11240

    LOCALE = 'fr'
    MO_FILE = 'locale/%s/LC_MESSAGES/django.mo' % LOCALE

    def test_percent_symbol_in_po_file(self):
        call_command('compilemessages', locale=[self.LOCALE], stdout=StringIO())
        self.assertTrue(os.path.exists(self.MO_FILE))


class MultipleLocaleCompilationTests(MessageCompilationTests):

    MO_FILE_HR = None
    MO_FILE_FR = None

    def setUp(self):
        super().setUp()
        localedir = os.path.join(self.test_dir, 'locale')
        self.MO_FILE_HR = os.path.join(localedir, 'hr/LC_MESSAGES/django.mo')
        self.MO_FILE_FR = os.path.join(localedir, 'fr/LC_MESSAGES/django.mo')

    def test_one_locale(self):
        with override_settings(LOCALE_PATHS=[os.path.join(self.test_dir, 'locale')]):
            call_command('compilemessages', locale=['hr'], stdout=StringIO())

            self.assertTrue(os.path.exists(self.MO_FILE_HR))

    def test_multiple_locales(self):
        with override_settings(LOCALE_PATHS=[os.path.join(self.test_dir, 'locale')]):
            call_command('compilemessages', locale=['hr', 'fr'], stdout=StringIO())

            self.assertTrue(os.path.exists(self.MO_FILE_HR))
            self.assertTrue(os.path.exists(self.MO_FILE_FR))


class ExcludedLocaleCompilationTests(MessageCompilationTests):

    work_subdir = 'exclude'

    MO_FILE = 'locale/%s/LC_MESSAGES/django.mo'

    def setUp(self):
        super().setUp()
        copytree('canned_locale', 'locale')

    def test_command_help(self):
        with captured_stdout(), captured_stderr():
            # `call_command` bypasses the parser; by calling
            # `execute_from_command_line` with the help subcommand we
            # ensure that there are no issues with the parser itself.
            execute_from_command_line(['django-admin', 'help', 'compilemessages'])

    def test_one_locale_excluded(self):
        call_command('compilemessages', exclude=['it'], stdout=StringIO())
        self.assertTrue(os.path.exists(self.MO_FILE % 'en'))
        self.assertTrue(os.path.exists(self.MO_FILE % 'fr'))
        self.assertFalse(os.path.exists(self.MO_FILE % 'it'))

    def test_multiple_locales_excluded(self):
        call_command('compilemessages', exclude=['it', 'fr'], stdout=StringIO())
        self.assertTrue(os.path.exists(self.MO_FILE % 'en'))
        self.assertFalse(os.path.exists(self.MO_FILE % 'fr'))
        self.assertFalse(os.path.exists(self.MO_FILE % 'it'))

    def test_one_locale_excluded_with_locale(self):
        call_command('compilemessages', locale=['en', 'fr'], exclude=['fr'], stdout=StringIO())
        self.assertTrue(os.path.exists(self.MO_FILE % 'en'))
        self.assertFalse(os.path.exists(self.MO_FILE % 'fr'))
        self.assertFalse(os.path.exists(self.MO_FILE % 'it'))

    def test_multiple_locales_excluded_with_locale(self):
        call_command('compilemessages', locale=['en', 'fr', 'it'], exclude=['fr', 'it'],
                     stdout=StringIO())
        self.assertTrue(os.path.exists(self.MO_FILE % 'en'))
        self.assertFalse(os.path.exists(self.MO_FILE % 'fr'))
        self.assertFalse(os.path.exists(self.MO_FILE % 'it'))


class CompilationErrorHandling(MessageCompilationTests):
    def test_error_reported_by_msgfmt(self):
        # po file contains wrong po formatting.
        with self.assertRaises(CommandError):
            call_command('compilemessages', locale=['ja'], verbosity=0)

    def test_msgfmt_error_including_non_ascii(self):
        # po file contains invalid msgstr content (triggers non-ascii error content).
        # Make sure the output of msgfmt is unaffected by the current locale.
        env = os.environ.copy()
        env.update({'LANG': 'C'})
        with mock.patch('django.core.management.utils.Popen', lambda *args, **kwargs: Popen(*args, env=env, **kwargs)):
            cmd = MakeMessagesCommand()
            if cmd.gettext_version < (0, 18, 3):
                self.skipTest("python-brace-format is a recent gettext addition.")
            with self.assertRaisesMessage(CommandError, "' cannot start a field name"):
                call_command('compilemessages', locale=['ko'], verbosity=0)


class ProjectAndAppTests(MessageCompilationTests):
    LOCALE = 'ru'
    PROJECT_MO_FILE = 'locale/%s/LC_MESSAGES/django.mo' % LOCALE
    APP_MO_FILE = 'app_with_locale/locale/%s/LC_MESSAGES/django.mo' % LOCALE


class FuzzyTranslationTest(ProjectAndAppTests):

    def setUp(self):
        super().setUp()
        gettext_module._translations = {}  # flush cache or test will be useless

    def test_nofuzzy_compiling(self):
        with override_settings(LOCALE_PATHS=[os.path.join(self.test_dir, 'locale')]):
            call_command('compilemessages', locale=[self.LOCALE], stdout=StringIO())
            with translation.override(self.LOCALE):
                self.assertEqual(gettext('Lenin'), 'Ленин')
                self.assertEqual(gettext('Vodka'), 'Vodka')

    def test_fuzzy_compiling(self):
        with override_settings(LOCALE_PATHS=[os.path.join(self.test_dir, 'locale')]):
            call_command('compilemessages', locale=[self.LOCALE], fuzzy=True, stdout=StringIO())
            with translation.override(self.LOCALE):
                self.assertEqual(gettext('Lenin'), 'Ленин')
                self.assertEqual(gettext('Vodka'), 'Водка')


class AppCompilationTest(ProjectAndAppTests):

    def test_app_locale_compiled(self):
        call_command('compilemessages', locale=[self.LOCALE], stdout=StringIO())
        self.assertTrue(os.path.exists(self.PROJECT_MO_FILE))
        self.assertTrue(os.path.exists(self.APP_MO_FILE))
