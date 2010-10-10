import os
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from django.core.management import CommandError
from django.core.management.commands.compilemessages import compile_messages
from django.test import TestCase

LOCALE='es_AR'


class MessageCompilationTests(TestCase):

    MO_FILE='locale/%s/LC_MESSAGES/django.mo' % LOCALE

    def setUp(self):
        self._cwd = os.getcwd()
        self.test_dir = os.path.abspath(os.path.dirname(__file__))

    def tearDown(self):
        os.chdir(self._cwd)


class PoFileTests(MessageCompilationTests):

    def test_bom_rejection(self):
        os.chdir(self.test_dir)
        # We don't use the django.core.management intrastructure (call_command()
        # et al) because CommandError's cause exit(1) there. We test the
        # underlying compile_messages function instead
        out = StringIO()
        self.assertRaises(CommandError, compile_messages, out, locale=LOCALE)
        self.failIf(os.path.exists(self.MO_FILE))
