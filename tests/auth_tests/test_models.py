from unittest import mock

from django.conf.global_settings import PASSWORD_HASHERS
from django.contrib.auth import get_user_model
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.hashers import get_hasher
from django.contrib.auth.models import (
    AbstractUser, AnonymousUser, Group, Permission, User, UserManager,
)
from django.contrib.contenttypes.models import ContentType
from django.core import mail
from django.db.models.signals import post_save
from django.test import SimpleTestCase, TestCase, override_settings

from .models import IntegerUsernameUser
from .models.with_custom_email_field import CustomEmailField


class NaturalKeysTestCase(TestCase):

    def test_user_natural_key(self):
        staff_user = User.objects.create_user(username='staff')
        self.assertEqual(User.objects.get_by_natural_key('staff'), staff_user)
        self.assertEqual(staff_user.natural_key(), ('staff',))

    def test_group_natural_key(self):
        users_group = Group.objects.create(name='users')
        self.assertEqual(Group.objects.get_by_natural_key('users'), users_group)


class LoadDataWithoutNaturalKeysTestCase(TestCase):
    fixtures = ['regular.json']

    def test_user_is_created_and_added_to_group(self):
        user = User.objects.get(username='my_username')
        group = Group.objects.get(name='my_group')
        self.assertEqual(group, user.groups.get())


class LoadDataWithNaturalKeysTestCase(TestCase):
    fixtures = ['natural.json']

    def test_user_is_created_and_added_to_group(self):
        user = User.objects.get(username='my_username')
        group = Group.objects.get(name='my_group')
        self.assertEqual(group, user.groups.get())


class LoadDataWithNaturalKeysAndMultipleDatabasesTestCase(TestCase):
    databases = {'default', 'other'}

    def test_load_data_with_user_permissions(self):
        # Create test contenttypes for both databases
        default_objects = [
            ContentType.objects.db_manager('default').create(
                model='examplemodela',
                app_label='app_a',
            ),
            ContentType.objects.db_manager('default').create(
                model='examplemodelb',
                app_label='app_b',
            ),
        ]
        other_objects = [
            ContentType.objects.db_manager('other').create(
                model='examplemodelb',
                app_label='app_b',
            ),
            ContentType.objects.db_manager('other').create(
                model='examplemodela',
                app_label='app_a',
            ),
        ]

        # Now we create the test UserPermission
        Permission.objects.db_manager("default").create(
            name="Can delete example model b",
            codename="delete_examplemodelb",
            content_type=default_objects[1],
        )
        Permission.objects.db_manager("other").create(
            name="Can delete example model b",
            codename="delete_examplemodelb",
            content_type=other_objects[0],
        )

        perm_default = Permission.objects.get_by_natural_key(
            'delete_examplemodelb',
            'app_b',
            'examplemodelb',
        )

        perm_other = Permission.objects.db_manager('other').get_by_natural_key(
            'delete_examplemodelb',
            'app_b',
            'examplemodelb',
        )

        self.assertEqual(perm_default.content_type_id, default_objects[1].id)
        self.assertEqual(perm_other.content_type_id, other_objects[0].id)


class UserManagerTestCase(TestCase):

    def test_create_user(self):
        email_lowercase = 'normal@normal.com'
        user = User.objects.create_user('user', email_lowercase)
        self.assertEqual(user.email, email_lowercase)
        self.assertEqual(user.username, 'user')
        self.assertFalse(user.has_usable_password())

    def test_create_user_email_domain_normalize_rfc3696(self):
        # According to https://tools.ietf.org/html/rfc3696#section-3
        # the "@" symbol can be part of the local part of an email address
        returned = UserManager.normalize_email(r'Abc\@DEF@EXAMPLE.com')
        self.assertEqual(returned, r'Abc\@DEF@example.com')

    def test_create_user_email_domain_normalize(self):
        returned = UserManager.normalize_email('normal@DOMAIN.COM')
        self.assertEqual(returned, 'normal@domain.com')

    def test_create_user_email_domain_normalize_with_whitespace(self):
        returned = UserManager.normalize_email(r'email\ with_whitespace@D.COM')
        self.assertEqual(returned, r'email\ with_whitespace@d.com')

    def test_empty_username(self):
        with self.assertRaisesMessage(ValueError, 'The given username must be set'):
            User.objects.create_user(username='')

    def test_create_user_is_staff(self):
        email = 'normal@normal.com'
        user = User.objects.create_user('user', email, is_staff=True)
        self.assertEqual(user.email, email)
        self.assertEqual(user.username, 'user')
        self.assertTrue(user.is_staff)

    def test_create_super_user_raises_error_on_false_is_superuser(self):
        with self.assertRaisesMessage(ValueError, 'Superuser must have is_superuser=True.'):
            User.objects.create_superuser(
                username='test', email='test@test.com',
                password='test', is_superuser=False,
            )

    def test_create_superuser_raises_error_on_false_is_staff(self):
        with self.assertRaisesMessage(ValueError, 'Superuser must have is_staff=True.'):
            User.objects.create_superuser(
                username='test', email='test@test.com',
                password='test', is_staff=False,
            )

    def test_make_random_password(self):
        allowed_chars = 'abcdefg'
        password = UserManager().make_random_password(5, allowed_chars)
        self.assertEqual(len(password), 5)
        for char in password:
            self.assertIn(char, allowed_chars)


class AbstractBaseUserTests(SimpleTestCase):

    def test_has_usable_password(self):
        """
        Passwords are usable even if they don't correspond to a hasher in
        settings.PASSWORD_HASHERS.
        """
        self.assertIs(User(password='some-gibbberish').has_usable_password(), True)

    def test_normalize_username(self):
        self.assertEqual(IntegerUsernameUser().normalize_username(123), 123)

    def test_clean_normalize_username(self):
        # The normalization happens in AbstractBaseUser.clean()
        ohm_username = 'iamtheΩ'  # U+2126 OHM SIGN
        for model in ('auth.User', 'auth_tests.CustomUser'):
            with self.subTest(model=model), self.settings(AUTH_USER_MODEL=model):
                User = get_user_model()
                user = User(**{User.USERNAME_FIELD: ohm_username, 'password': 'foo'})
                user.clean()
                username = user.get_username()
                self.assertNotEqual(username, ohm_username)
                self.assertEqual(username, 'iamtheΩ')  # U+03A9 GREEK CAPITAL LETTER OMEGA

    def test_default_email(self):
        user = AbstractBaseUser()
        self.assertEqual(user.get_email_field_name(), 'email')

    def test_custom_email(self):
        user = CustomEmailField()
        self.assertEqual(user.get_email_field_name(), 'email_address')


class AbstractUserTestCase(TestCase):
    def test_email_user(self):
        # valid send_mail parameters
        kwargs = {
            "fail_silently": False,
            "auth_user": None,
            "auth_password": None,
            "connection": None,
            "html_message": None,
        }
        abstract_user = AbstractUser(email='foo@bar.com')
        abstract_user.email_user(
            subject="Subject here",
            message="This is a message",
            from_email="from@domain.com",
            **kwargs
        )
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.subject, "Subject here")
        self.assertEqual(message.body, "This is a message")
        self.assertEqual(message.from_email, "from@domain.com")
        self.assertEqual(message.to, [abstract_user.email])

    def test_last_login_default(self):
        user1 = User.objects.create(username='user1')
        self.assertIsNone(user1.last_login)

        user2 = User.objects.create_user(username='user2')
        self.assertIsNone(user2.last_login)

    def test_user_clean_normalize_email(self):
        user = User(username='user', password='foo', email='foo@BAR.com')
        user.clean()
        self.assertEqual(user.email, 'foo@bar.com')

    def test_user_double_save(self):
        """
        Calling user.save() twice should trigger password_changed() once.
        """
        user = User.objects.create_user(username='user', password='foo')
        user.set_password('bar')
        with mock.patch('django.contrib.auth.password_validation.password_changed') as pw_changed:
            user.save()
            self.assertEqual(pw_changed.call_count, 1)
            user.save()
            self.assertEqual(pw_changed.call_count, 1)

    @override_settings(PASSWORD_HASHERS=PASSWORD_HASHERS)
    def test_check_password_upgrade(self):
        """
        password_changed() shouldn't be called if User.check_password()
        triggers a hash iteration upgrade.
        """
        user = User.objects.create_user(username='user', password='foo')
        initial_password = user.password
        self.assertTrue(user.check_password('foo'))
        hasher = get_hasher('default')
        self.assertEqual('pbkdf2_sha256', hasher.algorithm)

        old_iterations = hasher.iterations
        try:
            # Upgrade the password iterations
            hasher.iterations = old_iterations + 1
            with mock.patch('django.contrib.auth.password_validation.password_changed') as pw_changed:
                user.check_password('foo')
                self.assertEqual(pw_changed.call_count, 0)
            self.assertNotEqual(initial_password, user.password)
        finally:
            hasher.iterations = old_iterations


class IsActiveTestCase(TestCase):
    """
    Tests the behavior of the guaranteed is_active attribute
    """

    def test_builtin_user_isactive(self):
        user = User.objects.create(username='foo', email='foo@bar.com')
        # is_active is true by default
        self.assertIs(user.is_active, True)
        user.is_active = False
        user.save()
        user_fetched = User.objects.get(pk=user.pk)
        # the is_active flag is saved
        self.assertFalse(user_fetched.is_active)

    @override_settings(AUTH_USER_MODEL='auth_tests.IsActiveTestUser1')
    def test_is_active_field_default(self):
        """
        tests that the default value for is_active is provided
        """
        UserModel = get_user_model()
        user = UserModel(username='foo')
        self.assertIs(user.is_active, True)
        # you can set the attribute - but it will not save
        user.is_active = False
        # there should be no problem saving - but the attribute is not saved
        user.save()
        user_fetched = UserModel._default_manager.get(pk=user.pk)
        # the attribute is always true for newly retrieved instance
        self.assertIs(user_fetched.is_active, True)


class TestCreateSuperUserSignals(TestCase):
    """
    Simple test case for ticket #20541
    """
    def post_save_listener(self, *args, **kwargs):
        self.signals_count += 1

    def setUp(self):
        self.signals_count = 0
        post_save.connect(self.post_save_listener, sender=User)

    def tearDown(self):
        post_save.disconnect(self.post_save_listener, sender=User)

    def test_create_user(self):
        User.objects.create_user("JohnDoe")
        self.assertEqual(self.signals_count, 1)

    def test_create_superuser(self):
        User.objects.create_superuser("JohnDoe", "mail@example.com", "1")
        self.assertEqual(self.signals_count, 1)


class AnonymousUserTests(SimpleTestCase):
    no_repr_msg = "Django doesn't provide a DB representation for AnonymousUser."

    def setUp(self):
        self.user = AnonymousUser()

    def test_properties(self):
        self.assertIsNone(self.user.pk)
        self.assertEqual(self.user.username, '')
        self.assertEqual(self.user.get_username(), '')
        self.assertIs(self.user.is_anonymous, True)
        self.assertIs(self.user.is_authenticated, False)
        self.assertIs(self.user.is_staff, False)
        self.assertIs(self.user.is_active, False)
        self.assertIs(self.user.is_superuser, False)
        self.assertEqual(self.user.groups.all().count(), 0)
        self.assertEqual(self.user.user_permissions.all().count(), 0)
        self.assertEqual(self.user.get_user_permissions(), set())
        self.assertEqual(self.user.get_group_permissions(), set())

    def test_str(self):
        self.assertEqual(str(self.user), 'AnonymousUser')

    def test_eq(self):
        self.assertEqual(self.user, AnonymousUser())
        self.assertNotEqual(self.user, User('super', 'super@example.com', 'super'))

    def test_hash(self):
        self.assertEqual(hash(self.user), 1)

    def test_int(self):
        msg = (
            'Cannot cast AnonymousUser to int. Are you trying to use it in '
            'place of User?'
        )
        with self.assertRaisesMessage(TypeError, msg):
            int(self.user)

    def test_delete(self):
        with self.assertRaisesMessage(NotImplementedError, self.no_repr_msg):
            self.user.delete()

    def test_save(self):
        with self.assertRaisesMessage(NotImplementedError, self.no_repr_msg):
            self.user.save()

    def test_set_password(self):
        with self.assertRaisesMessage(NotImplementedError, self.no_repr_msg):
            self.user.set_password('password')

    def test_check_password(self):
        with self.assertRaisesMessage(NotImplementedError, self.no_repr_msg):
            self.user.check_password('password')


class GroupTests(SimpleTestCase):
    def test_str(self):
        g = Group(name='Users')
        self.assertEqual(str(g), 'Users')


class PermissionTests(TestCase):
    def test_str(self):
        p = Permission.objects.get(codename='view_customemailfield')
        self.assertEqual(str(p), 'auth_tests | custom email field | Can view custom email field')
