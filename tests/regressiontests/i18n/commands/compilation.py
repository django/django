import os
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from django.core.management import CommandError
from django.core.management.commands.compilemessages import compile_messages
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
        # We don't use the django.core.management infrastructure (call_command()
        # et al) because CommandError's cause exit(1) there. We test the
        # underlying compile_messages function instead
        out = StringIO()
        self.assertRaises(CommandError, compile_messages, out, locale=self.LOCALE)
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
        # We don't use the django.core.management infrastructure (call_command()
        # et al) because CommandError's cause exit(1) there. We test the
        # underlying compile_messages function instead
        out = StringIO()
        compile_messages(out, locale=self.LOCALE)
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
        # We don't use the django.core.management infrastructure (call_command()
        # et al) because CommandError's cause exit(1) there. We test the
        # underlying compile_messages function instead
        out = StringIO()
        compile_messages(out, locale=self.LOCALE)
        with translation.override(self.LOCALE):
            t = Template('{% load i18n %}{% trans "Looks like a str fmt spec %% o but shouldn\'t be interpreted as such" %}')
            rendered = t.render(Context({}))
            self.assertEqual(rendered, 'IT translation contains %% for the above string')

            t = Template('{% load i18n %}{% trans "Completed 50%% of all the tasks" %}')
            rendered = t.render(Context({}))
            self.assertEqual(rendered, 'IT translation of Completed 50%% of all the tasks')
