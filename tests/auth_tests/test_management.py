from __future__ import unicode_literals

import locale
import sys
from datetime import date

from django.apps import apps
from django.contrib.auth import management, models
from django.contrib.auth.checks import check_user_model
from django.contrib.auth.management import create_permissions
from django.contrib.auth.management.commands import (
    changepassword, createsuperuser,
)
from django.contrib.auth.models import Group, User
from django.contrib.auth.tests.custom_user import CustomUser
from django.contrib.contenttypes.models import ContentType
from django.core import checks, exceptions
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings, override_system_checks
from django.utils import six
from django.utils.encoding import force_str
from django.utils.translation import ugettext_lazy as _

from .models import (
    CustomUserBadRequiredFields, CustomUserNonListRequiredFields,
    CustomUserNonUniqueUsername, CustomUserWithFK, Email,
)


def mock_inputs(inputs):
    """
    Decorator to temporarily replace input/getpass to allow interactive
    createsuperuser.
    """
    def inner(test_func):
        def wrapped(*args):
            class mock_getpass:
                @staticmethod
                def getpass(prompt=b'Password: ', stream=None):
                    if six.PY2:
                        # getpass on Windows only supports prompt as bytestring (#19807)
                        assert isinstance(prompt, six.binary_type)
                    return inputs['password']

            def mock_input(prompt):
                # prompt should be encoded in Python 2. This line will raise an
                # Exception if prompt contains unencoded non-ASCII on Python 2.
                prompt = str(prompt)
                assert str('__proxy__') not in prompt
                response = ''
                for key, val in inputs.items():
                    if force_str(key) in prompt.lower():
                        response = val
                        break
                return response

            old_getpass = createsuperuser.getpass
            old_input = createsuperuser.input
            createsuperuser.getpass = mock_getpass
            createsuperuser.input = mock_input
            try:
                test_func(*args)
            finally:
                createsuperuser.getpass = old_getpass
                createsuperuser.input = old_input
        return wrapped
    return inner


class MockTTY(object):
    """
    A fake stdin object that pretends to be a TTY to be used in conjunction
    with mock_inputs.
    """
    def isatty(self):
        return True


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


class ChangepasswordManagementCommandTestCase(TestCase):

    def setUp(self):
        self.user = models.User.objects.create_user(username='joe', password='qwerty')
        self.stdout = six.StringIO()
        self.stderr = six.StringIO()

    def tearDown(self):
        self.stdout.close()
        self.stderr.close()

    def test_that_changepassword_command_changes_joes_password(self):
        "Executing the changepassword management command should change joe's password"
        self.assertTrue(self.user.check_password('qwerty'))
        command = changepassword.Command()
        command._get_pass = lambda *args: 'not qwerty'

        command.execute(username="joe", stdout=self.stdout)
        command_output = self.stdout.getvalue().strip()

        self.assertEqual(
            command_output,
            "Changing password for user 'joe'\nPassword changed successfully for user 'joe'"
        )
        self.assertTrue(models.User.objects.get(username="joe").check_password("not qwerty"))

    def test_that_max_tries_exits_1(self):
        """
        A CommandError should be thrown by handle() if the user enters in
        mismatched passwords three times.
        """
        command = changepassword.Command()
        command._get_pass = lambda *args: args or 'foo'

        with self.assertRaises(CommandError):
            command.execute(username="joe", stdout=self.stdout, stderr=self.stderr)

    def test_that_changepassword_command_works_with_nonascii_output(self):
        """
        #21627 -- Executing the changepassword management command should allow
        non-ASCII characters from the User object representation.
        """
        # 'Julia' with accented 'u':
        models.User.objects.create_user(username='J\xfalia', password='qwerty')

        command = changepassword.Command()
        command._get_pass = lambda *args: 'not qwerty'

        command.execute(username="J\xfalia", stdout=self.stdout)


@override_settings(SILENCED_SYSTEM_CHECKS=['fields.W342'])  # ForeignKey(unique=True)
class CreatesuperuserManagementCommandTestCase(TestCase):

    def test_basic_usage(self):
        "Check the operation of the createsuperuser management command"
        # We can use the management command to create a superuser
        new_io = six.StringIO()
        call_command(
            "createsuperuser",
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

    @mock_inputs({'password': "nopasswd"})
    def test_nolocale(self):
        """
        Check that createsuperuser does not break when no locale is set. See
        ticket #16017.
        """

        old_getdefaultlocale = locale.getdefaultlocale
        try:
            # Temporarily remove locale information
            locale.getdefaultlocale = lambda: (None, None)

            # Call the command in this new environment
            call_command(
                "createsuperuser",
                interactive=True,
                username="nolocale@somewhere.org",
                email="nolocale@somewhere.org",
                verbosity=0,
                stdin=MockTTY(),
            )

        except TypeError:
            self.fail("createsuperuser fails if the OS provides no information about the current locale")

        finally:
            # Re-apply locale information
            locale.getdefaultlocale = old_getdefaultlocale

        # If we were successful, a user should have been created
        u = User.objects.get(username="nolocale@somewhere.org")
        self.assertEqual(u.email, 'nolocale@somewhere.org')

    @mock_inputs({
        'password': "nopasswd",
        'u\u017eivatel': 'foo',  # username (cz)
        'email': 'nolocale@somewhere.org'})
    def test_non_ascii_verbose_name(self):
        username_field = User._meta.get_field('username')
        old_verbose_name = username_field.verbose_name
        username_field.verbose_name = _('u\u017eivatel')
        new_io = six.StringIO()
        try:
            call_command(
                "createsuperuser",
                interactive=True,
                stdout=new_io,
                stdin=MockTTY(),
            )
        finally:
            username_field.verbose_name = old_verbose_name

        command_output = new_io.getvalue().strip()
        self.assertEqual(command_output, 'Superuser created successfully.')

    def test_verbosity_zero(self):
        # We can suppress output on the management command
        new_io = six.StringIO()
        call_command(
            "createsuperuser",
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
        new_io = six.StringIO()
        call_command(
            "createsuperuser",
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
        new_io = six.StringIO()
        call_command(
            "createsuperuser",
            interactive=False,
            email="joe@somewhere.org",
            date_of_birth="1976-04-01",
            stdout=new_io,
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
        new_io = six.StringIO()
        with self.assertRaises(CommandError):
            call_command(
                "createsuperuser",
                interactive=False,
                username="joe@somewhere.org",
                stdout=new_io,
                stderr=new_io,
            )

        self.assertEqual(CustomUser._default_manager.count(), 0)

    def test_skip_if_not_in_TTY(self):
        """
        If the command is not called from a TTY, it should be skipped and a
        message should be displayed (#7423).
        """
        class FakeStdin(object):
            """A fake stdin object that has isatty() return False."""
            def isatty(self):
                return False

        out = six.StringIO()
        call_command(
            "createsuperuser",
            stdin=FakeStdin(),
            stdout=out,
            interactive=True,
        )

        self.assertEqual(User._default_manager.count(), 0)
        self.assertIn("Superuser creation skipped", out.getvalue())

    def test_passing_stdin(self):
        """
        You can pass a stdin object as an option and it should be
        available on self.stdin.
        If no such option is passed, it defaults to sys.stdin.
        """
        sentinel = object()
        command = createsuperuser.Command()
        command.check = lambda: []
        command.execute(
            stdin=sentinel,
            stdout=six.StringIO(),
            stderr=six.StringIO(),
            interactive=False,
            verbosity=0,
            username='janet',
            email='janet@example.com',
        )
        self.assertIs(command.stdin, sentinel)

        command = createsuperuser.Command()
        command.check = lambda: []
        command.execute(
            stdout=six.StringIO(),
            stderr=six.StringIO(),
            interactive=False,
            verbosity=0,
            username='joe',
            email='joe@example.com',
        )
        self.assertIs(command.stdin, sys.stdin)

    @override_settings(AUTH_USER_MODEL='auth.CustomUserWithFK')
    def test_fields_with_fk(self):
        new_io = six.StringIO()
        group = Group.objects.create(name='mygroup')
        email = Email.objects.create(email='mymail@gmail.com')
        call_command(
            'createsuperuser',
            interactive=False,
            username=email.pk,
            email=email.email,
            group=group.pk,
            stdout=new_io,
        )
        command_output = new_io.getvalue().strip()
        self.assertEqual(command_output, 'Superuser created successfully.')
        u = CustomUserWithFK._default_manager.get(email=email)
        self.assertEqual(u.username, email)
        self.assertEqual(u.group, group)

        non_existent_email = 'mymail2@gmail.com'
        with self.assertRaisesMessage(CommandError,
                'email instance with email %r does not exist.' % non_existent_email):
            call_command(
                'createsuperuser',
                interactive=False,
                username=email.pk,
                email=non_existent_email,
                stdout=new_io,
            )

    @override_settings(AUTH_USER_MODEL='auth.CustomUserWithFK')
    def test_fields_with_fk_interactive(self):
        new_io = six.StringIO()
        group = Group.objects.create(name='mygroup')
        email = Email.objects.create(email='mymail@gmail.com')

        @mock_inputs({
            'password': 'nopasswd',
            'username (email.id)': email.pk,
            'email (email.email)': email.email,
            'group (group.id)': group.pk,
        })
        def test(self):
            call_command(
                'createsuperuser',
                interactive=True,
                stdout=new_io,
                stdin=MockTTY(),
            )

            command_output = new_io.getvalue().strip()
            self.assertEqual(command_output, 'Superuser created successfully.')
            u = CustomUserWithFK._default_manager.get(email=email)
            self.assertEqual(u.username, email)
            self.assertEqual(u.group, group)

        test(self)


class CustomUserModelValidationTestCase(TestCase):
    @override_settings(AUTH_USER_MODEL='auth.CustomUserNonListRequiredFields')
    @override_system_checks([check_user_model])
    def test_required_fields_is_list(self):
        "REQUIRED_FIELDS should be a list."
        errors = checks.run_checks()
        expected = [
            checks.Error(
                "'REQUIRED_FIELDS' must be a list or tuple.",
                hint=None,
                obj=CustomUserNonListRequiredFields,
                id='auth.E001',
            ),
        ]
        self.assertEqual(errors, expected)

    @override_settings(AUTH_USER_MODEL='auth.CustomUserBadRequiredFields')
    @override_system_checks([check_user_model])
    def test_username_not_in_required_fields(self):
        "USERNAME_FIELD should not appear in REQUIRED_FIELDS."
        errors = checks.run_checks()
        expected = [
            checks.Error(
                ("The field named as the 'USERNAME_FIELD' for a custom user model "
                 "must not be included in 'REQUIRED_FIELDS'."),
                hint=None,
                obj=CustomUserBadRequiredFields,
                id='auth.E002',
            ),
        ]
        self.assertEqual(errors, expected)

    @override_settings(AUTH_USER_MODEL='auth.CustomUserNonUniqueUsername')
    @override_system_checks([check_user_model])
    def test_username_non_unique(self):
        "A non-unique USERNAME_FIELD should raise a model validation error."
        errors = checks.run_checks()
        expected = [
            checks.Error(
                ("'CustomUserNonUniqueUsername.username' must be "
                 "unique because it is named as the 'USERNAME_FIELD'."),
                hint=None,
                obj=CustomUserNonUniqueUsername,
                id='auth.E003',
            ),
        ]
        self.assertEqual(errors, expected)

    @override_settings(AUTH_USER_MODEL='auth.CustomUserNonUniqueUsername',
                       AUTHENTICATION_BACKENDS=[
                           'my.custom.backend',
                       ])
    @override_system_checks([check_user_model])
    def test_username_non_unique_with_custom_backend(self):
        """ A non-unique USERNAME_FIELD should raise an error only if we use the
        default authentication backend. Otherwise, an warning should be raised.
        """
        errors = checks.run_checks()
        expected = [
            checks.Warning(
                ("'CustomUserNonUniqueUsername.username' is named as "
                 "the 'USERNAME_FIELD', but it is not unique."),
                hint=('Ensure that your authentication backend(s) can handle '
                      'non-unique usernames.'),
                obj=CustomUserNonUniqueUsername,
                id='auth.W004',
            )
        ]
        self.assertEqual(errors, expected)


class PermissionTestCase(TestCase):

    def setUp(self):
        self._original_permissions = models.Permission._meta.permissions[:]
        self._original_default_permissions = models.Permission._meta.default_permissions
        self._original_verbose_name = models.Permission._meta.verbose_name

    def tearDown(self):
        models.Permission._meta.permissions = self._original_permissions
        models.Permission._meta.default_permissions = self._original_default_permissions
        models.Permission._meta.verbose_name = self._original_verbose_name
        ContentType.objects.clear_cache()

    def test_duplicated_permissions(self):
        """
        Test that we show proper error message if we are trying to create
        duplicate permissions.
        """
        auth_app_config = apps.get_app_config('auth')

        # check duplicated default permission
        models.Permission._meta.permissions = [
            ('change_permission', 'Can edit permission (duplicate)')]
        six.assertRaisesRegex(self, CommandError,
            "The permission codename 'change_permission' clashes with a "
            "builtin permission for model 'auth.Permission'.",
            create_permissions, auth_app_config, verbosity=0)

        # check duplicated custom permissions
        models.Permission._meta.permissions = [
            ('my_custom_permission', 'Some permission'),
            ('other_one', 'Some other permission'),
            ('my_custom_permission', 'Some permission with duplicate permission code'),
        ]
        six.assertRaisesRegex(self, CommandError,
            "The permission codename 'my_custom_permission' is duplicated for model "
            "'auth.Permission'.",
            create_permissions, auth_app_config, verbosity=0)

        # should not raise anything
        models.Permission._meta.permissions = [
            ('my_custom_permission', 'Some permission'),
            ('other_one', 'Some other permission'),
        ]
        create_permissions(auth_app_config, verbosity=0)

    def test_default_permissions(self):
        auth_app_config = apps.get_app_config('auth')

        permission_content_type = ContentType.objects.get_by_natural_key('auth', 'permission')
        models.Permission._meta.permissions = [
            ('my_custom_permission', 'Some permission'),
        ]
        create_permissions(auth_app_config, verbosity=0)

        # add/change/delete permission by default + custom permission
        self.assertEqual(models.Permission.objects.filter(
            content_type=permission_content_type,
        ).count(), 4)

        models.Permission.objects.filter(content_type=permission_content_type).delete()
        models.Permission._meta.default_permissions = []
        create_permissions(auth_app_config, verbosity=0)

        # custom permission only since default permissions is empty
        self.assertEqual(models.Permission.objects.filter(
            content_type=permission_content_type,
        ).count(), 1)

    def test_verbose_name_length(self):
        auth_app_config = apps.get_app_config('auth')

        permission_content_type = ContentType.objects.get_by_natural_key('auth', 'permission')
        models.Permission.objects.filter(content_type=permission_content_type).delete()
        models.Permission._meta.verbose_name = "some ridiculously long verbose name that is out of control" * 5

        six.assertRaisesRegex(self, exceptions.ValidationError,
            "The verbose_name of auth.permission is longer than 244 characters",
            create_permissions, auth_app_config, verbosity=0)
