from django.test import TestCase
from django.contrib.auth import models, management


class GetDefaultUsernameTestCase(TestCase):

    def setUp(self):
        self._getpass_getuser = management.get_system_username

    def tearDown(self):
        management.get_system_username = self._getpass_getuser

    def test_simple(self):
        management.get_system_username = lambda: u'joe'
        self.assertEqual(management.get_default_username(), 'joe')

    def test_existing(self):
        models.User.objects.create(username='joe')
        management.get_system_username = lambda: u'joe'
        self.assertEqual(management.get_default_username(), '')
        self.assertEqual(
            management.get_default_username(check_db=False), 'joe')

    def test_i18n(self):
        # 'Julia' with accented 'u':
        management.get_system_username = lambda: u'J\xfalia'
        self.assertEqual(management.get_default_username(), 'julia')
