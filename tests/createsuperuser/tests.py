from django.contrib.auth import models
from django.contrib.auth.management.commands import changepassword
from django.core.management import call_command
from django.test import TestCase
from django.utils.six import StringIO


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

        self.assertEqual(command_output, "Changing password for user 'joe'\nPassword changed successfully for user 'joe'")
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


class CreateSuperUserReadFromStdin(TestCase):

    def setUp(self):
        self.user = models.User.objects.create_user(username='joe', password='qwerty')
        self.stdout = StringIO()

    def tearDown(self):
        self.stdout.close()

    def test_change_password_reading_from_stdin_works(self):
        class MyStdin(object):
            stdin = [None, 'not qwerty', 'not qwerty']
            def read(self):
                self.stdin = self.stdin[1:]
                if not len(self.stdin):
                    raise EOFError
                return self.stdin[0]

        self.assertTrue(self.user.check_password('qwerty'))
        command = changepassword.Command()
        command.execute(
            "joe",
            stdout=self.stdout,
            read_stdin=True,
            stdin=MyStdin()
        )
        command_output = self.stdout.getvalue().strip()
        self.assertEqual(command_output, "Changing password for user 'joe'\nPassword changed successfully for user 'joe'")
        self.assertTrue(models.User.objects.get(username="joe").check_password("not qwerty"))


class CreateSuperUserInTTYShouldSkip(TestCase):

    def test_createsuperuser_no_tty(self):
        # Ticket Ref: 7423
        class MyStdin(object):

            def isatty(self):
                return False

        new_io = StringIO()

        call_command(
            "createsuperuser",
            stdin=MyStdin(),
            stdout=new_io,
            interactive=True
        )
        command_output = new_io.getvalue().strip()
        output = "Superuser creation skipped due to not running in a shell." \
                 " You can run `createsuperuser` in your shell in your" \
                 " project's directory to create a superuser for your" \
                 " project."

        self.assertEqual(command_output, output)
        new_io.close()
