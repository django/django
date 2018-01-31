import warnings

from django.contrib.auth import authenticate
from django.test import SimpleTestCase, override_settings

mock_request = object()
mock_backend = object()


class NoRequestBackend(object):
    def authenticate(self, username=None, password=None):
        # Doesn't accept a request parameter.
        pass


class NoRequestWithKwargs:
    def authenticate(self, username=None, password=None, **kwargs):
        pass


class RequestPositionalArg:
    def authenticate(self, request, username=None, password=None, **kwargs):
        assert username == 'username'
        assert password == 'pass'
        assert request is mock_request


class RequestNotPositionArgBackend:
    def authenticate(self, username=None, password=None, request=None):
        assert username == 'username'
        assert password == 'pass'
        assert request is mock_request


class RequestNotPositionArgWithUsedKwargBackend:
    def authenticate(self, username=None, password=None, request=None, backend=None):
        assert username == 'username'
        assert password == 'pass'
        assert request is mock_request
        assert backend is mock_backend


class AcceptsRequestBackendTest(SimpleTestCase):
    """
    A deprecation warning is shown for backends that have an authenticate()
    method without a request parameter.
    """
    no_request_backend = '%s.NoRequestBackend' % __name__
    no_request_with_kwargs_backend = '%s.NoRequestWithKwargs' % __name__
    request_positional_arg_backend = '%s.RequestPositionalArg' % __name__
    request_not_positional_backend = '%s.RequestNotPositionArgBackend' % __name__
    request_not_positional_with_used_kwarg_backend = '%s.RequestNotPositionArgWithUsedKwargBackend' % __name__

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

    @override_settings(AUTHENTICATION_BACKENDS=[no_request_with_kwargs_backend, request_positional_arg_backend])
    def test_credentials_not_mutated(self):
        """
        No problem if a backend doesn't accept `request` and a later one does.
        """
        with warnings.catch_warnings(record=True) as warns:
            warnings.simplefilter('always')
            authenticate(mock_request, username='username', password='pass')
        self.assertEqual(len(warns), 1)
        self.assertEqual(
            str(warns[0].message),
            "In %s.authenticate(), move the `request` keyword argument to the "
            "first positional argument." % self.no_request_with_kwargs_backend
        )

    @override_settings(AUTHENTICATION_BACKENDS=[request_not_positional_with_used_kwarg_backend])
    def test_handles_backend_in_kwargs(self):
        with warnings.catch_warnings(record=True) as warns:
            warnings.simplefilter('always')
            authenticate(username='username', password='pass', request=mock_request, backend=mock_backend)
        self.assertEqual(len(warns), 1)
        self.assertEqual(
            str(warns[0].message),
            "In %s.authenticate(), move the `request` keyword argument to the "
            "first positional argument." % self.request_not_positional_with_used_kwarg_backend
        )
