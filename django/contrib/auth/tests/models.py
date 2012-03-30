from django.conf import settings
from django.test import TestCase
from django.test.utils import override_settings
from django.contrib.auth.models import (Group, User,
    SiteProfileNotAvailable, UserManager)


@override_settings(USE_TZ=False)
class ProfileTestCase(TestCase):
    fixtures = ['authtestdata.json']

    def setUp(self):
        """Backs up the AUTH_PROFILE_MODULE"""
        self.old_AUTH_PROFILE_MODULE = getattr(settings,
                                               'AUTH_PROFILE_MODULE', None)

    def tearDown(self):
        """Restores the AUTH_PROFILE_MODULE -- if it was not set it is deleted,
        otherwise the old value is restored"""
        if self.old_AUTH_PROFILE_MODULE is None and \
                hasattr(settings, 'AUTH_PROFILE_MODULE'):
            del settings.AUTH_PROFILE_MODULE

        if self.old_AUTH_PROFILE_MODULE is not None:
            settings.AUTH_PROFILE_MODULE = self.old_AUTH_PROFILE_MODULE

    def test_site_profile_not_available(self):
        # calling get_profile without AUTH_PROFILE_MODULE set
        if hasattr(settings, 'AUTH_PROFILE_MODULE'):
            del settings.AUTH_PROFILE_MODULE
        user = User.objects.get(username='testclient')
        self.assertRaises(SiteProfileNotAvailable, user.get_profile)

        # Bad syntax in AUTH_PROFILE_MODULE:
        settings.AUTH_PROFILE_MODULE = 'foobar'
        self.assertRaises(SiteProfileNotAvailable, user.get_profile)

        # module that doesn't exist
        settings.AUTH_PROFILE_MODULE = 'foo.bar'
        self.assertRaises(SiteProfileNotAvailable, user.get_profile)


@override_settings(USE_TZ=False)
class NaturalKeysTestCase(TestCase):
    fixtures = ['authtestdata.json']

    def test_user_natural_key(self):
        staff_user = User.objects.get(username='staff')
        self.assertEquals(User.objects.get_by_natural_key('staff'), staff_user)
        self.assertEquals(staff_user.natural_key(), ('staff',))

    def test_group_natural_key(self):
        users_group = Group.objects.create(name='users')
        self.assertEquals(Group.objects.get_by_natural_key('users'), users_group)


@override_settings(USE_TZ=False)
class LoadDataWithoutNaturalKeysTestCase(TestCase):
    fixtures = ['regular.json']

    def test_user_is_created_and_added_to_group(self):
        user = User.objects.get(username='my_username')
        group = Group.objects.get(name='my_group')
        self.assertEquals(group, user.groups.get())


@override_settings(USE_TZ=False)
class LoadDataWithNaturalKeysTestCase(TestCase):
    fixtures = ['natural.json']

    def test_user_is_created_and_added_to_group(self):
        user = User.objects.get(username='my_username')
        group = Group.objects.get(name='my_group')
        self.assertEquals(group, user.groups.get())


class UserManagerTestCase(TestCase):

    def test_create_user(self):
        email_lowercase = 'normal@normal.com'
        user = User.objects.create_user('user', email_lowercase)
        self.assertEquals(user.email, email_lowercase)
        self.assertEquals(user.username, 'user')
        self.assertEquals(user.password, '!')

    def test_create_user_email_domain_normalize_rfc3696(self):
        # According to  http://tools.ietf.org/html/rfc3696#section-3
        # the "@" symbol can be part of the local part of an email address
        returned = UserManager.normalize_email(r'Abc\@DEF@EXAMPLE.com')
        self.assertEquals(returned, r'Abc\@DEF@example.com')

    def test_create_user_email_domain_normalize(self):
        returned = UserManager.normalize_email('normal@DOMAIN.COM')
        self.assertEquals(returned, 'normal@domain.com')

    def test_create_user_email_domain_normalize_with_whitespace(self):
        returned = UserManager.normalize_email('email\ with_whitespace@D.COM')
        self.assertEquals(returned, 'email\ with_whitespace@d.com')

    def test_empty_username(self):
        self.assertRaisesMessage(ValueError,
                                 'The given username must be set',
                                  User.objects.create_user, username='')
