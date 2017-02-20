import warnings

from django.contrib.auth import authenticate
from django.test import SimpleTestCase, override_settings


class NoRequestBackend:
    def authenticate(self, username=None, password=None):
        # Doesn't accept a request parameter.
        pass


class AcceptsRequestBackendTest(SimpleTestCase):
    """
    A deprecation warning is shown for backends that have an authenticate()
    method without a request parameter.
    """
    no_request_backend = '%s.NoRequestBackend' % __name__

    @override_settings(AUTHENTICATION_BACKENDS=[no_request_backend])
    def test_no_request_deprecation_warning(self):
        with warnings.catch_warnings(record=True) as warns:
            warnings.simplefilter('always')
            authenticate(username='test', password='test')
        self.assertEqual(len(warns), 1)
        self.assertEqual(
            str(warns[0].message),
            "Update authentication backend %s to accept a positional `request` "
            "argument." % self.no_request_backend
        )
