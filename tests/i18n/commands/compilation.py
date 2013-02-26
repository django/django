import os

from django.core.management import call_command, CommandError
from django.test import SimpleTestCase
from django.test.utils import override_settings
from django.utils import translation
from django.utils._os import upath
from django.utils.six import StringIO

test_dir = os.path.abspath(os.path.dirname(upath(__file__)))


class MessageCompilationTests(SimpleTestCase):

    def setUp(self):
        self._cwd = os.getcwd()

    def tearDown(self):
        os.chdir(self._cwd)


class PoFileTests(MessageCompilationTests):

    LOCALE = 'es_AR'
    MO_FILE = 'locale/%s/LC_MESSAGES/django.mo' % LOCALE

    def test_bom_rejection(self):
        os.chdir(test_dir)
        with self.assertRaises(CommandError) as cm:
            call_command('compilemessages', locale=self.LOCALE, stderr=StringIO())
        self.assertIn("file has a BOM (Byte Order Mark)", cm.exception.args[0])
        self.assertFalse(os.path.exists(self.MO_FILE))


class PoFileContentsTests(MessageCompilationTests):
    # Ticket #11240

    LOCALE='fr'
    MO_FILE='locale/%s/LC_MESSAGES/django.mo' % LOCALE

    def setUp(self):
        super(PoFileContentsTests, self).setUp()
        self.addCleanup(os.unlink, os.path.join(test_dir, self.MO_FILE))

    def test_percent_symbol_in_po_file(self):
        os.chdir(test_dir)
        call_command('compilemessages', locale=self.LOCALE, stderr=StringIO())
        self.assertTrue(os.path.exists(self.MO_FILE))


class PercentRenderingTests(MessageCompilationTests):
    # Ticket #11240 -- Testing rendering doesn't belong here but we are trying
    # to keep tests for all the stack together

    LOCALE='it'
    MO_FILE='locale/%s/LC_MESSAGES/django.mo' % LOCALE

    @override_settings(LOCALE_PATHS=(os.path.join(test_dir, 'locale'),))
    def test_percent_symbol_escaping(self):
        from django.template import Template, Context
        os.chdir(test_dir)
        call_command('compilemessages', locale=self.LOCALE, stderr=StringIO())
        with translation.override(self.LOCALE):
            t = Template('{% load i18n %}{% trans "Looks like a str fmt spec %% o but shouldn\'t be interpreted as such" %}')
            rendered = t.render(Context({}))
            self.assertEqual(rendered, 'IT translation contains %% for the above string')

            t = Template('{% load i18n %}{% trans "Completed 50%% of all the tasks" %}')
            rendered = t.render(Context({}))
            self.assertEqual(rendered, 'IT translation of Completed 50%% of all the tasks')


@override_settings(LOCALE_PATHS=(os.path.join(test_dir, 'locale'),))
class MultipleLocaleCompilationTests(MessageCompilationTests):
    MO_FILE_HR = None
    MO_FILE_FR = None

    def setUp(self):
        super(MultipleLocaleCompilationTests, self).setUp()
        self.localedir = os.path.join(test_dir, 'locale')
        self.MO_FILE_HR = os.path.join(self.localedir, 'hr/LC_MESSAGES/django.mo')
        self.MO_FILE_FR = os.path.join(self.localedir, 'fr/LC_MESSAGES/django.mo')
        self.addCleanup(self._rmfile, os.path.join(self.localedir, self.MO_FILE_HR))
        self.addCleanup(self._rmfile, os.path.join(self.localedir, self.MO_FILE_FR))

    def _rmfile(self, filepath):
        if os.path.exists(filepath):
            os.remove(filepath)

    def test_one_locale(self):
        os.chdir(test_dir)
        call_command('compilemessages', locale='hr', stderr=StringIO())

        self.assertTrue(os.path.exists(self.MO_FILE_HR))

    def test_multiple_locales(self):
        os.chdir(test_dir)
        call_command('compilemessages', locale=['hr', 'fr'], stderr=StringIO())

        self.assertTrue(os.path.exists(self.MO_FILE_HR))
        self.assertTrue(os.path.exists(self.MO_FILE_FR))
