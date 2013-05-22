# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

import locale

from django.contrib.auth import get_user_model
from django.contrib.auth.management.commands import createsuperuser
from django.contrib.auth.models import User, AnonymousUser
from django.contrib.auth.tests.test_custom_user import CustomUser
from django.contrib.auth.tests.utils import skipIfCustomUser
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.dispatch import receiver
from django.test import TestCase
from django.test.signals import setting_changed
from django.test.utils import override_settings
from django.utils import translation
from django.utils.encoding import force_str
from django.utils.six import binary_type, PY3, StringIO


@receiver(setting_changed)
def user_model_swapped(**kwargs):
    if kwargs['setting'] == 'AUTH_USER_MODEL':
        from django.db.models.manager import ensure_default_manager
        from django.contrib.auth.models import User
        # Reset User manager
        setattr(User, 'objects', User._default_manager)
        ensure_default_manager(User)


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
                    if not PY3:
                        # getpass on Windows only supports prompt as bytestring (#19807)
                        assert isinstance(prompt, binary_type)
                    return inputs['password']

            def mock_input(prompt):
                # prompt should be encoded in Python 2. This line will raise an
                # Exception if prompt contains unencoded non-ascii on Python 2.
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


@skipIfCustomUser
class BasicTestCase(TestCase):
    def test_user(self):
        "Check that users can be created and can set their password"
        u = User.objects.create_user('testuser', 'test@example.com', 'testpw')
        self.assertTrue(u.has_usable_password())
        self.assertFalse(u.check_password('bad'))
        self.assertTrue(u.check_password('testpw'))

        # Check we can manually set an unusable password
        u.set_unusable_password()
        u.save()
        self.assertFalse(u.check_password('testpw'))
        self.assertFalse(u.has_usable_password())
        u.set_password('testpw')
        self.assertTrue(u.check_password('testpw'))
        u.set_password(None)
        self.assertFalse(u.has_usable_password())

        # Check authentication/permissions
        self.assertTrue(u.is_authenticated())
        self.assertFalse(u.is_staff)
        self.assertTrue(u.is_active)
        self.assertFalse(u.is_superuser)

        # Check API-based user creation with no password
        u2 = User.objects.create_user('testuser2', 'test2@example.com')
        self.assertFalse(u2.has_usable_password())

    def test_user_no_email(self):
        "Check that users can be created without an email"
        u = User.objects.create_user('testuser1')
        self.assertEqual(u.email, '')

        u2 = User.objects.create_user('testuser2', email='')
        self.assertEqual(u2.email, '')

        u3 = User.objects.create_user('testuser3', email=None)
        self.assertEqual(u3.email, '')

    def test_anonymous_user(self):
        "Check the properties of the anonymous user"
        a = AnonymousUser()
        self.assertEqual(a.pk, None)
        self.assertFalse(a.is_authenticated())
        self.assertFalse(a.is_staff)
        self.assertFalse(a.is_active)
        self.assertFalse(a.is_superuser)
        self.assertEqual(a.groups.all().count(), 0)
        self.assertEqual(a.user_permissions.all().count(), 0)

    def test_superuser(self):
        "Check the creation and properties of a superuser"
        super = User.objects.create_superuser('super', 'super@example.com', 'super')
        self.assertTrue(super.is_superuser)
        self.assertTrue(super.is_active)
        self.assertTrue(super.is_staff)

    def test_createsuperuser_management_command(self):
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

        call_command("createsuperuser",
            interactive=False,
            username="joe+admin@somewhere.org",
            email="joe@somewhere.org",
            verbosity=0
        )
        u = User.objects.get(username="joe+admin@somewhere.org")
        self.assertEqual(u.email, 'joe@somewhere.org')
        self.assertFalse(u.has_usable_password())

    @mock_inputs({'password': "nopasswd"})
    def test_createsuperuser_nolocale(self):
        """
        Check that createsuperuser does not break when no locale is set. See
        ticket #16017.
        """

        old_getdefaultlocale = locale.getdefaultlocale
        try:
            # Temporarily remove locale information
            locale.getdefaultlocale = lambda: (None, None)

            # Call the command in this new environment
            call_command("createsuperuser",
                interactive=True,
                username="nolocale@somewhere.org",
                email="nolocale@somewhere.org",
                verbosity=0
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
        'uživatel': 'foo',  # username (cz)
        'email': 'nolocale@somewhere.org'})
    def test_createsuperuser_non_ascii_verbose_name(self):
        # Aliased so the string doesn't get extracted
        from django.utils.translation import ugettext_lazy as ulazy
        username_field = User._meta.get_field('username')
        old_verbose_name = username_field.verbose_name
        username_field.verbose_name = ulazy('uživatel')
        new_io = StringIO()
        try:
            call_command("createsuperuser",
                interactive=True,
                stdout=new_io
            )
        finally:
            username_field.verbose_name = old_verbose_name

        command_output = new_io.getvalue().strip()
        self.assertEqual(command_output, 'Superuser created successfully.')

    def test_get_user_model(self):
        "The current user model can be retrieved"
        self.assertEqual(get_user_model(), User)

    @override_settings(AUTH_USER_MODEL='auth.CustomUser')
    def test_swappable_user(self):
        "The current user model can be swapped out for another"
        self.assertEqual(get_user_model(), CustomUser)
        with self.assertRaises(AttributeError):
            User.objects.all()

    @override_settings(AUTH_USER_MODEL='badsetting')
    def test_swappable_user_bad_setting(self):
        "The alternate user setting must point to something in the format app.model"
        with self.assertRaises(ImproperlyConfigured):
            get_user_model()

    @override_settings(AUTH_USER_MODEL='thismodel.doesntexist')
    def test_swappable_user_nonexistent_model(self):
        "The current user model must point to an installed model"
        with self.assertRaises(ImproperlyConfigured):
            get_user_model()

    @skipIfCustomUser
    def test_user_verbose_names_translatable(self):
        "Default User model verbose names are translatable (#19945)"
        with translation.override('en'):
            self.assertEqual(User._meta.verbose_name, 'user')
            self.assertEqual(User._meta.verbose_name_plural, 'users')
        with translation.override('es'):
            self.assertEqual(User._meta.verbose_name, 'usuario')
            self.assertEqual(User._meta.verbose_name_plural, 'usuarios')
