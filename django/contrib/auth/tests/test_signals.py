from django.contrib.auth import signals
from django.contrib.auth.models import User
from django.contrib.auth.tests.utils import skipIfCustomUser
from django.test import TestCase
from django.test.client import RequestFactory
from django.test import override_settings


@skipIfCustomUser
@override_settings(USE_TZ=False, PASSWORD_HASHERS=('django.contrib.auth.hashers.SHA1PasswordHasher',))
class SignalTestCase(TestCase):
    urls = 'django.contrib.auth.tests.urls'
    fixtures = ['authtestdata.json']

    def listener_login(self, user, **kwargs):
        self.logged_in.append(user)

    def listener_logout(self, user, **kwargs):
        self.logged_out.append(user)

    def listener_login_failed(self, sender, credentials, **kwargs):
        self.login_failed.append(credentials)

    def setUp(self):
        """Set up the listeners and reset the logged in/logged out counters"""
        self.logged_in = []
        self.logged_out = []
        self.login_failed = []
        signals.user_logged_in.connect(self.listener_login)
        signals.user_logged_out.connect(self.listener_logout)
        signals.user_login_failed.connect(self.listener_login_failed)

    def tearDown(self):
        """Disconnect the listeners"""
        signals.user_logged_in.disconnect(self.listener_login)
        signals.user_logged_out.disconnect(self.listener_logout)
        signals.user_login_failed.disconnect(self.listener_login_failed)

    def test_login(self):
        # Only a successful login will trigger the success signal.
        self.client.login(username='testclient', password='bad')
        self.assertEqual(len(self.logged_in), 0)
        self.assertEqual(len(self.login_failed), 1)
        self.assertEqual(self.login_failed[0]['username'], 'testclient')
        # verify the password is cleansed
        self.assertTrue('***' in self.login_failed[0]['password'])

        # Like this:
        self.client.login(username='testclient', password='password')
        self.assertEqual(len(self.logged_in), 1)
        self.assertEqual(self.logged_in[0].username, 'testclient')

        # Ensure there were no more failures.
        self.assertEqual(len(self.login_failed), 1)

    def test_logout_anonymous(self):
        # The log_out function will still trigger the signal for anonymous
        # users.
        self.client.get('/logout/next_page/')
        self.assertEqual(len(self.logged_out), 1)
        self.assertEqual(self.logged_out[0], None)

    def test_logout(self):
        self.client.login(username='testclient', password='password')
        self.client.get('/logout/next_page/')
        self.assertEqual(len(self.logged_out), 1)
        self.assertEqual(self.logged_out[0].username, 'testclient')

    def test_update_last_login(self):
        """Ensure that only `last_login` is updated in `update_last_login`"""
        user = User.objects.get(pk=3)
        old_last_login = user.last_login

        user.username = "This username shouldn't get saved"
        request = RequestFactory().get('/login')
        signals.user_logged_in.send(sender=user.__class__, request=request,
            user=user)
        user = User.objects.get(pk=3)
        self.assertEqual(user.username, 'staff')
        self.assertNotEqual(user.last_login, old_last_login)
