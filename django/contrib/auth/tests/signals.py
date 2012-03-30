from django.test import TestCase
from django.test.utils import override_settings
from django.contrib.auth import signals


@override_settings(USE_TZ=False)
class SignalTestCase(TestCase):
    urls = 'django.contrib.auth.tests.urls'
    fixtures = ['authtestdata.json']

    def listener_login(self, user, **kwargs):
        self.logged_in.append(user)

    def listener_logout(self, user, **kwargs):
        self.logged_out.append(user)

    def setUp(self):
        """Set up the listeners and reset the logged in/logged out counters"""
        self.logged_in = []
        self.logged_out = []
        signals.user_logged_in.connect(self.listener_login)
        signals.user_logged_out.connect(self.listener_logout)

    def tearDown(self):
        """Disconnect the listeners"""
        signals.user_logged_in.disconnect(self.listener_login)
        signals.user_logged_out.disconnect(self.listener_logout)

    def test_login(self):
        # Only a successful login will trigger the signal.
        self.client.login(username='testclient', password='bad')
        self.assertEqual(len(self.logged_in), 0)
        # Like this:
        self.client.login(username='testclient', password='password')
        self.assertEqual(len(self.logged_in), 1)
        self.assertEqual(self.logged_in[0].username, 'testclient')

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
