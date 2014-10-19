import os
import sys
import warnings

from django.db import connection
from django.core import management
from django.core.management import BaseCommand, CommandError
from django.core.management.utils import find_command, popen_wrapper
from django.test import SimpleTestCase
from django.utils import translation
from django.utils.deprecation import RemovedInDjango20Warning
from django.utils.six import StringIO


class CommandTests(SimpleTestCase):
    def test_command(self):
        out = StringIO()
        management.call_command('dance', stdout=out)
        self.assertIn("I don't feel like dancing Rock'n'Roll.\n", out.getvalue())

    def test_command_style(self):
        out = StringIO()
        management.call_command('dance', style='Jive', stdout=out)
        self.assertIn("I don't feel like dancing Jive.\n", out.getvalue())
        # Passing options as arguments also works (thanks argparse)
        management.call_command('dance', '--style', 'Jive', stdout=out)
        self.assertIn("I don't feel like dancing Jive.\n", out.getvalue())

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

    def test_find_command_without_PATH(self):
        """
        find_command should still work when the PATH environment variable
        doesn't exist (#22256).
        """
        current_path = os.environ.pop('PATH', None)

        try:
            self.assertIsNone(find_command('_missing_'))
        finally:
            if current_path is not None:
                os.environ['PATH'] = current_path

    def test_call_command_option_parsing(self):
        """
        When passing the long option name to call_command, the available option
        key is the option dest name (#22985).
        """
        out = StringIO()
        management.call_command('dance', stdout=out, opt_3=True)
        self.assertIn("option3", out.getvalue())
        self.assertNotIn("opt_3", out.getvalue())
        self.assertNotIn("opt-3", out.getvalue())

    def test_optparse_compatibility(self):
        """
        optparse should be supported during Django 1.8/1.9 releases.
        """
        out = StringIO()
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=RemovedInDjango20Warning)
            management.call_command('optparse_cmd', stdout=out)
        self.assertEqual(out.getvalue(), "All right, let's dance Rock'n'Roll.\n")

        # Simulate command line execution
        old_stdout, old_stderr = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = StringIO(), StringIO()
        try:
            management.execute_from_command_line(['django-admin', 'optparse_cmd'])
        finally:
            output = sys.stdout.getvalue()
            sys.stdout, sys.stderr = old_stdout, old_stderr
        self.assertEqual(output, "All right, let's dance Rock'n'Roll.\n")

    def test_calling_a_command_with_only_empty_parameter_should_ends_gracefully(self):
        out = StringIO()
        management.call_command('hal', "--empty", stdout=out)
        self.assertIn("Dave, I can't do that.\n", out.getvalue())

    def test_calling_command_with_app_labels_and_parameters_should_be_ok(self):
        out = StringIO()
        management.call_command('hal', 'myapp', "--verbosity", "3", stdout=out)
        self.assertIn("Dave, my mind is going. I can feel it. I can feel it.\n", out.getvalue())

    def test_calling_command_with_parameters_and_app_labels_at_the_end_should_be_ok(self):
        out = StringIO()
        management.call_command('hal', "--verbosity", "3", "myapp", stdout=out)
        self.assertIn("Dave, my mind is going. I can feel it. I can feel it.\n", out.getvalue())

    def test_calling_a_command_with_no_app_labels_and_parameters_should_raise_a_command_error(self):
        out = StringIO()
        with self.assertRaises(CommandError):
            management.call_command('hal', stdout=out)

    def test_output_transaction(self):
        out = StringIO()
        management.call_command('transaction', stdout=out, no_color=True)
        output = out.getvalue().strip()
        self.assertTrue(output.startswith(connection.ops.start_transaction_sql()))
        self.assertTrue(output.endswith(connection.ops.end_transaction_sql()))

    def test_call_command_no_checks(self):
        """
        By default, call_command should not trigger the check framework, unless
        specifically asked.
        """
        self.counter = 0

        def patched_check(self_, **kwargs):
            self.counter = self.counter + 1

        saved_check = BaseCommand.check
        BaseCommand.check = patched_check
        try:
            management.call_command("dance", verbosity=0)
            self.assertEqual(self.counter, 0)
            management.call_command("dance", verbosity=0, skip_checks=False)
            self.assertEqual(self.counter, 1)
        finally:
            BaseCommand.check = saved_check


class UtilsTests(SimpleTestCase):

    def test_no_existent_external_program(self):
        self.assertRaises(CommandError, popen_wrapper, ['a_42_command_that_doesnt_exist_42'])
