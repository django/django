from datetime import datetime

from django.conf import settings
from django.contrib.auth.backends import RemoteUserBackend
from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone


class RemoteUserTest(TestCase):

    urls = 'django.contrib.auth.tests.urls'
    middleware = 'django.contrib.auth.middleware.RemoteUserMiddleware'
    backend = 'django.contrib.auth.backends.RemoteUserBackend'

    # Usernames to be passed in REMOTE_USER for the test_known_user test case.
    known_user = 'knownuser'
    known_user2 = 'knownuser2'

    def setUp(self):
        self.curr_middleware = settings.MIDDLEWARE_CLASSES
        self.curr_auth = settings.AUTHENTICATION_BACKENDS
        settings.MIDDLEWARE_CLASSES += (self.middleware,)
        settings.AUTHENTICATION_BACKENDS = (self.backend,)

    def test_no_remote_user(self):
        """
        Tests requests where no remote user is specified and insures that no
        users get created.
        """
        num_users = User.objects.count()

        response = self.client.get('/remote_user/')
        self.assertTrue(response.context['user'].is_anonymous())
        self.assertEqual(User.objects.count(), num_users)

        response = self.client.get('/remote_user/', REMOTE_USER=None)
        self.assertTrue(response.context['user'].is_anonymous())
        self.assertEqual(User.objects.count(), num_users)

        response = self.client.get('/remote_user/', REMOTE_USER='')
        self.assertTrue(response.context['user'].is_anonymous())
        self.assertEqual(User.objects.count(), num_users)

    def test_unknown_user(self):
        """
        Tests the case where the username passed in the header does not exist
        as a User.
        """
        num_users = User.objects.count()
        response = self.client.get('/remote_user/', REMOTE_USER='newuser')
        self.assertEqual(response.context['user'].username, 'newuser')
        self.assertEqual(User.objects.count(), num_users + 1)
        User.objects.get(username='newuser')

        # Another request with same user should not create any new users.
        response = self.client.get('/remote_user/', REMOTE_USER='newuser')
        self.assertEqual(User.objects.count(), num_users + 1)

    def test_known_user(self):
        """
        Tests the case where the username passed in the header is a valid User.
        """
        User.objects.create(username='knownuser')
        User.objects.create(username='knownuser2')
        num_users = User.objects.count()
        response = self.client.get('/remote_user/', REMOTE_USER=self.known_user)
        self.assertEqual(response.context['user'].username, 'knownuser')
        self.assertEqual(User.objects.count(), num_users)
        # Test that a different user passed in the headers causes the new user
        # to be logged in.
        response = self.client.get('/remote_user/', REMOTE_USER=self.known_user2)
        self.assertEqual(response.context['user'].username, 'knownuser2')
        self.assertEqual(User.objects.count(), num_users)

    def test_last_login(self):
        """
        Tests that a user's last_login is set the first time they make a
        request but not updated in subsequent requests with the same session.
        """
        user = User.objects.create(username='knownuser')
        # Set last_login to something so we can determine if it changes.
        default_login = datetime(2000, 1, 1)
        if settings.USE_TZ:
            default_login = default_login.replace(tzinfo=timezone.utc)
        user.last_login = default_login
        user.save()

        response = self.client.get('/remote_user/', REMOTE_USER=self.known_user)
        self.assertNotEqual(default_login, response.context['user'].last_login)

        user = User.objects.get(username='knownuser')
        user.last_login = default_login
        user.save()
        response = self.client.get('/remote_user/', REMOTE_USER=self.known_user)
        self.assertEqual(default_login, response.context['user'].last_login)

    def test_user_switch_forces_new_login(self):
        """
        Tests that if the username in the header changes between requests
        that the original user is logged out
        """
        User.objects.create(username='knownuser')
        # Known user authenticates
        response = self.client.get('/remote_user/',
                                   **{'REMOTE_USER': self.known_user})
        self.assertEqual(response.context['user'].username, 'knownuser')
        # During the session, the REMOTE_USER changes to a different user.
        response = self.client.get('/remote_user/',
                                   **{'REMOTE_USER': "newnewuser"})
        # Ensure that the current user is not the prior remote_user
        # In backends that create a new user, username is "newnewuser"
        # In backends that do not create new users, it is '' (anonymous user)
        self.assertNotEqual(response.context['user'].username, 'knownuser')

    def tearDown(self):
        """Restores settings to avoid breaking other tests."""
        settings.MIDDLEWARE_CLASSES = self.curr_middleware
        settings.AUTHENTICATION_BACKENDS = self.curr_auth


class RemoteUserNoCreateBackend(RemoteUserBackend):
    """Backend that doesn't create unknown users."""
    create_unknown_user = False


class RemoteUserNoCreateTest(RemoteUserTest):
    """
    Contains the same tests as RemoteUserTest, but using a custom auth backend
    class that doesn't create unknown users.
    """

    backend =\
        'django.contrib.auth.tests.remote_user.RemoteUserNoCreateBackend'

    def test_unknown_user(self):
        num_users = User.objects.count()
        response = self.client.get('/remote_user/', REMOTE_USER='newuser')
        self.assertTrue(response.context['user'].is_anonymous())
        self.assertEqual(User.objects.count(), num_users)


class CustomRemoteUserBackend(RemoteUserBackend):
    """
    Backend that overrides RemoteUserBackend methods.
    """

    def clean_username(self, username):
        """
        Grabs username before the @ character.
        """
        return username.split('@')[0]

    def configure_user(self, user):
        """
        Sets user's email address.
        """
        user.email = 'user@example.com'
        user.save()
        return user


class RemoteUserCustomTest(RemoteUserTest):
    """
    Tests a custom RemoteUserBackend subclass that overrides the clean_username
    and configure_user methods.
    """

    backend =\
        'django.contrib.auth.tests.remote_user.CustomRemoteUserBackend'
    # REMOTE_USER strings with email addresses for the custom backend to
    # clean.
    known_user = 'knownuser@example.com'
    known_user2 = 'knownuser2@example.com'

    def test_known_user(self):
        """
        The strings passed in REMOTE_USER should be cleaned and the known users
        should not have been configured with an email address.
        """
        super(RemoteUserCustomTest, self).test_known_user()
        self.assertEqual(User.objects.get(username='knownuser').email, '')
        self.assertEqual(User.objects.get(username='knownuser2').email, '')

    def test_unknown_user(self):
        """
        The unknown user created should be configured with an email address.
        """
        super(RemoteUserCustomTest, self).test_unknown_user()
        newuser = User.objects.get(username='newuser')
        self.assertEqual(newuser.email, 'user@example.com')
