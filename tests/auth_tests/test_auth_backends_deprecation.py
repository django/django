import warnings

from django.contrib.auth import authenticate
from django.test import SimpleTestCase, override_settings

mock_request = object()


class NoRequestBackend:
    def authenticate(self, username=None, password=None):
        # Doesn't accept a request parameter.
        pass


class RequestNotPositionArgBackend:
    def authenticate(self, username=None, password=None, request=None):
        assert username == 'username'
        assert password == 'pass'
        assert request is mock_request


class AcceptsRequestBackendTest(SimpleTestCase):
    """
    A deprecation warning is shown for backends that have an authenticate()
    method without a request parameter.
    """
    no_request_backend = '%s.NoRequestBackend' % __name__
    request_not_positional_backend = '%s.RequestNotPositionArgBackend' % __name__

    @override_settings(AUTHENTICATION_BACKENDS=[no_request_backend])
    def test_no_request_deprecation_warning(self):
        with warnings.catch_warnings(record=True) as warns:
            warnings.simplefilter('always')
            authenticate(username='test', password='test')
        self.assertEqual(len(warns), 1)
        self.assertEqual(
            str(warns[0].message),
            "Update %s.authenticate() to accept a positional `request` "
            "argument." % self.no_request_backend
        )

    @override_settings(AUTHENTICATION_BACKENDS=[request_not_positional_backend])
    def test_request_keyword_arg_deprecation_warning(self):
        with warnings.catch_warnings(record=True) as warns:
            warnings.simplefilter('always')
            authenticate(username='username', password='pass', request=mock_request)
        self.assertEqual(len(warns), 1)
        self.assertEqual(
            str(warns[0].message),
            "In %s.authenticate(), move the `request` keyword argument to the "
            "first positional argument." % self.request_not_positional_backend
        )

    @override_settings(AUTHENTICATION_BACKENDS=[request_not_positional_backend, no_request_backend])
    def test_both_types_of_deprecation_warning(self):
        with warnings.catch_warnings(record=True) as warns:
            warnings.simplefilter('always')
            authenticate(mock_request, username='username', password='pass')

        self.assertEqual(len(warns), 2)
        self.assertEqual(
            str(warns[0].message),
            "In %s.authenticate(), move the `request` keyword argument to the "
            "first positional argument." % self.request_not_positional_backend
        )
        self.assertEqual(
            str(warns[1].message),
            "Update %s.authenticate() to accept a positional `request` "
            "argument." % self.no_request_backend
        )
