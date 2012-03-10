from StringIO import StringIO

from django.contrib.auth import models
from django.contrib.auth.management.commands import changepassword
from django.core.management import call_command
from django.test import TestCase


class MultiDBChangepasswordManagementCommandTestCase(TestCase):
    multi_db = True

    def setUp(self):
        self.user = models.User.objects.db_manager('other').create_user(username='joe', password='qwerty')
        self.stdout = StringIO()

    def tearDown(self):
        self.stdout.close()

    def test_that_changepassword_command_with_database_option_uses_given_db(self):
        """
        Executing the changepassword management command with a database option
        should operate on the specified DB
        """
        self.assertTrue(self.user.check_password('qwerty'))
        command = changepassword.Command()
        command._get_pass = lambda *args: 'not qwerty'

        command.execute("joe", database='other', stdout=self.stdout)
        command_output = self.stdout.getvalue().strip()

        self.assertEquals(command_output, "Changing password for user 'joe'\nPassword changed successfully for user 'joe'")
        self.assertTrue(models.User.objects.using('other').get(username="joe").check_password("not qwerty"))


class MultiDBCreatesuperuserTestCase(TestCase):
    multi_db = True

    def test_createsuperuser_command_with_database_option(self):
        " createsuperuser command should operate on specified DB"
        new_io = StringIO()

        call_command("createsuperuser",
            interactive=False,
            username="joe",
            email="joe@somewhere.org",
            database='other',
            stdout=new_io
        )
        command_output = new_io.getvalue().strip()

        self.assertEqual(command_output, 'Superuser created successfully.')

        u = models.User.objects.using('other').get(username="joe")
        self.assertEqual(u.email, 'joe@somewhere.org')

        new_io.close()

