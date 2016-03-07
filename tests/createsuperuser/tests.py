from django.contrib.auth import models
from django.contrib.auth.management.commands import changepassword
from django.core.management import call_command
from django.test import TestCase, mock
from django.utils.six import StringIO


class MultiDBChangepasswordManagementCommandTestCase(TestCase):
    multi_db = True

    def setUp(self):
        self.user = models.User.objects.db_manager('other').create_user(username='joe', password='qwerty')

    @mock.patch.object(changepassword.Command, '_get_pass', return_value='not qwerty')
    def test_that_changepassword_command_with_database_option_uses_given_db(self, mock_get_pass):
        """
        Executing the changepassword management command with a database option
        should operate on the specified DB
        """
        self.assertTrue(self.user.check_password('qwerty'))

        out = StringIO()
        call_command('changepassword', username='joe', database='other', stdout=out)
        command_output = out.getvalue().strip()

        self.assertEqual(
            command_output,
            "Changing password for user 'joe'\nPassword changed successfully for user 'joe'"
        )
        self.assertTrue(models.User.objects.using('other').get(username="joe").check_password("not qwerty"))


class MultiDBCreatesuperuserTestCase(TestCase):
    multi_db = True

    def test_createsuperuser_command_with_database_option(self):
        " createsuperuser command should operate on specified DB"
        new_io = StringIO()

        call_command(
            "createsuperuser",
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
