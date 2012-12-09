import os

from django.core.management import call_command, CommandError
from django.test import TestCase
from django.test.utils import override_settings
from django.utils import translation, six
from django.utils._os import upath
from django.utils.six import StringIO

test_dir = os.path.abspath(os.path.dirname(upath(__file__)))


class MessageCompilationTests(TestCase):

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
