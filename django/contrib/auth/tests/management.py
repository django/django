from StringIO import StringIO

from django.contrib.auth import models, management
from django.contrib.auth.management.commands import changepassword
from django.test import TestCase


class GetDefaultUsernameTestCase(TestCase):

    def setUp(self):
        self._getpass_getuser = management.get_system_username

    def tearDown(self):
        management.get_system_username = self._getpass_getuser

    def test_simple(self):
        management.get_system_username = lambda: u'joe'
        self.assertEqual(management.get_default_username(), 'joe')

    def test_existing(self):
        models.User.objects.create(username='joe')
        management.get_system_username = lambda: u'joe'
        self.assertEqual(management.get_default_username(), '')
        self.assertEqual(
            management.get_default_username(check_db=False), 'joe')

    def test_i18n(self):
        # 'Julia' with accented 'u':
        management.get_system_username = lambda: u'J\xfalia'
        self.assertEqual(management.get_default_username(), 'julia')


class ChangepasswordManagementCommandTestCase(TestCase):

    def setUp(self):
        self.user = models.User.objects.create_user(username='joe', password='qwerty')
        self.stdout = StringIO()
        self.stderr = StringIO()

    def tearDown(self):
        self.stdout.close()
        self.stderr.close()

    def test_that_changepassword_command_changes_joes_password(self):
        " Executing the changepassword management command should change joe's password "
        self.assertTrue(self.user.check_password('qwerty'))
        command = changepassword.Command()
        command._get_pass = lambda *args: 'not qwerty'

        command.execute("joe", stdout=self.stdout)
        command_output = self.stdout.getvalue().strip()

        self.assertEquals(command_output, "Changing password for user 'joe'\nPassword changed successfully for user 'joe'")
        self.assertTrue(models.User.objects.get(username="joe").check_password("not qwerty"))

    def test_that_max_tries_exits_1(self):
        """
        A CommandError should be thrown by handle() if the user enters in
        mismatched passwords three times. This should be caught by execute() and
        converted to a SystemExit
        """
        command = changepassword.Command()
        command._get_pass = lambda *args: args or 'foo'

        self.assertRaises(
            SystemExit,
            command.execute,
            "joe",
            stdout=self.stdout,
            stderr=self.stderr
        )
