import builtins
import getpass
import os
import sys
from datetime import date
from io import StringIO
from unittest import mock

from django.apps import apps
from django.contrib.auth import get_permission_codename, management
from django.contrib.auth.management import create_permissions, get_default_username
from django.contrib.auth.management.commands import changepassword, createsuperuser
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import migrations
from django.test import TestCase, override_settings
from django.utils.translation import gettext_lazy as _

from .models import (
    CustomUser,
    CustomUserNonUniqueUsername,
    CustomUserWithFK,
    CustomUserWithM2M,
    CustomUserWithUniqueConstraint,
    Email,
    Organization,
    UserProxy,
)

MOCK_INPUT_KEY_TO_PROMPTS = {
    # @mock_inputs dict key: [expected prompt messages],
    "bypass": ["Bypass password validation and create user anyway? [y/N]: "],
    "email": ["Email address: "],
    "date_of_birth": ["Date of birth: "],
    "first_name": ["First name: "],
    "username": [
        "Username: ",
        lambda: "Username (leave blank to use '%s'): " % get_default_username(),
    ],
}


def mock_inputs(inputs):
    """
    Decorator to temporarily replace input/getpass to allow interactive
    createsuperuser.
    """

    def inner(test_func):
        def wrapper(*args):
            class mock_getpass:
                @staticmethod
                def getpass(prompt=b"Password: ", stream=None):
                    if callable(inputs["password"]):
                        return inputs["password"]()
                    return inputs["password"]

            def mock_input(prompt):
                assert "__proxy__" not in prompt
                response = None
                for key, val in inputs.items():
                    if val == "KeyboardInterrupt":
                        raise KeyboardInterrupt
                    # get() fallback because sometimes 'key' is the actual
                    # prompt rather than a shortcut name.
                    prompt_msgs = MOCK_INPUT_KEY_TO_PROMPTS.get(key, key)
                    if isinstance(prompt_msgs, list):
                        prompt_msgs = [
                            msg() if callable(msg) else msg for msg in prompt_msgs
                        ]
                    if prompt in prompt_msgs:
                        if callable(val):
                            response = val()
                        else:
                            response = val
                        break
                if response is None:
                    raise ValueError("Mock input for %r not found." % prompt)
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

        return wrapper

    return inner


class MockTTY:
    """
    A fake stdin object that pretends to be a TTY to be used in conjunction
    with mock_inputs.
    """

    def isatty(self):
        return True


class MockInputTests(TestCase):
    @mock_inputs({"username": "alice"})
    def test_input_not_found(self):
        with self.assertRaisesMessage(
            ValueError, "Mock input for 'Email address: ' not found."
        ):
            call_command("createsuperuser", stdin=MockTTY())


class GetDefaultUsernameTestCase(TestCase):
    databases = {"default", "other"}

    def setUp(self):
        self.old_get_system_username = management.get_system_username

    def tearDown(self):
        management.get_system_username = self.old_get_system_username

    def test_actual_implementation(self):
        self.assertIsInstance(management.get_system_username(), str)

    def test_simple(self):
        management.get_system_username = lambda: "joe"
        self.assertEqual(management.get_default_username(), "joe")

    def test_existing(self):
        User.objects.create(username="joe")
        management.get_system_username = lambda: "joe"
        self.assertEqual(management.get_default_username(), "")
        self.assertEqual(management.get_default_username(check_db=False), "joe")

    def test_i18n(self):
        # 'Julia' with accented 'u':
        management.get_system_username = lambda: "J\xfalia"
        self.assertEqual(management.get_default_username(), "julia")

    def test_with_database(self):
        User.objects.create(username="joe")
        management.get_system_username = lambda: "joe"
        self.assertEqual(management.get_default_username(), "")
        self.assertEqual(management.get_default_username(database="other"), "joe")

        User.objects.using("other").create(username="joe")
        self.assertEqual(management.get_default_username(database="other"), "")


@override_settings(
    AUTH_PASSWORD_VALIDATORS=[
        {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
    ]
)
class ChangepasswordManagementCommandTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="joe", password="qwerty")

    def setUp(self):
        self.stdout = StringIO()
        self.stderr = StringIO()

    def tearDown(self):
        self.stdout.close()
        self.stderr.close()

    @mock.patch.object(getpass, "getpass", return_value="password")
    def test_get_pass(self, mock_get_pass):
        call_command("changepassword", username="joe", stdout=self.stdout)
        self.assertIs(User.objects.get(username="joe").check_password("password"), True)

    @mock.patch.object(getpass, "getpass", return_value="")
    def test_get_pass_no_input(self, mock_get_pass):
        with self.assertRaisesMessage(CommandError, "aborted"):
            call_command("changepassword", username="joe", stdout=self.stdout)

    @mock.patch.object(changepassword.Command, "_get_pass", return_value="new_password")
    def test_system_username(self, mock_get_pass):
        """The system username is used if --username isn't provided."""
        username = getpass.getuser()
        User.objects.create_user(username=username, password="qwerty")
        call_command("changepassword", stdout=self.stdout)
        self.assertIs(
            User.objects.get(username=username).check_password("new_password"), True
        )

    def test_nonexistent_username(self):
        with self.assertRaisesMessage(CommandError, "user 'test' does not exist"):
            call_command("changepassword", username="test", stdout=self.stdout)

    @mock.patch.object(changepassword.Command, "_get_pass", return_value="not qwerty")
    def test_that_changepassword_command_changes_joes_password(self, mock_get_pass):
        "Executing the changepassword management command should change joe's password"
        self.assertTrue(self.user.check_password("qwerty"))

        call_command("changepassword", username="joe", stdout=self.stdout)
        command_output = self.stdout.getvalue().strip()

        self.assertEqual(
            command_output,
            "Changing password for user 'joe'\n"
            "Password changed successfully for user 'joe'",
        )
        self.assertTrue(User.objects.get(username="joe").check_password("not qwerty"))

    @mock.patch.object(
        changepassword.Command, "_get_pass", side_effect=lambda *args: str(args)
    )
    def test_that_max_tries_exits_1(self, mock_get_pass):
        """
        A CommandError should be thrown by handle() if the user enters in
        mismatched passwords three times.
        """
        msg = "Aborting password change for user 'joe' after 3 attempts"
        with self.assertRaisesMessage(CommandError, msg):
            call_command(
                "changepassword", username="joe", stdout=self.stdout, stderr=self.stderr
            )

    @mock.patch.object(changepassword.Command, "_get_pass", return_value="1234567890")
    def test_password_validation(self, mock_get_pass):
        """
        A CommandError should be raised if the user enters in passwords which
        fail validation three times.
        """
        abort_msg = "Aborting password change for user 'joe' after 3 attempts"
        with self.assertRaisesMessage(CommandError, abort_msg):
            call_command(
                "changepassword", username="joe", stdout=self.stdout, stderr=self.stderr
            )
        self.assertIn("This password is entirely numeric.", self.stderr.getvalue())

    @mock.patch.object(changepassword.Command, "_get_pass", return_value="not qwerty")
    def test_that_changepassword_command_works_with_nonascii_output(
        self, mock_get_pass
    ):
        """
        #21627 -- Executing the changepassword management command should allow
        non-ASCII characters from the User object representation.
        """
        # 'Julia' with accented 'u':
        User.objects.create_user(username="J\xfalia", password="qwerty")
        call_command("changepassword", username="J\xfalia", stdout=self.stdout)


class MultiDBChangepasswordManagementCommandTestCase(TestCase):
    databases = {"default", "other"}

    @mock.patch.object(changepassword.Command, "_get_pass", return_value="not qwerty")
    def test_that_changepassword_command_with_database_option_uses_given_db(
        self, mock_get_pass
    ):
        """
        changepassword --database should operate on the specified DB.
        """
        user = User.objects.db_manager("other").create_user(
            username="joe", password="qwerty"
        )
        self.assertTrue(user.check_password("qwerty"))

        out = StringIO()
        call_command("changepassword", username="joe", database="other", stdout=out)
        command_output = out.getvalue().strip()

        self.assertEqual(
            command_output,
            "Changing password for user 'joe'\n"
            "Password changed successfully for user 'joe'",
        )
        self.assertTrue(
            User.objects.using("other").get(username="joe").check_password("not qwerty")
        )


@override_settings(
    SILENCED_SYSTEM_CHECKS=["fields.W342"],  # ForeignKey(unique=True)
    AUTH_PASSWORD_VALIDATORS=[
        {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"}
    ],
)
class CreatesuperuserManagementCommandTestCase(TestCase):
    def test_no_email_argument(self):
        new_io = StringIO()
        with self.assertRaisesMessage(
            CommandError, "You must use --email with --noinput."
        ):
            call_command(
                "createsuperuser", interactive=False, username="joe", stdout=new_io
            )

    def test_basic_usage(self):
        "Check the operation of the createsuperuser management command"
        # We can use the management command to create a superuser
        new_io = StringIO()
        call_command(
            "createsuperuser",
            interactive=False,
            username="joe",
            email="joe@somewhere.org",
            stdout=new_io,
        )
        command_output = new_io.getvalue().strip()
        self.assertEqual(command_output, "Superuser created successfully.")
        u = User.objects.get(username="joe")
        self.assertEqual(u.email, "joe@somewhere.org")

        # created password should be unusable
        self.assertFalse(u.has_usable_password())

    def test_validate_username(self):
        msg = (
            "Enter a valid username. This value may contain only letters, numbers, "
            "and @/./+/-/_ characters."
        )
        with self.assertRaisesMessage(CommandError, msg):
            call_command(
                "createsuperuser",
                interactive=False,
                username="🤠",
                email="joe@somewhere.org",
            )

    def test_non_ascii_verbose_name(self):
        @mock_inputs(
            {
                "password": "nopasswd",
                "Uživatel (leave blank to use '%s'): "
                % get_default_username(): "foo",  # username (cz)
                "email": "nolocale@somewhere.org",
            }
        )
        def test(self):
            username_field = User._meta.get_field("username")
            old_verbose_name = username_field.verbose_name
            username_field.verbose_name = _("u\u017eivatel")
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
            self.assertEqual(command_output, "Superuser created successfully.")

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
            stdout=new_io,
        )
        command_output = new_io.getvalue().strip()
        self.assertEqual(command_output, "")
        u = User.objects.get(username="joe2")
        self.assertEqual(u.email, "joe2@somewhere.org")
        self.assertFalse(u.has_usable_password())

    def test_email_in_username(self):
        call_command(
            "createsuperuser",
            interactive=False,
            username="joe+admin@somewhere.org",
            email="joe@somewhere.org",
            verbosity=0,
        )
        u = User._default_manager.get(username="joe+admin@somewhere.org")
        self.assertEqual(u.email, "joe@somewhere.org")
        self.assertFalse(u.has_usable_password())

    @override_settings(AUTH_USER_MODEL="auth_tests.CustomUser")
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
            first_name="Joe",
            stdout=new_io,
        )
        command_output = new_io.getvalue().strip()
        self.assertEqual(command_output, "Superuser created successfully.")
        u = CustomUser._default_manager.get(email="joe@somewhere.org")
        self.assertEqual(u.date_of_birth, date(1976, 4, 1))

        # created password should be unusable
        self.assertFalse(u.has_usable_password())

    @override_settings(AUTH_USER_MODEL="auth_tests.CustomUser")
    def test_swappable_user_missing_required_field(self):
        "A Custom superuser won't be created when a required field isn't provided"
        # We can use the management command to create a superuser
        # We skip validation because the temporary substitution of the
        # swappable User model messes with validation.
        new_io = StringIO()
        with self.assertRaisesMessage(
            CommandError, "You must use --email with --noinput."
        ):
            call_command(
                "createsuperuser",
                interactive=False,
                stdout=new_io,
                stderr=new_io,
            )

        self.assertEqual(CustomUser._default_manager.count(), 0)

    @override_settings(
        AUTH_USER_MODEL="auth_tests.CustomUserNonUniqueUsername",
        AUTHENTICATION_BACKENDS=["my.custom.backend"],
    )
    def test_swappable_user_username_non_unique(self):
        @mock_inputs(
            {
                "username": "joe",
                "password": "nopasswd",
            }
        )
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
            self.assertEqual(command_output, "Superuser created successfully.")

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
            interactive=False,
            verbosity=0,
            username="janet",
            email="janet@example.com",
        )
        self.assertIs(command.stdin, sentinel)

        command = createsuperuser.Command()
        call_command(
            command,
            interactive=False,
            verbosity=0,
            username="joe",
            email="joe@example.com",
        )
        self.assertIs(command.stdin, sys.stdin)

    @override_settings(AUTH_USER_MODEL="auth_tests.CustomUserWithFK")
    def test_fields_with_fk(self):
        new_io = StringIO()
        group = Group.objects.create(name="mygroup")
        email = Email.objects.create(email="mymail@gmail.com")
        call_command(
            "createsuperuser",
            interactive=False,
            username=email.pk,
            email=email.email,
            group=group.pk,
            stdout=new_io,
        )
        command_output = new_io.getvalue().strip()
        self.assertEqual(command_output, "Superuser created successfully.")
        u = CustomUserWithFK._default_manager.get(email=email)
        self.assertEqual(u.username, email)
        self.assertEqual(u.group, group)

        non_existent_email = "mymail2@gmail.com"
        msg = "email instance with email %r does not exist." % non_existent_email
        with self.assertRaisesMessage(CommandError, msg):
            call_command(
                "createsuperuser",
                interactive=False,
                username=email.pk,
                email=non_existent_email,
                stdout=new_io,
            )

    @override_settings(AUTH_USER_MODEL="auth_tests.CustomUserWithFK")
    def test_fields_with_fk_interactive(self):
        new_io = StringIO()
        group = Group.objects.create(name="mygroup")
        email = Email.objects.create(email="mymail@gmail.com")

        @mock_inputs(
            {
                "password": "nopasswd",
                "Username (Email.id): ": email.pk,
                "Email (Email.email): ": email.email,
                "Group (Group.id): ": group.pk,
            }
        )
        def test(self):
            call_command(
                "createsuperuser",
                interactive=True,
                stdout=new_io,
                stdin=MockTTY(),
            )

            command_output = new_io.getvalue().strip()
            self.assertEqual(command_output, "Superuser created successfully.")
            u = CustomUserWithFK._default_manager.get(email=email)
            self.assertEqual(u.username, email)
            self.assertEqual(u.group, group)

        test(self)

    @override_settings(AUTH_USER_MODEL="auth_tests.CustomUserWithFK")
    def test_fields_with_fk_via_option_interactive(self):
        new_io = StringIO()
        group = Group.objects.create(name="mygroup")
        email = Email.objects.create(email="mymail@gmail.com")

        @mock_inputs({"password": "nopasswd"})
        def test(self):
            call_command(
                "createsuperuser",
                interactive=True,
                username=email.pk,
                email=email.email,
                group=group.pk,
                stdout=new_io,
                stdin=MockTTY(),
            )

            command_output = new_io.getvalue().strip()
            self.assertEqual(command_output, "Superuser created successfully.")
            u = CustomUserWithFK._default_manager.get(email=email)
            self.assertEqual(u.username, email)
            self.assertEqual(u.group, group)

        test(self)

    @override_settings(AUTH_USER_MODEL="auth_tests.CustomUserWithFK")
    def test_validate_fk(self):
        email = Email.objects.create(email="mymail@gmail.com")
        Group.objects.all().delete()
        nonexistent_group_id = 1
        msg = f"group instance with id {nonexistent_group_id} does not exist."

        with self.assertRaisesMessage(CommandError, msg):
            call_command(
                "createsuperuser",
                interactive=False,
                username=email.pk,
                email=email.email,
                group=nonexistent_group_id,
                verbosity=0,
            )

    @override_settings(AUTH_USER_MODEL="auth_tests.CustomUserWithFK")
    def test_validate_fk_environment_variable(self):
        email = Email.objects.create(email="mymail@gmail.com")
        Group.objects.all().delete()
        nonexistent_group_id = 1
        msg = f"group instance with id {nonexistent_group_id} does not exist."

        with mock.patch.dict(
            os.environ,
            {"DJANGO_SUPERUSER_GROUP": str(nonexistent_group_id)},
        ):
            with self.assertRaisesMessage(CommandError, msg):
                call_command(
                    "createsuperuser",
                    interactive=False,
                    username=email.pk,
                    email=email.email,
                    verbosity=0,
                )

    @override_settings(AUTH_USER_MODEL="auth_tests.CustomUserWithFK")
    def test_validate_fk_via_option_interactive(self):
        email = Email.objects.create(email="mymail@gmail.com")
        Group.objects.all().delete()
        nonexistent_group_id = 1
        msg = f"group instance with id {nonexistent_group_id} does not exist."

        @mock_inputs(
            {
                "password": "nopasswd",
                "Username (Email.id): ": email.pk,
                "Email (Email.email): ": email.email,
            }
        )
        def test(self):
            with self.assertRaisesMessage(CommandError, msg):
                call_command(
                    "createsuperuser",
                    group=nonexistent_group_id,
                    stdin=MockTTY(),
                    verbosity=0,
                )

        test(self)

    @override_settings(AUTH_USER_MODEL="auth_tests.CustomUserWithM2m")
    def test_fields_with_m2m(self):
        new_io = StringIO()
        org_id_1 = Organization.objects.create(name="Organization 1").pk
        org_id_2 = Organization.objects.create(name="Organization 2").pk
        call_command(
            "createsuperuser",
            interactive=False,
            username="joe",
            orgs=[org_id_1, org_id_2],
            stdout=new_io,
        )
        command_output = new_io.getvalue().strip()
        self.assertEqual(command_output, "Superuser created successfully.")
        user = CustomUserWithM2M._default_manager.get(username="joe")
        self.assertEqual(user.orgs.count(), 2)

    @override_settings(AUTH_USER_MODEL="auth_tests.CustomUserWithM2M")
    def test_fields_with_m2m_interactive(self):
        new_io = StringIO()
        org_id_1 = Organization.objects.create(name="Organization 1").pk
        org_id_2 = Organization.objects.create(name="Organization 2").pk

        @mock_inputs(
            {
                "password": "nopasswd",
                "Username: ": "joe",
                "Orgs (Organization.id): ": "%s, %s" % (org_id_1, org_id_2),
            }
        )
        def test(self):
            call_command(
                "createsuperuser",
                interactive=True,
                stdout=new_io,
                stdin=MockTTY(),
            )
            command_output = new_io.getvalue().strip()
            self.assertEqual(command_output, "Superuser created successfully.")
            user = CustomUserWithM2M._default_manager.get(username="joe")
            self.assertEqual(user.orgs.count(), 2)

        test(self)

    @override_settings(AUTH_USER_MODEL="auth_tests.CustomUserWithM2M")
    def test_fields_with_m2m_interactive_blank(self):
        new_io = StringIO()
        org_id = Organization.objects.create(name="Organization").pk
        entered_orgs = [str(org_id), " "]

        def return_orgs():
            return entered_orgs.pop()

        @mock_inputs(
            {
                "password": "nopasswd",
                "Username: ": "joe",
                "Orgs (Organization.id): ": return_orgs,
            }
        )
        def test(self):
            call_command(
                "createsuperuser",
                interactive=True,
                stdout=new_io,
                stderr=new_io,
                stdin=MockTTY(),
            )
            self.assertEqual(
                new_io.getvalue().strip(),
                "Error: This field cannot be blank.\n"
                "Superuser created successfully.",
            )

        test(self)

    @override_settings(AUTH_USER_MODEL="auth_tests.CustomUserWithM2MThrough")
    def test_fields_with_m2m_and_through(self):
        msg = (
            "Required field 'orgs' specifies a many-to-many relation through "
            "model, which is not supported."
        )
        with self.assertRaisesMessage(CommandError, msg):
            call_command("createsuperuser")

    def test_default_username(self):
        """createsuperuser uses a default username when one isn't provided."""
        # Get the default username before creating a user.
        default_username = get_default_username()
        new_io = StringIO()
        entered_passwords = ["password", "password"]

        def return_passwords():
            return entered_passwords.pop(0)

        @mock_inputs({"password": return_passwords, "username": "", "email": ""})
        def test(self):
            call_command(
                "createsuperuser",
                interactive=True,
                stdin=MockTTY(),
                stdout=new_io,
                stderr=new_io,
            )
            self.assertEqual(
                new_io.getvalue().strip(), "Superuser created successfully."
            )
            self.assertTrue(User.objects.filter(username=default_username).exists())

        test(self)

    def test_password_validation(self):
        """
        Creation should fail if the password fails validation.
        """
        new_io = StringIO()
        entered_passwords = ["1234567890", "1234567890", "password", "password"]

        def bad_then_good_password():
            return entered_passwords.pop(0)

        @mock_inputs(
            {
                "password": bad_then_good_password,
                "username": "joe1234567890",
                "email": "",
                "bypass": "n",
            }
        )
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
                "Superuser created successfully.",
            )

        test(self)

    @override_settings(
        AUTH_PASSWORD_VALIDATORS=[
            {
                "NAME": (
                    "django.contrib.auth.password_validation."
                    "UserAttributeSimilarityValidator"
                )
            },
        ]
    )
    def test_validate_password_against_username(self):
        new_io = StringIO()
        username = "supremelycomplex"
        entered_passwords = [
            username,
            username,
            "superduperunguessablepassword",
            "superduperunguessablepassword",
        ]

        def bad_then_good_password():
            return entered_passwords.pop(0)

        @mock_inputs(
            {
                "password": bad_then_good_password,
                "username": username,
                "email": "",
                "bypass": "n",
            }
        )
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
                "The password is too similar to the username.\n"
                "Superuser created successfully.",
            )

        test(self)

    @override_settings(
        AUTH_USER_MODEL="auth_tests.CustomUser",
        AUTH_PASSWORD_VALIDATORS=[
            {
                "NAME": (
                    "django.contrib.auth.password_validation."
                    "UserAttributeSimilarityValidator"
                )
            },
        ],
    )
    def test_validate_password_against_required_fields(self):
        new_io = StringIO()
        first_name = "josephine"
        entered_passwords = [
            first_name,
            first_name,
            "superduperunguessablepassword",
            "superduperunguessablepassword",
        ]

        def bad_then_good_password():
            return entered_passwords.pop(0)

        @mock_inputs(
            {
                "password": bad_then_good_password,
                "username": "whatever",
                "first_name": first_name,
                "date_of_birth": "1970-01-01",
                "email": "joey@example.com",
                "bypass": "n",
            }
        )
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
                "The password is too similar to the first name.\n"
                "Superuser created successfully.",
            )

        test(self)

    @override_settings(
        AUTH_USER_MODEL="auth_tests.CustomUser",
        AUTH_PASSWORD_VALIDATORS=[
            {
                "NAME": (
                    "django.contrib.auth.password_validation."
                    "UserAttributeSimilarityValidator"
                )
            },
        ],
    )
    def test_validate_password_against_required_fields_via_option(self):
        new_io = StringIO()
        first_name = "josephine"
        entered_passwords = [
            first_name,
            first_name,
            "superduperunguessablepassword",
            "superduperunguessablepassword",
        ]

        def bad_then_good_password():
            return entered_passwords.pop(0)

        @mock_inputs(
            {
                "password": bad_then_good_password,
                "bypass": "n",
            }
        )
        def test(self):
            call_command(
                "createsuperuser",
                interactive=True,
                first_name=first_name,
                date_of_birth="1970-01-01",
                email="joey@example.com",
                stdin=MockTTY(),
                stdout=new_io,
                stderr=new_io,
            )
            self.assertEqual(
                new_io.getvalue().strip(),
                "The password is too similar to the first name.\n"
                "Superuser created successfully.",
            )

        test(self)

    def test_blank_username(self):
        """Creation fails if --username is blank."""
        new_io = StringIO()
        with self.assertRaisesMessage(CommandError, "Username cannot be blank."):
            call_command(
                "createsuperuser",
                username="",
                stdin=MockTTY(),
                stdout=new_io,
                stderr=new_io,
            )

    def test_blank_username_non_interactive(self):
        new_io = StringIO()
        with self.assertRaisesMessage(CommandError, "Username cannot be blank."):
            call_command(
                "createsuperuser",
                username="",
                interactive=False,
                stdin=MockTTY(),
                stdout=new_io,
                stderr=new_io,
            )

    def test_password_validation_bypass(self):
        """
        Password validation can be bypassed by entering 'y' at the prompt.
        """
        new_io = StringIO()

        @mock_inputs(
            {
                "password": "1234567890",
                "username": "joe1234567890",
                "email": "",
                "bypass": "y",
            }
        )
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
                "Superuser created successfully.",
            )

        test(self)

    def test_invalid_username(self):
        """Creation fails if the username fails validation."""
        user_field = User._meta.get_field(User.USERNAME_FIELD)
        new_io = StringIO()
        entered_passwords = ["password", "password"]
        # Enter an invalid (too long) username first and then a valid one.
        invalid_username = ("x" * user_field.max_length) + "y"
        entered_usernames = [invalid_username, "janet"]

        def return_passwords():
            return entered_passwords.pop(0)

        def return_usernames():
            return entered_usernames.pop(0)

        @mock_inputs(
            {"password": return_passwords, "username": return_usernames, "email": ""}
        )
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
                "Error: Ensure this value has at most %s characters (it has %s).\n"
                "Superuser created successfully."
                % (user_field.max_length, len(invalid_username)),
            )

        test(self)

    @mock_inputs({"username": "KeyboardInterrupt"})
    def test_keyboard_interrupt(self):
        new_io = StringIO()
        with self.assertRaises(SystemExit):
            call_command(
                "createsuperuser",
                interactive=True,
                stdin=MockTTY(),
                stdout=new_io,
                stderr=new_io,
            )
        self.assertEqual(new_io.getvalue(), "\nOperation cancelled.\n")

    def test_existing_username(self):
        """Creation fails if the username already exists."""
        user = User.objects.create(username="janet")
        new_io = StringIO()
        entered_passwords = ["password", "password"]
        # Enter the existing username first and then a new one.
        entered_usernames = [user.username, "joe"]

        def return_passwords():
            return entered_passwords.pop(0)

        def return_usernames():
            return entered_usernames.pop(0)

        @mock_inputs(
            {"password": return_passwords, "username": return_usernames, "email": ""}
        )
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
                "Error: That username is already taken.\n"
                "Superuser created successfully.",
            )

        test(self)

    @override_settings(AUTH_USER_MODEL="auth_tests.CustomUserWithUniqueConstraint")
    def test_existing_username_meta_unique_constraint(self):
        """
        Creation fails if the username already exists and a custom user model
        has UniqueConstraint.
        """
        user = CustomUserWithUniqueConstraint.objects.create(username="janet")
        new_io = StringIO()
        entered_passwords = ["password", "password"]
        # Enter the existing username first and then a new one.
        entered_usernames = [user.username, "joe"]

        def return_passwords():
            return entered_passwords.pop(0)

        def return_usernames():
            return entered_usernames.pop(0)

        @mock_inputs({"password": return_passwords, "username": return_usernames})
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
                "Error: That username is already taken.\n"
                "Superuser created successfully.",
            )

        test(self)

    def test_existing_username_non_interactive(self):
        """Creation fails if the username already exists."""
        User.objects.create(username="janet")
        new_io = StringIO()
        with self.assertRaisesMessage(
            CommandError, "Error: That username is already taken."
        ):
            call_command(
                "createsuperuser",
                username="janet",
                email="",
                interactive=False,
                stdout=new_io,
            )

    def test_existing_username_provided_via_option_and_interactive(self):
        """call_command() gets username='janet' and interactive=True."""
        new_io = StringIO()
        entered_passwords = ["password", "password"]
        User.objects.create(username="janet")

        def return_passwords():
            return entered_passwords.pop(0)

        @mock_inputs(
            {
                "password": return_passwords,
                "username": "janet1",
                "email": "test@test.com",
            }
        )
        def test(self):
            call_command(
                "createsuperuser",
                username="janet",
                interactive=True,
                stdin=MockTTY(),
                stdout=new_io,
                stderr=new_io,
            )
            msg = (
                "Error: That username is already taken.\n"
                "Superuser created successfully."
            )
            self.assertEqual(new_io.getvalue().strip(), msg)

        test(self)

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

        @mock_inputs(
            {
                "password": mismatched_passwords_then_matched,
                "username": "joe1234567890",
                "email": "",
            }
        )
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
                "Superuser created successfully.",
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

        @mock_inputs(
            {
                "password": blank_passwords_then_valid,
                "username": "joe1234567890",
                "email": "",
            }
        )
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
                "Superuser created successfully.",
            )

        test(self)

    @override_settings(AUTH_USER_MODEL="auth_tests.NoPasswordUser")
    def test_usermodel_without_password(self):
        new_io = StringIO()
        call_command(
            "createsuperuser",
            interactive=False,
            stdin=MockTTY(),
            stdout=new_io,
            stderr=new_io,
            username="username",
        )
        self.assertEqual(new_io.getvalue().strip(), "Superuser created successfully.")

    @override_settings(AUTH_USER_MODEL="auth_tests.NoPasswordUser")
    def test_usermodel_without_password_interactive(self):
        new_io = StringIO()

        @mock_inputs({"username": "username"})
        def test(self):
            call_command(
                "createsuperuser",
                interactive=True,
                stdin=MockTTY(),
                stdout=new_io,
                stderr=new_io,
            )
            self.assertEqual(
                new_io.getvalue().strip(), "Superuser created successfully."
            )

        test(self)

    @mock.patch.dict(
        os.environ,
        {
            "DJANGO_SUPERUSER_PASSWORD": "test_password",
            "DJANGO_SUPERUSER_USERNAME": "test_superuser",
            "DJANGO_SUPERUSER_EMAIL": "joe@somewhere.org",
            "DJANGO_SUPERUSER_FIRST_NAME": "ignored_first_name",
        },
    )
    def test_environment_variable_non_interactive(self):
        call_command("createsuperuser", interactive=False, verbosity=0)
        user = User.objects.get(username="test_superuser")
        self.assertEqual(user.email, "joe@somewhere.org")
        self.assertTrue(user.check_password("test_password"))
        # Environment variables are ignored for non-required fields.
        self.assertEqual(user.first_name, "")

    @override_settings(AUTH_USER_MODEL="auth_tests.CustomUserWithM2m")
    def test_environment_variable_m2m_non_interactive(self):
        new_io = StringIO()
        org_id_1 = Organization.objects.create(name="Organization 1").pk
        org_id_2 = Organization.objects.create(name="Organization 2").pk
        with mock.patch.dict(
            os.environ,
            {
                "DJANGO_SUPERUSER_ORGS": f"{org_id_1},{org_id_2}",
            },
        ):
            call_command(
                "createsuperuser",
                interactive=False,
                username="joe",
                stdout=new_io,
            )
        command_output = new_io.getvalue().strip()
        self.assertEqual(command_output, "Superuser created successfully.")
        user = CustomUserWithM2M._default_manager.get(username="joe")
        self.assertEqual(user.orgs.count(), 2)

    @mock.patch.dict(
        os.environ,
        {
            "DJANGO_SUPERUSER_USERNAME": "test_superuser",
            "DJANGO_SUPERUSER_EMAIL": "joe@somewhere.org",
        },
    )
    def test_ignore_environment_variable_non_interactive(self):
        # Environment variables are ignored in non-interactive mode, if
        # provided by a command line arguments.
        call_command(
            "createsuperuser",
            interactive=False,
            username="cmd_superuser",
            email="cmd@somewhere.org",
            verbosity=0,
        )
        user = User.objects.get(username="cmd_superuser")
        self.assertEqual(user.email, "cmd@somewhere.org")
        self.assertFalse(user.has_usable_password())

    @mock.patch.dict(
        os.environ,
        {
            "DJANGO_SUPERUSER_PASSWORD": "test_password",
            "DJANGO_SUPERUSER_USERNAME": "test_superuser",
            "DJANGO_SUPERUSER_EMAIL": "joe@somewhere.org",
        },
    )
    def test_ignore_environment_variable_interactive(self):
        # Environment variables are ignored in interactive mode.
        @mock_inputs({"password": "cmd_password"})
        def test(self):
            call_command(
                "createsuperuser",
                interactive=True,
                username="cmd_superuser",
                email="cmd@somewhere.org",
                stdin=MockTTY(),
                verbosity=0,
            )
            user = User.objects.get(username="cmd_superuser")
            self.assertEqual(user.email, "cmd@somewhere.org")
            self.assertTrue(user.check_password("cmd_password"))

        test(self)


class MultiDBCreatesuperuserTestCase(TestCase):
    databases = {"default", "other"}

    def test_createsuperuser_command_with_database_option(self):
        """
        createsuperuser --database should operate on the specified DB.
        """
        new_io = StringIO()
        call_command(
            "createsuperuser",
            interactive=False,
            username="joe",
            email="joe@somewhere.org",
            database="other",
            stdout=new_io,
        )
        command_output = new_io.getvalue().strip()
        self.assertEqual(command_output, "Superuser created successfully.")
        user = User.objects.using("other").get(username="joe")
        self.assertEqual(user.email, "joe@somewhere.org")

    def test_createsuperuser_command_suggested_username_with_database_option(self):
        default_username = get_default_username(database="other")
        qs = User.objects.using("other")

        @mock_inputs({"password": "nopasswd", "username": "", "email": ""})
        def test_other_create_with_suggested_username(self):
            call_command(
                "createsuperuser",
                interactive=True,
                stdin=MockTTY(),
                verbosity=0,
                database="other",
            )
            self.assertIs(qs.filter(username=default_username).exists(), True)

        test_other_create_with_suggested_username(self)

        @mock_inputs({"password": "nopasswd", "Username: ": "other", "email": ""})
        def test_other_no_suggestion(self):
            call_command(
                "createsuperuser",
                interactive=True,
                stdin=MockTTY(),
                verbosity=0,
                database="other",
            )
            self.assertIs(qs.filter(username="other").exists(), True)

        test_other_no_suggestion(self)


class CreatePermissionsTests(TestCase):
    def setUp(self):
        self._original_permissions = Permission._meta.permissions[:]
        self._original_default_permissions = Permission._meta.default_permissions
        self.app_config = apps.get_app_config("auth")

    def tearDown(self):
        Permission._meta.permissions = self._original_permissions
        Permission._meta.default_permissions = self._original_default_permissions
        ContentType.objects.clear_cache()

    def test_default_permissions(self):
        permission_content_type = ContentType.objects.get_by_natural_key(
            "auth", "permission"
        )
        Permission._meta.permissions = [
            ("my_custom_permission", "Some permission"),
        ]
        create_permissions(self.app_config, verbosity=0)

        # view/add/change/delete permission by default + custom permission
        self.assertEqual(
            Permission.objects.filter(
                content_type=permission_content_type,
            ).count(),
            5,
        )

        Permission.objects.filter(content_type=permission_content_type).delete()
        Permission._meta.default_permissions = []
        create_permissions(self.app_config, verbosity=0)

        # custom permission only since default permissions is empty
        self.assertEqual(
            Permission.objects.filter(
                content_type=permission_content_type,
            ).count(),
            1,
        )

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
        state = migrations.state.ProjectState(real_apps={"contenttypes"})
        with self.assertNumQueries(0):
            create_permissions(self.app_config, verbosity=0, apps=state.apps)

    def test_create_permissions_checks_contenttypes_created(self):
        """
        `post_migrate` handler ordering isn't guaranteed. Simulate a case
        where create_permissions() is called before create_contenttypes().
        """
        # Warm the manager cache.
        ContentType.objects.get_for_model(Group)
        # Apply a deletion as if e.g. a database 'flush' had been executed.
        ContentType.objects.filter(app_label="auth", model="group").delete()
        # This fails with a foreign key constraint without the fix.
        create_permissions(apps.get_app_config("auth"), interactive=False, verbosity=0)

    def test_permission_with_proxy_content_type_created(self):
        """
        A proxy model's permissions use its own content type rather than the
        content type of the concrete model.
        """
        opts = UserProxy._meta
        codename = get_permission_codename("add", opts)
        self.assertTrue(
            Permission.objects.filter(
                content_type__model=opts.model_name,
                content_type__app_label=opts.app_label,
                codename=codename,
            ).exists()
        )
