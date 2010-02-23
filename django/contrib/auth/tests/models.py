from django.conf import settings
from django.test import TestCase
from django.contrib.auth.models import User, SiteProfileNotAvailable

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
