import builtins
import getpass
import sys
from datetime import date
from io import StringIO
from unittest import mock

from django.apps import apps
from django.contrib.auth import management
from django.contrib.auth.management import (
    create_permissions, get_default_username,
)
from django.contrib.auth.management.commands import (
    changepassword, createsuperuser,
)
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import migrations
from django.test import TestCase, override_settings
from django.utils.translation import gettext_lazy as _

from .models import (
    CustomUser, CustomUserNonUniqueUsername, CustomUserWithFK, Email,
)

MOCK_INPUT_KEY_TO_PROMPTS = {
    # @mock_inputs dict key: [expected prompt messages],
    'bypass': ['Bypass password validation and create user anyway? [y/N]: '],
    'email': ['Email address: '],
    'username': ['Username: ', lambda: "Username (leave blank to use '%s'): " % get_default_username()],
}


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
                    if callable(inputs['password']):
                        return inputs['password']()
                    return inputs['password']

            def mock_input(prompt):
                assert '__proxy__' not in prompt
                response = None
                for key, val in inputs.items():
                    if val == 'KeyboardInterrupt':
                        raise KeyboardInterrupt
                    # get() fallback because sometimes 'key' is the actual
                    # prompt rather than a shortcut name.
                    prompt_msgs = MOCK_INPUT_KEY_TO_PROMPTS.get(key, key)
                    if isinstance(prompt_msgs, list):
                        prompt_msgs = [msg() if callable(msg) else msg for msg in prompt_msgs]
                    if prompt in prompt_msgs:
                        if callable(val):
                            response = val()
                        else:
                            response = val
                        break
                if response is None:
                    raise ValueError('Mock input for %r not found.' % prompt)
                return response

            old_getpass = createsuperuser.getpass
            old_input = builtins.input
            createsuperuser.getpass = mock_getpass
            builtins.input = mock_input
            try:
                test_func(*args)
            finally:
                createsuperuser.getpass = old_getpass
                builtins.input = old_input
        return wrapped
    return inner


class MockTTY:
    """
    A fake stdin object that pretends to be a TTY to be used in conjunction
    with mock_inputs.
    """
    def isatty(self):
        return True


class MockInputTests(TestCase):
    @mock_inputs({'username': 'alice'})
    def test_input_not_found(self):
        with self.assertRaisesMessage(ValueError, "Mock input for 'Email address: ' not found."):
            call_command('createsuperuser', stdin=MockTTY())


class GetDefaultUsernameTestCase(TestCase):

    def setUp(self):
        self.old_get_system_username = management.get_system_username

    def tearDown(self):
        management.get_system_username = self.old_get_system_username

    def test_actual_implementation(self):
        self.assertIsInstance(management.get_system_username(), str)

    def test_simple(self):
        management.get_system_username = lambda: 'joe'
        self.assertEqual(management.get_default_username(), 'joe')

    def test_existing(self):
        User.objects.create(username='joe')
        management.get_system_username = lambda: 'joe'
        self.assertEqual(management.get_default_username(), '')
        self.assertEqual(
            management.get_default_username(check_db=False), 'joe')

    def test_i18n(self):
        # 'Julia' with accented 'u':
        management.get_system_username = lambda: 'J\xfalia'
        self.assertEqual(management.get_default_username(), 'julia')


@override_settings(AUTH_PASSWORD_VALIDATORS=[
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
])
class ChangepasswordManagementCommandTestCase(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='joe', password='qwerty')
        self.stdout = StringIO()
        self.stderr = StringIO()

    def tearDown(self):
        self.stdout.close()
        self.stderr.close()

    @mock.patch.object(getpass, 'getpass', return_value='password')
    def test_get_pass(self, mock_get_pass):
        call_command('changepassword', username='joe', stdout=self.stdout)
        self.assertIs(User.objects.get(username='joe').check_password('password'), True)

    @mock.patch.object(getpass, 'getpass', return_value='')
    def test_get_pass_no_input(self, mock_get_pass):
        with self.assertRaisesMessage(CommandError, 'aborted'):
            call_command('changepassword', username='joe', stdout=self.stdout)

    @mock.patch.object(changepassword.Command, '_get_pass', return_value='new_password')
    def test_system_username(self, mock_get_pass):
        """The system username is used if --username isn't provided."""
        username = getpass.getuser()
        User.objects.create_user(username=username, password='qwerty')
        call_command('changepassword', stdout=self.stdout)
        self.assertIs(User.objects.get(username=username).check_password('new_password'), True)

    def test_nonexistent_username(self):
        with self.assertRaisesMessage(CommandError, "user 'test' does not exist"):
            call_command('changepassword', username='test', stdout=self.stdout)

    @mock.patch.object(changepassword.Command, '_get_pass', return_value='not qwerty')
    def test_that_changepassword_command_changes_joes_password(self, mock_get_pass):
        "Executing the changepassword management command should change joe's password"
        self.assertTrue(self.user.check_password('qwerty'))

        call_command('changepassword', username='joe', stdout=self.stdout)
        command_output = self.stdout.getvalue().strip()

        self.assertEqual(
            command_output,
            "Changing password for user 'joe'\nPassword changed successfully for user 'joe'"
        )
        self.assertTrue(User.objects.get(username="joe").check_password("not qwerty"))

    @mock.patch.object(changepassword.Command, '_get_pass', side_effect=lambda *args: str(args))
    def test_that_max_tries_exits_1(self, mock_get_pass):
        """
        A CommandError should be thrown by handle() if the user enters in
        mismatched passwords three times.
        """
        msg = "Aborting password change for user 'joe' after 3 attempts"
        with self.assertRaisesMessage(CommandError, msg):
            call_command('changepassword', username='joe', stdout=self.stdout, stderr=self.stderr)

    @mock.patch.object(changepassword.Command, '_get_pass', return_value='1234567890')
    def test_password_validation(self, mock_get_pass):
        """
        A CommandError should be raised if the user enters in passwords which
        fail validation three times.
        """
        abort_msg = "Aborting password change for user 'joe' after 3 attempts"
        with self.assertRaisesMessage(CommandError, abort_msg):
            call_command('changepassword', username='joe', stdout=self.stdout, stderr=self.stderr)
        self.assertIn('This password is entirely numeric.', self.stderr.getvalue())

    @mock.patch.object(changepassword.Command, '_get_pass', return_value='not qwerty')
    def test_that_changepassword_command_works_with_nonascii_output(self, mock_get_pass):
        """
        #21627 -- Executing the changepassword management command should allow
        non-ASCII characters from the User object representation.
        """
        # 'Julia' with accented 'u':
        User.objects.create_user(username='J\xfalia', password='qwerty')
        call_command('changepassword', username='J\xfalia', stdout=self.stdout)


class MultiDBChangepasswordManagementCommandTestCase(TestCase):
    multi_db = True

    @mock.patch.object(changepassword.Command, '_get_pass', return_value='not qwerty')
    def test_that_changepassword_command_with_database_option_uses_given_db(self, mock_get_pass):
        """
        changepassword --database should operate on the specified DB.
        """
        user = User.objects.db_manager('other').create_user(username='joe', password='qwerty')
        self.assertTrue(user.check_password('qwerty'))

        out = StringIO()
        call_command('changepassword', username='joe', database='other', stdout=out)
        command_output = out.getvalue().strip()

        self.assertEqual(
            command_output,
            "Changing password for user 'joe'\nPassword changed successfully for user 'joe'"
        )
        self.assertTrue(User.objects.using('other').get(username="joe").check_password('not qwerty'))


@override_settings(
    SILENCED_SYSTEM_CHECKS=['fields.W342'],  # ForeignKey(unique=True)
    AUTH_PASSWORD_VALIDATORS=[{'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'}],
)
class CreatesuperuserManagementCommandTestCase(TestCase):

    def test_no_email_argument(self):
        new_io = StringIO()
        with self.assertRaisesMessage(CommandError, 'You must use --email with --noinput.'):
            call_command('createsuperuser', interactive=False, username='joe', stdout=new_io)

    def test_basic_usage(self):
        "Check the operation of the createsuperuser management command"
        # We can use the management command to create a superuser
        new_io = StringIO()
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

    def test_non_ascii_verbose_name(self):
        @mock_inputs({
            'password': "nopasswd",
            "Uživatel (leave blank to use '%s'): " % get_default_username(): 'foo',  # username (cz)
            'email': 'nolocale@somewhere.org',
        })
        def test(self):
            username_field = User._meta.get_field('username')
            old_verbose_name = username_field.verbose_name
            username_field.verbose_name = _('u\u017eivatel')
            new_io = StringIO()
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

        test(self)

    def test_verbosity_zero(self):
        # We can suppress output on the management command
        new_io = StringIO()
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
        new_io = StringIO()
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

    @override_settings(AUTH_USER_MODEL='auth_tests.CustomUser')
    def test_swappable_user(self):
        "A superuser can be created when a custom user model is in use"
        # We can use the management command to create a superuser
        # We skip validation because the temporary substitution of the
        # swappable User model messes with validation.
        new_io = StringIO()
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

    @override_settings(AUTH_USER_MODEL='auth_tests.CustomUser')
    def test_swappable_user_missing_required_field(self):
        "A Custom superuser won't be created when a required field isn't provided"
        # We can use the management command to create a superuser
        # We skip validation because the temporary substitution of the
        # swappable User model messes with validation.
        new_io = StringIO()
        with self.assertRaisesMessage(CommandError, 'You must use --email with --noinput.'):
            call_command(
                "createsuperuser",
                interactive=False,
                stdout=new_io,
                stderr=new_io,
            )

        self.assertEqual(CustomUser._default_manager.count(), 0)

    @override_settings(
        AUTH_USER_MODEL='auth_tests.CustomUserNonUniqueUsername',
        AUTHENTICATION_BACKENDS=['my.custom.backend'],
    )
    def test_swappable_user_username_non_unique(self):
        @mock_inputs({
            'username': 'joe',
            'password': 'nopasswd',
        })
        def createsuperuser():
            new_io = StringIO()
            call_command(
                "createsuperuser",
                interactive=True,
                email="joe@somewhere.org",
                stdout=new_io,
                stdin=MockTTY(),
            )
            command_output = new_io.getvalue().strip()
            self.assertEqual(command_output, 'Superuser created successfully.')

        for i in range(2):
            createsuperuser()

        users = CustomUserNonUniqueUsername.objects.filter(username="joe")
        self.assertEqual(users.count(), 2)

    def test_skip_if_not_in_TTY(self):
        """
        If the command is not called from a TTY, it should be skipped and a
        message should be displayed (#7423).
        """
        class FakeStdin:
            """A fake stdin object that has isatty() return False."""
            def isatty(self):
                return False

        out = StringIO()
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
        call_command(
            command,
            stdin=sentinel,
            stdout=StringIO(),
            stderr=StringIO(),
            interactive=False,
            verbosity=0,
            username='janet',
            email='janet@example.com',
        )
        self.assertIs(command.stdin, sentinel)

        command = createsuperuser.Command()
        call_command(
            command,
            stdout=StringIO(),
            stderr=StringIO(),
            interactive=False,
            verbosity=0,
            username='joe',
            email='joe@example.com',
        )
        self.assertIs(command.stdin, sys.stdin)

    @override_settings(AUTH_USER_MODEL='auth_tests.CustomUserWithFK')
    def test_fields_with_fk(self):
        new_io = StringIO()
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
        msg = 'email instance with email %r does not exist.' % non_existent_email
        with self.assertRaisesMessage(CommandError, msg):
            call_command(
                'createsuperuser',
                interactive=False,
                username=email.pk,
                email=non_existent_email,
                stdout=new_io,
            )

    @override_settings(AUTH_USER_MODEL='auth_tests.CustomUserWithFK')
    def test_fields_with_fk_interactive(self):
        new_io = StringIO()
        group = Group.objects.create(name='mygroup')
        email = Email.objects.create(email='mymail@gmail.com')

        @mock_inputs({
            'password': 'nopasswd',
            'Username (Email.id): ': email.pk,
            'Email (Email.email): ': email.email,
            'Group (Group.id): ': group.pk,
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

    def test_default_username(self):
        """createsuperuser uses a default username when one isn't provided."""
        # Get the default username before creating a user.
        default_username = get_default_username()
        new_io = StringIO()
        entered_passwords = ['password', 'password']

        def return_passwords():
            return entered_passwords.pop(0)

        @mock_inputs({'password': return_passwords, 'username': '', 'email': ''})
        def test(self):
            call_command(
                'createsuperuser',
                interactive=True,
                stdin=MockTTY(),
                stdout=new_io,
                stderr=new_io,
            )
            self.assertEqual(new_io.getvalue().strip(), 'Superuser created successfully.')
            self.assertTrue(User.objects.filter(username=default_username).exists())

        test(self)

    def test_password_validation(self):
        """
        Creation should fail if the password fails validation.
        """
        new_io = StringIO()

        # Returns '1234567890' the first two times it is called, then
        # 'password' subsequently.
        def bad_then_good_password(index=[0]):
            index[0] += 1
            if index[0] <= 2:
                return '1234567890'
            return 'password'

        @mock_inputs({
            'password': bad_then_good_password,
            'username': 'joe1234567890',
            'email': '',
            'bypass': 'n',
        })
        def test(self):
            call_command(
                "createsuperuser",
                interactive=True,
                stdin=MockTTY(),
                stdout=new_io,
                stderr=new_io,
            )
            self.assertEqual(
                new_io.getvalue().strip(),
                "This password is entirely numeric.\n"
                "Superuser created successfully."
            )

        test(self)

    def test_blank_username(self):
        """Creation fails if --username is blank."""
        new_io = StringIO()

        def test(self):
            with self.assertRaisesMessage(CommandError, 'Username cannot be blank.'):
                call_command(
                    'createsuperuser',
                    username='',
                    stdin=MockTTY(),
                    stdout=new_io,
                    stderr=new_io,
                )

        test(self)

    def test_blank_username_non_interactive(self):
        new_io = StringIO()

        def test(self):
            with self.assertRaisesMessage(CommandError, 'Username cannot be blank.'):
                call_command(
                    'createsuperuser',
                    username='',
                    interactive=False,
                    stdin=MockTTY(),
                    stdout=new_io,
                    stderr=new_io,
                )

        test(self)

    def test_password_validation_bypass(self):
        """
        Password validation can be bypassed by entering 'y' at the prompt.
        """
        new_io = StringIO()

        @mock_inputs({
            'password': '1234567890',
            'username': 'joe1234567890',
            'email': '',
            'bypass': 'y',
        })
        def test(self):
            call_command(
                'createsuperuser',
                interactive=True,
                stdin=MockTTY(),
                stdout=new_io,
                stderr=new_io,
            )
            self.assertEqual(
                new_io.getvalue().strip(),
                'This password is entirely numeric.\n'
                'Superuser created successfully.'
            )

        test(self)

    def test_invalid_username(self):
        """Creation fails if the username fails validation."""
        user_field = User._meta.get_field(User.USERNAME_FIELD)
        new_io = StringIO()
        entered_passwords = ['password', 'password']
        # Enter an invalid (too long) username first and then a valid one.
        invalid_username = ('x' * user_field.max_length) + 'y'
        entered_usernames = [invalid_username, 'janet']

        def return_passwords():
            return entered_passwords.pop(0)

        def return_usernames():
            return entered_usernames.pop(0)

        @mock_inputs({'password': return_passwords, 'username': return_usernames, 'email': ''})
        def test(self):
            call_command(
                'createsuperuser',
                interactive=True,
                stdin=MockTTY(),
                stdout=new_io,
                stderr=new_io,
            )
            self.assertEqual(
                new_io.getvalue().strip(),
                'Error: Ensure this value has at most %s characters (it has %s).\n'
                'Superuser created successfully.' % (user_field.max_length, len(invalid_username))
            )

        test(self)

    @mock_inputs({'username': 'KeyboardInterrupt'})
    def test_keyboard_interrupt(self):
        new_io = StringIO()
        with self.assertRaises(SystemExit):
            call_command(
                'createsuperuser',
                interactive=True,
                stdin=MockTTY(),
                stdout=new_io,
                stderr=new_io,
            )
        self.assertEqual(new_io.getvalue(), '\nOperation cancelled.\n')

    def test_existing_username(self):
        """Creation fails if the username already exists."""
        user = User.objects.create(username='janet')
        new_io = StringIO()
        entered_passwords = ['password', 'password']
        # Enter the existing username first and then a new one.
        entered_usernames = [user.username, 'joe']

        def return_passwords():
            return entered_passwords.pop(0)

        def return_usernames():
            return entered_usernames.pop(0)

        @mock_inputs({'password': return_passwords, 'username': return_usernames, 'email': ''})
        def test(self):
            call_command(
                'createsuperuser',
                interactive=True,
                stdin=MockTTY(),
                stdout=new_io,
                stderr=new_io,
            )
            self.assertEqual(
                new_io.getvalue().strip(),
                'Error: That username is already taken.\n'
                'Superuser created successfully.'
            )

        test(self)

    def test_existing_username_non_interactive(self):
        """Creation fails if the username already exists."""
        User.objects.create(username='janet')
        new_io = StringIO()
        with self.assertRaisesMessage(CommandError, "Error: That username is already taken."):
            call_command(
                'createsuperuser',
                username='janet',
                email='',
                interactive=False,
                stdout=new_io,
            )

    def test_validation_mismatched_passwords(self):
        """
        Creation should fail if the user enters mismatched passwords.
        """
        new_io = StringIO()

        # The first two passwords do not match, but the second two do match and
        # are valid.
        entered_passwords = ["password", "not password", "password2", "password2"]

        def mismatched_passwords_then_matched():
            return entered_passwords.pop(0)

        @mock_inputs({
            'password': mismatched_passwords_then_matched,
            'username': 'joe1234567890',
            'email': '',
        })
        def test(self):
            call_command(
                "createsuperuser",
                interactive=True,
                stdin=MockTTY(),
                stdout=new_io,
                stderr=new_io,
            )
            self.assertEqual(
                new_io.getvalue().strip(),
                "Error: Your passwords didn't match.\n"
                "Superuser created successfully."
            )

        test(self)

    def test_validation_blank_password_entered(self):
        """
        Creation should fail if the user enters blank passwords.
        """
        new_io = StringIO()

        # The first two passwords are empty strings, but the second two are
        # valid.
        entered_passwords = ["", "", "password2", "password2"]

        def blank_passwords_then_valid():
            return entered_passwords.pop(0)

        @mock_inputs({
            'password': blank_passwords_then_valid,
            'username': 'joe1234567890',
            'email': '',
        })
        def test(self):
            call_command(
                "createsuperuser",
                interactive=True,
                stdin=MockTTY(),
                stdout=new_io,
                stderr=new_io,
            )
            self.assertEqual(
                new_io.getvalue().strip(),
                "Error: Blank passwords aren't allowed.\n"
                "Superuser created successfully."
            )

        test(self)


class MultiDBCreatesuperuserTestCase(TestCase):
    multi_db = True

    def test_createsuperuser_command_with_database_option(self):
        """
        changepassword --database should operate on the specified DB.
        """
        new_io = StringIO()
        call_command(
            'createsuperuser',
            interactive=False,
            username='joe',
            email='joe@somewhere.org',
            database='other',
            stdout=new_io,
        )
        command_output = new_io.getvalue().strip()
        self.assertEqual(command_output, 'Superuser created successfully.')
        user = User.objects.using('other').get(username='joe')
        self.assertEqual(user.email, 'joe@somewhere.org')


class CreatePermissionsTests(TestCase):

    def setUp(self):
        self._original_permissions = Permission._meta.permissions[:]
        self._original_default_permissions = Permission._meta.default_permissions
        self.app_config = apps.get_app_config('auth')

    def tearDown(self):
        Permission._meta.permissions = self._original_permissions
        Permission._meta.default_permissions = self._original_default_permissions
        ContentType.objects.clear_cache()

    def test_default_permissions(self):
        permission_content_type = ContentType.objects.get_by_natural_key('auth', 'permission')
        Permission._meta.permissions = [
            ('my_custom_permission', 'Some permission'),
        ]
        create_permissions(self.app_config, verbosity=0)

        # view/add/change/delete permission by default + custom permission
        self.assertEqual(Permission.objects.filter(
            content_type=permission_content_type,
        ).count(), 5)

        Permission.objects.filter(content_type=permission_content_type).delete()
        Permission._meta.default_permissions = []
        create_permissions(self.app_config, verbosity=0)

        # custom permission only since default permissions is empty
        self.assertEqual(Permission.objects.filter(
            content_type=permission_content_type,
        ).count(), 1)

    def test_unavailable_models(self):
        """
        #24075 - Permissions shouldn't be created or deleted if the ContentType
        or Permission models aren't available.
        """
        state = migrations.state.ProjectState()
        # Unavailable contenttypes.ContentType
        with self.assertNumQueries(0):
            create_permissions(self.app_config, verbosity=0, apps=state.apps)
        # Unavailable auth.Permission
        state = migrations.state.ProjectState(real_apps=['contenttypes'])
        with self.assertNumQueries(0):
            create_permissions(self.app_config, verbosity=0, apps=state.apps)
