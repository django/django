"""
A series of tests to establish that the command-line bash completion works.
"""
import os
import sys
import StringIO

from django.conf import settings
from django.core.management import ManagementUtility
from django.utils import unittest


class BashCompletionTests(unittest.TestCase):
    """
    Testing the Python level bash completion code.
    This requires setting up the environment as if we got passed data
    from bash.
    """

    def setUp(self):
        self.old_DJANGO_AUTO_COMPLETE = os.environ.get('DJANGO_AUTO_COMPLETE')
        os.environ['DJANGO_AUTO_COMPLETE'] = '1'
        self.output = StringIO.StringIO()
        self.old_stdout = sys.stdout
        sys.stdout = self.output

    def tearDown(self):
        sys.stdout = self.old_stdout
        if self.old_DJANGO_AUTO_COMPLETE:
            os.environ['DJANGO_AUTO_COMPLETE'] = self.old_DJANGO_AUTO_COMPLETE
        else:
            del os.environ['DJANGO_AUTO_COMPLETE']

    def _user_input(self, input_str):
        os.environ['COMP_WORDS'] = input_str
        os.environ['COMP_CWORD'] = str(len(input_str.split()) - 1)
        sys.argv = input_str.split(' ')

    def _run_autocomplete(self):
        util = ManagementUtility(argv=sys.argv)
        try:
            util.autocomplete()
        except SystemExit:
            pass
        return self.output.getvalue().strip().split('\n')

    def test_django_admin_py(self):
        "django_admin.py will autocomplete option flags"
        self._user_input('django-admin.py sqlall --v')
        output = self._run_autocomplete()
        self.assertEqual(output, ['--verbosity='])

    def test_manage_py(self):
        "manage.py will autocomplete option flags"
        self._user_input('manage.py sqlall --v')
        output = self._run_autocomplete()
        self.assertEqual(output, ['--verbosity='])

    def test_custom_command(self):
        "A custom command can autocomplete option flags"
        self._user_input('django-admin.py test_command --l')
        output = self._run_autocomplete()
        self.assertEqual(output, ['--list'])

    def test_subcommands(self):
        "Subcommands can be autocompleted"
        self._user_input('django-admin.py sql')
        output = self._run_autocomplete()
        self.assertEqual(output, ['sql sqlall sqlclear sqlcustom sqlflush sqlindexes sqlinitialdata sqlsequencereset'])

    def test_help(self):
        "No errors, just an empty list if there are no autocomplete options"
        self._user_input('django-admin.py help --')
        output = self._run_autocomplete()
        self.assertEqual(output, [''])

    def test_runfcgi(self):
        "Command arguments will be autocompleted"
        self._user_input('django-admin.py runfcgi h')
        output = self._run_autocomplete()
        self.assertEqual(output, ['host='])

    def test_app_completion(self):
        "Application names will be autocompleted for an AppCommand"
        self._user_input('django-admin.py sqlall a')
        output = self._run_autocomplete()
        app_labels = [name.split('.')[-1] for name in settings.INSTALLED_APPS]
        self.assertEqual(output, sorted(label for label in app_labels if label.startswith('a')))
