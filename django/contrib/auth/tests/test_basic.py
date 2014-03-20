from __future__ import unicode_literals

from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User, AnonymousUser
from django.contrib.auth.tests.custom_user import CustomUser
from django.contrib.auth.tests.utils import skipIfCustomUser
from django.core.exceptions import ImproperlyConfigured
from django.dispatch import receiver
from django.test import TestCase, override_settings
from django.test.signals import setting_changed
from django.utils import translation


@receiver(setting_changed)
def user_model_swapped(**kwargs):
    if kwargs['setting'] == 'AUTH_USER_MODEL':
        from django.db.models.manager import ensure_default_manager
        # Reset User manager
        setattr(User, 'objects', User._default_manager)
        ensure_default_manager(User)
        apps.clear_cache()


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
