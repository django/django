from __future__ import unicode_literals
from datetime import date

from django.contrib.auth import models, management
from django.contrib.auth.management import create_permissions
from django.contrib.auth.management.commands import changepassword
from django.contrib.auth.models import User
from django.contrib.auth.tests import CustomUser
from django.contrib.auth.tests.utils import skipIfCustomUser
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.test.utils import override_settings
from django.utils import six
from django.utils.six import StringIO


@skipIfCustomUser
class GetDefaultUsernameTestCase(TestCase):

    def setUp(self):
        self.old_get_system_username = management.get_system_username

    def tearDown(self):
        management.get_system_username = self.old_get_system_username

    def test_actual_implementation(self):
        self.assertIsInstance(management.get_system_username(), six.text_type)

    def test_simple(self):
        management.get_system_username = lambda: 'joe'
        self.assertEqual(management.get_default_username(), 'joe')

    def test_existing(self):
        models.User.objects.create(username='joe')
        management.get_system_username = lambda: 'joe'
        self.assertEqual(management.get_default_username(), '')
        self.assertEqual(
            management.get_default_username(check_db=False), 'joe')

    def test_i18n(self):
        # 'Julia' with accented 'u':
        management.get_system_username = lambda: 'J\xfalia'
        self.assertEqual(management.get_default_username(), 'julia')


@skipIfCustomUser
class ChangepasswordManagementCommandTestCase(TestCase):

    def setUp(self):
        self.user = models.User.objects.create_user(username='joe', password='qwerty')
        self.stdout = StringIO()
        self.stderr = StringIO()

    def tearDown(self):
        self.stdout.close()
        self.stderr.close()

    def test_that_changepassword_command_changes_joes_password(self):
        "Executing the changepassword management command should change joe's password"
        self.assertTrue(self.user.check_password('qwerty'))
        command = changepassword.Command()
        command._get_pass = lambda *args: 'not qwerty'

        command.execute("joe", stdout=self.stdout)
        command_output = self.stdout.getvalue().strip()

        self.assertEqual(command_output, "Changing password for user 'joe'\nPassword changed successfully for user 'joe'")
        self.assertTrue(models.User.objects.get(username="joe").check_password("not qwerty"))

    def test_that_max_tries_exits_1(self):
        """
        A CommandError should be thrown by handle() if the user enters in
        mismatched passwords three times.
        """
        command = changepassword.Command()
        command._get_pass = lambda *args: args or 'foo'

        with self.assertRaises(CommandError):
            command.execute("joe", stdout=self.stdout, stderr=self.stderr)


@skipIfCustomUser
class CreatesuperuserManagementCommandTestCase(TestCase):

    def test_createsuperuser(self):
        "Check the operation of the createsuperuser management command"
        # We can use the management command to create a superuser
        new_io = StringIO()
        call_command("createsuperuser",
            interactive=False,
            username="joe",
            email="joe@somewhere.org",
            stdout=new_io
        )
        command_output = new_io.getvalue().strip()
        self.assertEqual(command_output, 'Superuser created successfully.')
        u = User.objects.get(username="joe")
        self.assertEqual(u.email, 'joe@somewhere.org')

        # created password should be unusable
        self.assertFalse(u.has_usable_password())

    def test_verbosity_zero(self):
        # We can supress output on the management command
        new_io = StringIO()
        call_command("createsuperuser",
            interactive=False,
            username="joe2",
            email="joe2@somewhere.org",
            verbosity=0,
            stdout=new_io
        )
        command_output = new_io.getvalue().strip()
        self.assertEqual(command_output, '')
        u = User.objects.get(username="joe2")
        self.assertEqual(u.email, 'joe2@somewhere.org')
        self.assertFalse(u.has_usable_password())

    def test_email_in_username(self):
        new_io = StringIO()
        call_command("createsuperuser",
            interactive=False,
            username="joe+admin@somewhere.org",
            email="joe@somewhere.org",
            stdout=new_io
        )
        u = User._default_manager.get(username="joe+admin@somewhere.org")
        self.assertEqual(u.email, 'joe@somewhere.org')
        self.assertFalse(u.has_usable_password())

    @override_settings(AUTH_USER_MODEL='auth.CustomUser')
    def test_swappable_user(self):
        "A superuser can be created when a custom User model is in use"
        # We can use the management command to create a superuser
        # We skip validation because the temporary substitution of the
        # swappable User model messes with validation.
        new_io = StringIO()
        call_command("createsuperuser",
            interactive=False,
            email="joe@somewhere.org",
            date_of_birth="1976-04-01",
            stdout=new_io,
            skip_validation=True
        )
        command_output = new_io.getvalue().strip()
        self.assertEqual(command_output, 'Superuser created successfully.')
        u = CustomUser._default_manager.get(email="joe@somewhere.org")
        self.assertEqual(u.date_of_birth, date(1976, 4, 1))

        # created password should be unusable
        self.assertFalse(u.has_usable_password())

    @override_settings(AUTH_USER_MODEL='auth.CustomUser')
    def test_swappable_user_missing_required_field(self):
        "A Custom superuser won't be created when a required field isn't provided"
        # We can use the management command to create a superuser
        # We skip validation because the temporary substitution of the
        # swappable User model messes with validation.
        new_io = StringIO()
        with self.assertRaises(CommandError):
            call_command("createsuperuser",
                interactive=False,
                username="joe@somewhere.org",
                stdout=new_io,
                stderr=new_io,
                skip_validation=True
            )

        self.assertEqual(CustomUser._default_manager.count(), 0)


class PermissionDuplicationTestCase(TestCase):

    def setUp(self):
        self._original_permissions = models.Permission._meta.permissions[:]

    def tearDown(self):
        models.Permission._meta.permissions = self._original_permissions

    def test_duplicated_permissions(self):
        """
        Test that we show proper error message if we are trying to create
        duplicate permissions.
        """
        # check duplicated default permission
        models.Permission._meta.permissions = [
           ('change_permission', 'Can edit permission (duplicate)')]
        six.assertRaisesRegex(self, CommandError,
            "The permission codename 'change_permission' clashes with a "
            "builtin permission for model 'auth.Permission'.",
            create_permissions, models, [], verbosity=0)

        # check duplicated custom permissions
        models.Permission._meta.permissions = [
            ('my_custom_permission', 'Some permission'),
            ('other_one', 'Some other permission'),
            ('my_custom_permission', 'Some permission with duplicate permission code'),
        ]
        six.assertRaisesRegex(self, CommandError,
            "The permission codename 'my_custom_permission' is duplicated for model "
            "'auth.Permission'.",
            create_permissions, models, [], verbosity=0)

        # should not raise anything
        models.Permission._meta.permissions = [
            ('my_custom_permission', 'Some permission'),
            ('other_one', 'Some other permission'),
        ]
        create_permissions(models, [], verbosity=0)
