import os
from io import BytesIO
from StringIO import StringIO

from django.conf import settings
from django.core.management import call_command, CommandError
from django.core.management.commands import compilemessages
from django.test import TestCase
from django.test.utils import override_settings
from django.utils import translation




test_dir = os.path.abspath(os.path.dirname(__file__))

class MessageCompilationTests(TestCase):

    def setUp(self):
        self._cwd = os.getcwd()

    def tearDown(self):
        os.chdir(self._cwd)


class PoFileTests(MessageCompilationTests):

    LOCALE='es_AR'
    MO_FILE='locale/%s/LC_MESSAGES/django.mo' % LOCALE

    def test_bom_rejection(self):
        os.chdir(test_dir)
        with self.assertRaisesRegexp(CommandError,
                "file has a BOM \(Byte Order Mark\)"):
            call_command('compilemessages', locale=self.LOCALE, stderr=BytesIO())
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
        call_command('compilemessages', locale=self.LOCALE, stderr=BytesIO())
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
        call_command('compilemessages', locale=self.LOCALE, stderr=BytesIO())
        with translation.override(self.LOCALE):
            t = Template('{% load i18n %}{% trans "Looks like a str fmt spec %% o but shouldn\'t be interpreted as such" %}')
            rendered = t.render(Context({}))
            self.assertEqual(rendered, 'IT translation contains %% for the above string')

            t = Template('{% load i18n %}{% trans "Completed 50%% of all the tasks" %}')
            rendered = t.render(Context({}))
            self.assertEqual(rendered, 'IT translation of Completed 50%% of all the tasks')


class MultipleLocalesTestCase(TestCase):
    MO_FILE_DE = None
    MO_FILE_FR = None
    
    def setUp(self):
        self._old_locale_paths = settings.LOCALE_PATHS
        self.stderr = StringIO()
        self.localedir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'locale'
        )
        settings.LOCALE_PATHS = [self.localedir]
        self.MO_FILE_DE = os.path.join(self.localedir, 'de/LC_MESSAGES/django.mo')
        self.MO_FILE_FR = os.path.join(self.localedir, 'fr/LC_MESSAGES/django.mo')
        
    def tearDown(self):
        settings.LOCALE_PATHS = self._old_locale_paths
        self.stderr.close()
        self._rmfile(os.path.join(self.localedir, self.MO_FILE_DE))
        self._rmfile(os.path.join(self.localedir, self.MO_FILE_FR))
        
    def _rmfile(self, filepath):
        if os.path.exists(filepath):
            os.remove(filepath)
            
    def test_one_locale(self):
        command = compilemessages.Command()
        command.execute(locale='de', stderr=self.stderr)
        
        self.assertTrue(os.path.exists(self.MO_FILE_DE))
        
    def test_multiple_locales(self):
        command = compilemessages.Command()
        command.execute(locale=['de', 'fr'], stderr=self.stderr)
        
        self.assertTrue(os.path.exists(self.MO_FILE_DE))
        self.assertTrue(os.path.exists(self.MO_FILE_FR))