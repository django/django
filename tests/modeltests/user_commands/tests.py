import sys

from django.core import management
from django.core.management.base import CommandError
from django.test import TestCase
from django.utils import translation
from django.utils.six import StringIO


class CommandTests(TestCase):
    def test_command(self):
        out = StringIO()
        management.call_command('dance', stdout=out)
        self.assertEqual(out.getvalue(),
            "I don't feel like dancing Rock'n'Roll.\n")

    def test_command_style(self):
        out = StringIO()
        management.call_command('dance', style='Jive', stdout=out)
        self.assertEqual(out.getvalue(),
            "I don't feel like dancing Jive.\n")

    def test_language_preserved(self):
        out = StringIO()
        with translation.override('fr'):
            management.call_command('dance', stdout=out)
            self.assertEqual(translation.get_language(), 'fr')

    def test_explode(self):
        """ Test that an unknown command raises CommandError """
        self.assertRaises(CommandError, management.call_command, ('explode',))

    def test_system_exit(self):
        """ Exception raised in a command should raise CommandError with
            call_command, but SystemExit when run from command line
        """
        with self.assertRaises(CommandError):
            management.call_command('dance', example="raise")
        old_stderr = sys.stderr
        sys.stderr = err = StringIO()
        try:
            with self.assertRaises(SystemExit):
                management.ManagementUtility(['manage.py', 'dance', '--example=raise']).execute()
        finally:
            sys.stderr = old_stderr
        self.assertIn("CommandError", err.getvalue())

    def test_default_en_us_locale_set(self):
        # Forces en_us when set to true
        out = StringIO()
        with translation.override('pl'):
            management.call_command('leave_locale_alone_false', stdout=out)
            self.assertEqual(out.getvalue(), "en-us\n")

    def test_configured_locale_preserved(self):
        # Leaves locale from settings when set to false
        out = StringIO()
        with translation.override('pl'):
            management.call_command('leave_locale_alone_true', stdout=out)
            self.assertEqual(out.getvalue(), "pl\n")
