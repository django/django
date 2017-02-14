import logging
import re

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpRequest
from django.middleware.csrf import (
    CSRF_SESSION_KEY, CSRF_TOKEN_LENGTH, REASON_BAD_TOKEN,
    REASON_NO_CSRF_COOKIE, CsrfViewMiddleware,
    _compare_salted_tokens as equivalent_tokens, get_token,
)
from django.test import SimpleTestCase, override_settings
from django.test.utils import patch_logger
from django.views.decorators.csrf import csrf_exempt, requires_csrf_token

from .views import (
    ensure_csrf_cookie_view, non_token_view_using_request_processor,
    post_form_view, token_view,
)


class TestingHttpRequest(HttpRequest):
    """
    A version of HttpRequest that allows us to change some things
    more easily
    """
    def __init__(self):
        super().__init__()
        # A real session backend isn't needed.
        self.session = {}

    def is_secure(self):
        return getattr(self, '_is_secure_override', False)


class CsrfViewMiddlewareTestMixin:
    """
    Shared methods and tests for session-based and cookie-based tokens.
    """

    _csrf_id = _csrf_id_cookie = '1bcdefghij2bcdefghij3bcdefghij4bcdefghij5bcdefghij6bcdefghijABCD'

    def _get_GET_no_csrf_cookie_request(self):
        return TestingHttpRequest()

    def _get_GET_csrf_cookie_request(self):
        raise NotImplementedError('This method must be implemented by a subclass.')

    def _get_POST_csrf_cookie_request(self):
        req = self._get_GET_csrf_cookie_request()
        req.method = "POST"
        return req

    def _get_POST_no_csrf_cookie_request(self):
        req = self._get_GET_no_csrf_cookie_request()
        req.method = "POST"
        return req

    def _get_POST_request_with_token(self):
        req = self._get_POST_csrf_cookie_request()
        req.POST['csrfmiddlewaretoken'] = self._csrf_id
        return req

    def _check_token_present(self, response, csrf_id=None):
        text = str(response.content, response.charset)
        match = re.search("name='csrfmiddlewaretoken' value='(.*?)'", text)
        csrf_token = csrf_id or self._csrf_id
        self.assertTrue(
            match and equivalent_tokens(csrf_token, match.group(1)),
            "Could not find csrfmiddlewaretoken to match %s" % csrf_token
        )

    def test_process_response_get_token_not_used(self):
        """
        If get_token() is not called, the view middleware does not
        add a cookie.
        """
        # This is important to make pages cacheable.  Pages which do call
        # get_token(), assuming they use the token, are not cacheable because
        # the token is specific to the user
        req = self._get_GET_no_csrf_cookie_request()
        # non_token_view_using_request_processor does not call get_token(), but
        # does use the csrf request processor.  By using this, we are testing
        # that the view processor is properly lazy and doesn't call get_token()
        # until needed.
        CsrfViewMiddleware().process_view(req, non_token_view_using_request_processor, (), {})
        resp = non_token_view_using_request_processor(req)
        resp2 = CsrfViewMiddleware().process_response(req, resp)

        csrf_cookie = resp2.cookies.get(settings.CSRF_COOKIE_NAME, False)
        self.assertIs(csrf_cookie, False)

    # Check the request processing
    def test_process_request_no_csrf_cookie(self):
        """
        If no CSRF cookies is present, the middleware rejects the incoming
        request. This will stop login CSRF.
        """
        with patch_logger('django.security.csrf', 'warning') as logger_calls:
            req = self._get_POST_no_csrf_cookie_request()
            req2 = CsrfViewMiddleware().process_view(req, post_form_view, (), {})
            self.assertEqual(403, req2.status_code)
            self.assertEqual(logger_calls[0], 'Forbidden (%s): ' % REASON_NO_CSRF_COOKIE)

    def test_process_request_csrf_cookie_no_token(self):
        """
        If a CSRF cookie is present but no token, the middleware rejects
        the incoming request.
        """
        with patch_logger('django.security.csrf', 'warning') as logger_calls:
            req = self._get_POST_csrf_cookie_request()
            req2 = CsrfViewMiddleware().process_view(req, post_form_view, (), {})
            self.assertEqual(403, req2.status_code)
            self.assertEqual(logger_calls[0], 'Forbidden (%s): ' % REASON_BAD_TOKEN)

    def test_process_request_csrf_cookie_and_token(self):
        """
        If both a cookie and a token is present, the middleware lets it through.
        """
        req = self._get_POST_request_with_token()
        req2 = CsrfViewMiddleware().process_view(req, post_form_view, (), {})
        self.assertIsNone(req2)

    def test_process_request_csrf_cookie_no_token_exempt_view(self):
        """
        If a CSRF cookie is present and no token, but the csrf_exempt decorator
        has been applied to the view, the middleware lets it through
        """
        req = self._get_POST_csrf_cookie_request()
        req2 = CsrfViewMiddleware().process_view(req, csrf_exempt(post_form_view), (), {})
        self.assertIsNone(req2)

    def test_csrf_token_in_header(self):
        """
        The token may be passed in a header instead of in the form.
        """
        req = self._get_POST_csrf_cookie_request()
        req.META['HTTP_X_CSRFTOKEN'] = self._csrf_id
        req2 = CsrfViewMiddleware().process_view(req, post_form_view, (), {})
        self.assertIsNone(req2)

    @override_settings(CSRF_HEADER_NAME='HTTP_X_CSRFTOKEN_CUSTOMIZED')
    def test_csrf_token_in_header_with_customized_name(self):
        """
        settings.CSRF_HEADER_NAME can be used to customize the CSRF header name
        """
        req = self._get_POST_csrf_cookie_request()
        req.META['HTTP_X_CSRFTOKEN_CUSTOMIZED'] = self._csrf_id
        req2 = CsrfViewMiddleware().process_view(req, post_form_view, (), {})
        self.assertIsNone(req2)

    def test_put_and_delete_rejected(self):
        """
        HTTP PUT and DELETE methods have protection
        """
        req = TestingHttpRequest()
        req.method = 'PUT'
        with patch_logger('django.security.csrf', 'warning') as logger_calls:
            req2 = CsrfViewMiddleware().process_view(req, post_form_view, (), {})
            self.assertEqual(403, req2.status_code)
            self.assertEqual(logger_calls[0], 'Forbidden (%s): ' % REASON_NO_CSRF_COOKIE)

        req = TestingHttpRequest()
        req.method = 'DELETE'
        with patch_logger('django.security.csrf', 'warning') as logger_calls:
            req2 = CsrfViewMiddleware().process_view(req, post_form_view, (), {})
            self.assertEqual(403, req2.status_code)
            self.assertEqual(logger_calls[0], 'Forbidden (%s): ' % REASON_NO_CSRF_COOKIE)

    def test_put_and_delete_allowed(self):
        """
        HTTP PUT and DELETE can get through with X-CSRFToken and a cookie.
        """
        req = self._get_GET_csrf_cookie_request()
        req.method = 'PUT'
        req.META['HTTP_X_CSRFTOKEN'] = self._csrf_id
        req2 = CsrfViewMiddleware().process_view(req, post_form_view, (), {})
        self.assertIsNone(req2)

        req = self._get_GET_csrf_cookie_request()
        req.method = 'DELETE'
        req.META['HTTP_X_CSRFTOKEN'] = self._csrf_id
        req2 = CsrfViewMiddleware().process_view(req, post_form_view, (), {})
        self.assertIsNone(req2)

    # Tests for the template tag method
    def test_token_node_no_csrf_cookie(self):
        """
        CsrfTokenNode works when no CSRF cookie is set.
        """
        req = self._get_GET_no_csrf_cookie_request()
        resp = token_view(req)

        token = get_token(req)
        self.assertIsNotNone(token)
        self._check_token_present(resp, token)

    def test_token_node_empty_csrf_cookie(self):
        """
        A new token is sent if the csrf_cookie is the empty string.
        """
        req = self._get_GET_no_csrf_cookie_request()
        req.COOKIES[settings.CSRF_COOKIE_NAME] = ""
        CsrfViewMiddleware().process_view(req, token_view, (), {})
        resp = token_view(req)

        token = get_token(req)
        self.assertIsNotNone(token)
        self._check_token_present(resp, token)

    def test_token_node_with_csrf_cookie(self):
        """
        CsrfTokenNode works when a CSRF cookie is set.
        """
        req = self._get_GET_csrf_cookie_request()
        CsrfViewMiddleware().process_view(req, token_view, (), {})
        resp = token_view(req)
        self._check_token_present(resp)

    def test_get_token_for_exempt_view(self):
        """
        get_token still works for a view decorated with 'csrf_exempt'.
        """
        req = self._get_GET_csrf_cookie_request()
        CsrfViewMiddleware().process_view(req, csrf_exempt(token_view), (), {})
        resp = token_view(req)
        self._check_token_present(resp)

    def test_get_token_for_requires_csrf_token_view(self):
        """
        get_token() works for a view decorated solely with requires_csrf_token.
        """
        req = self._get_GET_csrf_cookie_request()
        resp = requires_csrf_token(token_view)(req)
        self._check_token_present(resp)

    def test_token_node_with_new_csrf_cookie(self):
        """
        CsrfTokenNode works when a CSRF cookie is created by
        the middleware (when one was not already present)
        """
        req = self._get_GET_no_csrf_cookie_request()
        CsrfViewMiddleware().process_view(req, token_view, (), {})
        resp = token_view(req)
        resp2 = CsrfViewMiddleware().process_response(req, resp)
        csrf_cookie = resp2.cookies[settings.CSRF_COOKIE_NAME]
        self._check_token_present(resp, csrf_id=csrf_cookie.value)

    def test_cookie_not_reset_on_accepted_request(self):
        """
        The csrf token used in posts is changed on every request (although
        stays equivalent). The csrf cookie should not change on accepted
        requests. If it appears in the response, it should keep its value.
        """
        req = self._get_POST_request_with_token()
        CsrfViewMiddleware().process_view(req, token_view, (), {})
        resp = token_view(req)
        resp = CsrfViewMiddleware().process_response(req, resp)
        csrf_cookie = resp.cookies.get(settings.CSRF_COOKIE_NAME, None)
        if csrf_cookie:
            self.assertEqual(
                csrf_cookie.value, self._csrf_id_cookie,
                "CSRF cookie was changed on an accepted request"
            )

    @override_settings(DEBUG=True, ALLOWED_HOSTS=['www.example.com'])
    def test_https_bad_referer(self):
        """
        A POST HTTPS request with a bad referer is rejected
        """
        req = self._get_POST_request_with_token()
        req._is_secure_override = True
        req.META['HTTP_HOST'] = 'www.example.com'
        req.META['HTTP_REFERER'] = 'https://www.evil.org/somepage'
        req.META['SERVER_PORT'] = '443'
        response = CsrfViewMiddleware().process_view(req, post_form_view, (), {})
        self.assertContains(
            response,
            'Referer checking failed - https://www.evil.org/somepage does not '
            'match any trusted origins.',
            status_code=403,
        )

    @override_settings(DEBUG=True)
    def test_https_malformed_referer(self):
        """
        A POST HTTPS request with a bad referer is rejected.
        """
        malformed_referer_msg = 'Referer checking failed - Referer is malformed.'
        req = self._get_POST_request_with_token()
        req._is_secure_override = True
        req.META['HTTP_REFERER'] = 'http://http://www.example.com/'
        response = CsrfViewMiddleware().process_view(req, post_form_view, (), {})
        self.assertContains(
            response,
            'Referer checking failed - Referer is insecure while host is secure.',
            status_code=403,
        )
        # Empty
        req.META['HTTP_REFERER'] = ''
        response = CsrfViewMiddleware().process_view(req, post_form_view, (), {})
        self.assertContains(response, malformed_referer_msg, status_code=403)
        # Non-ASCII
        req.META['HTTP_REFERER'] = 'ØBöIß'
        response = CsrfViewMiddleware().process_view(req, post_form_view, (), {})
        self.assertContains(response, malformed_referer_msg, status_code=403)
        # missing scheme
        # >>> urlparse('//example.com/')
        # ParseResult(scheme='', netloc='example.com', path='/', params='', query='', fragment='')
        req.META['HTTP_REFERER'] = '//example.com/'
        response = CsrfViewMiddleware().process_view(req, post_form_view, (), {})
        self.assertContains(response, malformed_referer_msg, status_code=403)
        # missing netloc
        # >>> urlparse('https://')
        # ParseResult(scheme='https', netloc='', path='', params='', query='', fragment='')
        req.META['HTTP_REFERER'] = 'https://'
        response = CsrfViewMiddleware().process_view(req, post_form_view, (), {})
        self.assertContains(response, malformed_referer_msg, status_code=403)

    @override_settings(ALLOWED_HOSTS=['www.example.com'])
    def test_https_good_referer(self):
        """
        A POST HTTPS request with a good referer is accepted.
        """
        req = self._get_POST_request_with_token()
        req._is_secure_override = True
        req.META['HTTP_HOST'] = 'www.example.com'
        req.META['HTTP_REFERER'] = 'https://www.example.com/somepage'
        req2 = CsrfViewMiddleware().process_view(req, post_form_view, (), {})
        self.assertIsNone(req2)

    @override_settings(ALLOWED_HOSTS=['www.example.com'])
    def test_https_good_referer_2(self):
        """
        A POST HTTPS request with a good referer is accepted where the referer
        contains no trailing slash.
        """
        # See ticket #15617
        req = self._get_POST_request_with_token()
        req._is_secure_override = True
        req.META['HTTP_HOST'] = 'www.example.com'
        req.META['HTTP_REFERER'] = 'https://www.example.com'
        req2 = CsrfViewMiddleware().process_view(req, post_form_view, (), {})
        self.assertIsNone(req2)

    def _test_https_good_referer_behind_proxy(self):
        req = self._get_POST_request_with_token()
        req._is_secure_override = True
        req.META.update({
            'HTTP_HOST': '10.0.0.2',
            'HTTP_REFERER': 'https://www.example.com/somepage',
            'SERVER_PORT': '8080',
            'HTTP_X_FORWARDED_HOST': 'www.example.com',
            'HTTP_X_FORWARDED_PORT': '443',
        })
        req2 = CsrfViewMiddleware().process_view(req, post_form_view, (), {})
        self.assertIsNone(req2)

    @override_settings(ALLOWED_HOSTS=['www.example.com'], CSRF_TRUSTED_ORIGINS=['dashboard.example.com'])
    def test_https_csrf_trusted_origin_allowed(self):
        """
        A POST HTTPS request with a referer added to the CSRF_TRUSTED_ORIGINS
        setting is accepted.
        """
        req = self._get_POST_request_with_token()
        req._is_secure_override = True
        req.META['HTTP_HOST'] = 'www.example.com'
        req.META['HTTP_REFERER'] = 'https://dashboard.example.com'
        req2 = CsrfViewMiddleware().process_view(req, post_form_view, (), {})
        self.assertIsNone(req2)

    @override_settings(ALLOWED_HOSTS=['www.example.com'], CSRF_TRUSTED_ORIGINS=['.example.com'])
    def test_https_csrf_wildcard_trusted_origin_allowed(self):
        """
        A POST HTTPS request with a referer that matches a CSRF_TRUSTED_ORIGINS
        wildcard is accepted.
        """
        req = self._get_POST_request_with_token()
        req._is_secure_override = True
        req.META['HTTP_HOST'] = 'www.example.com'
        req.META['HTTP_REFERER'] = 'https://dashboard.example.com'
        response = CsrfViewMiddleware().process_view(req, post_form_view, (), {})
        self.assertIsNone(response)

    def _test_https_good_referer_matches_cookie_domain(self):
        req = self._get_POST_request_with_token()
        req._is_secure_override = True
        req.META['HTTP_REFERER'] = 'https://foo.example.com/'
        req.META['SERVER_PORT'] = '443'
        response = CsrfViewMiddleware().process_view(req, post_form_view, (), {})
        self.assertIsNone(response)

    def _test_https_good_referer_matches_cookie_domain_with_different_port(self):
        req = self._get_POST_request_with_token()
        req._is_secure_override = True
        req.META['HTTP_HOST'] = 'www.example.com'
        req.META['HTTP_REFERER'] = 'https://foo.example.com:4443/'
        req.META['SERVER_PORT'] = '4443'
        response = CsrfViewMiddleware().process_view(req, post_form_view, (), {})
        self.assertIsNone(response)

    def test_ensures_csrf_cookie_no_logging(self):
        """
        ensure_csrf_cookie() doesn't log warnings (#19436).
        """
        class TestHandler(logging.Handler):
            def emit(self, record):
                raise Exception("This shouldn't have happened!")

        logger = logging.getLogger('django.request')
        test_handler = TestHandler()
        old_log_level = logger.level
        try:
            logger.addHandler(test_handler)
            logger.setLevel(logging.WARNING)

            req = self._get_GET_no_csrf_cookie_request()
            ensure_csrf_cookie_view(req)
        finally:
            logger.removeHandler(test_handler)
            logger.setLevel(old_log_level)

    def test_post_data_read_failure(self):
        """
        #20128 -- IOErrors during POST data reading should be caught and
        treated as if the POST data wasn't there.
        """
        class CsrfPostRequest(HttpRequest):
            """
            HttpRequest that can raise an IOError when accessing POST data
            """
            def __init__(self, token, raise_error):
                super().__init__()
                self.method = 'POST'

                self.raise_error = False
                self.COOKIES[settings.CSRF_COOKIE_NAME] = token

                # Handle both cases here to prevent duplicate code in the
                # session tests.
                self.session = {}
                self.session[CSRF_SESSION_KEY] = token

                self.POST['csrfmiddlewaretoken'] = token
                self.raise_error = raise_error

            def _load_post_and_files(self):
                raise IOError('error reading input data')

            def _get_post(self):
                if self.raise_error:
                    self._load_post_and_files()
                return self._post

            def _set_post(self, post):
                self._post = post

            POST = property(_get_post, _set_post)

        token = ('ABC' + self._csrf_id)[:CSRF_TOKEN_LENGTH]

        req = CsrfPostRequest(token, raise_error=False)
        resp = CsrfViewMiddleware().process_view(req, post_form_view, (), {})
        self.assertIsNone(resp)

        req = CsrfPostRequest(token, raise_error=True)
        with patch_logger('django.security.csrf', 'warning') as logger_calls:
            resp = CsrfViewMiddleware().process_view(req, post_form_view, (), {})
            self.assertEqual(resp.status_code, 403)
            self.assertEqual(logger_calls[0], 'Forbidden (%s): ' % REASON_BAD_TOKEN)


class CsrfViewMiddlewareTests(CsrfViewMiddlewareTestMixin, SimpleTestCase):

    def _get_GET_csrf_cookie_request(self):
        req = TestingHttpRequest()
        req.COOKIES[settings.CSRF_COOKIE_NAME] = self._csrf_id_cookie
        return req

    def _get_POST_bare_secret_csrf_cookie_request(self):
        req = self._get_POST_no_csrf_cookie_request()
        req.COOKIES[settings.CSRF_COOKIE_NAME] = self._csrf_id_cookie[:32]
        return req

    def _get_POST_bare_secret_csrf_cookie_request_with_token(self):
        req = self._get_POST_bare_secret_csrf_cookie_request()
        req.POST['csrfmiddlewaretoken'] = self._csrf_id_cookie[:32]
        return req

    def test_ensures_csrf_cookie_no_middleware(self):
        """
        The ensure_csrf_cookie() decorator works without middleware.
        """
        req = self._get_GET_no_csrf_cookie_request()
        resp = ensure_csrf_cookie_view(req)
        self.assertTrue(resp.cookies.get(settings.CSRF_COOKIE_NAME, False))
        self.assertIn('Cookie', resp.get('Vary', ''))

    def test_ensures_csrf_cookie_with_middleware(self):
        """
        The ensure_csrf_cookie() decorator works with the CsrfViewMiddleware
        enabled.
        """
        req = self._get_GET_no_csrf_cookie_request()
        CsrfViewMiddleware().process_view(req, ensure_csrf_cookie_view, (), {})
        resp = ensure_csrf_cookie_view(req)
        resp2 = CsrfViewMiddleware().process_response(req, resp)
        self.assertTrue(resp2.cookies.get(settings.CSRF_COOKIE_NAME, False))
        self.assertIn('Cookie', resp2.get('Vary', ''))

    def test_csrf_cookie_age(self):
        """
        CSRF cookie age can be set using settings.CSRF_COOKIE_AGE.
        """
        req = self._get_GET_no_csrf_cookie_request()

        MAX_AGE = 123
        with self.settings(CSRF_COOKIE_NAME='csrfcookie',
                           CSRF_COOKIE_DOMAIN='.example.com',
                           CSRF_COOKIE_AGE=MAX_AGE,
                           CSRF_COOKIE_PATH='/test/',
                           CSRF_COOKIE_SECURE=True,
                           CSRF_COOKIE_HTTPONLY=True):
            # token_view calls get_token() indirectly
            CsrfViewMiddleware().process_view(req, token_view, (), {})
            resp = token_view(req)

            resp2 = CsrfViewMiddleware().process_response(req, resp)
            max_age = resp2.cookies.get('csrfcookie').get('max-age')
            self.assertEqual(max_age, MAX_AGE)

    def test_csrf_cookie_age_none(self):
        """
        CSRF cookie age does not have max age set and therefore uses
        session-based cookies.
        """
        req = self._get_GET_no_csrf_cookie_request()

        MAX_AGE = None
        with self.settings(CSRF_COOKIE_NAME='csrfcookie',
                           CSRF_COOKIE_DOMAIN='.example.com',
                           CSRF_COOKIE_AGE=MAX_AGE,
                           CSRF_COOKIE_PATH='/test/',
                           CSRF_COOKIE_SECURE=True,
                           CSRF_COOKIE_HTTPONLY=True):
            # token_view calls get_token() indirectly
            CsrfViewMiddleware().process_view(req, token_view, (), {})
            resp = token_view(req)

            resp2 = CsrfViewMiddleware().process_response(req, resp)
            max_age = resp2.cookies.get('csrfcookie').get('max-age')
            self.assertEqual(max_age, '')

    def test_process_view_token_too_long(self):
        """
        If the token is longer than expected, it is ignored and a new token is
        created.
        """
        req = self._get_GET_no_csrf_cookie_request()
        req.COOKIES[settings.CSRF_COOKIE_NAME] = 'x' * 100000
        CsrfViewMiddleware().process_view(req, token_view, (), {})
        resp = token_view(req)
        resp2 = CsrfViewMiddleware().process_response(req, resp)
        csrf_cookie = resp2.cookies.get(settings.CSRF_COOKIE_NAME, False)
        self.assertEqual(len(csrf_cookie.value), CSRF_TOKEN_LENGTH)

    def test_process_view_token_invalid_chars(self):
        """
        If the token contains non-alphanumeric characters, it is ignored and a
        new token is created.
        """
        token = ('!@#' + self._csrf_id)[:CSRF_TOKEN_LENGTH]
        req = self._get_GET_no_csrf_cookie_request()
        req.COOKIES[settings.CSRF_COOKIE_NAME] = token
        CsrfViewMiddleware().process_view(req, token_view, (), {})
        resp = token_view(req)
        resp2 = CsrfViewMiddleware().process_response(req, resp)
        csrf_cookie = resp2.cookies.get(settings.CSRF_COOKIE_NAME, False)
        self.assertEqual(len(csrf_cookie.value), CSRF_TOKEN_LENGTH)
        self.assertNotEqual(csrf_cookie.value, token)

    def test_bare_secret_accepted_and_replaced(self):
        """
        The csrf token is reset from a bare secret.
        """
        req = self._get_POST_bare_secret_csrf_cookie_request_with_token()
        req2 = CsrfViewMiddleware().process_view(req, token_view, (), {})
        self.assertIsNone(req2)
        resp = token_view(req)
        resp = CsrfViewMiddleware().process_response(req, resp)
        self.assertIn(settings.CSRF_COOKIE_NAME, resp.cookies, "Cookie was not reset from bare secret")
        csrf_cookie = resp.cookies[settings.CSRF_COOKIE_NAME]
        self.assertEqual(len(csrf_cookie.value), CSRF_TOKEN_LENGTH)
        self._check_token_present(resp, csrf_id=csrf_cookie.value)

    @override_settings(ALLOWED_HOSTS=['www.example.com'], CSRF_COOKIE_DOMAIN='.example.com', USE_X_FORWARDED_PORT=True)
    def test_https_good_referer_behind_proxy(self):
        """
        A POST HTTPS request is accepted when USE_X_FORWARDED_PORT=True.
        """
        self._test_https_good_referer_behind_proxy()

    @override_settings(ALLOWED_HOSTS=['www.example.com'], CSRF_COOKIE_DOMAIN='.example.com')
    def test_https_good_referer_matches_cookie_domain(self):
        """
        A POST HTTPS request with a good referer should be accepted from a
        subdomain that's allowed by CSRF_COOKIE_DOMAIN.
        """
        self._test_https_good_referer_matches_cookie_domain()

    @override_settings(ALLOWED_HOSTS=['www.example.com'], CSRF_COOKIE_DOMAIN='.example.com')
    def test_https_good_referer_matches_cookie_domain_with_different_port(self):
        """
        A POST HTTPS request with a good referer should be accepted from a
        subdomain that's allowed by CSRF_COOKIE_DOMAIN and a non-443 port.
        """
        self._test_https_good_referer_matches_cookie_domain_with_different_port()

    @override_settings(CSRF_COOKIE_DOMAIN='.example.com', DEBUG=True)
    def test_https_reject_insecure_referer(self):
        """
        A POST HTTPS request from an insecure referer should be rejected.
        """
        req = self._get_POST_request_with_token()
        req._is_secure_override = True
        req.META['HTTP_REFERER'] = 'http://example.com/'
        req.META['SERVER_PORT'] = '443'
        response = CsrfViewMiddleware().process_view(req, post_form_view, (), {})
        self.assertContains(
            response,
            'Referer checking failed - Referer is insecure while host is secure.',
            status_code=403,
        )


@override_settings(CSRF_USE_SESSIONS=True, CSRF_COOKIE_DOMAIN=None)
class CsrfViewMiddlewareUseSessionsTests(CsrfViewMiddlewareTestMixin, SimpleTestCase):
    """
    CSRF tests with CSRF_USE_SESSIONS=True.
    """

    def _get_POST_bare_secret_csrf_cookie_request(self):
        req = self._get_POST_no_csrf_cookie_request()
        req.session[CSRF_SESSION_KEY] = self._csrf_id_cookie[:32]
        return req

    def _get_GET_csrf_cookie_request(self):
        req = TestingHttpRequest()
        req.session[CSRF_SESSION_KEY] = self._csrf_id_cookie
        return req

    def test_no_session_on_request(self):
        msg = (
            'CSRF_USE_SESSIONS is enabled, but request.session is not set. '
            'SessionMiddleware must appear before CsrfViewMiddleware in MIDDLEWARE.'
        )
        with self.assertRaisesMessage(ImproperlyConfigured, msg):
            CsrfViewMiddleware().process_view(HttpRequest(), None, (), {})

    def test_process_response_get_token_used(self):
        """The ensure_csrf_cookie() decorator works without middleware."""
        req = self._get_GET_no_csrf_cookie_request()
        ensure_csrf_cookie_view(req)
        self.assertTrue(req.session.get(CSRF_SESSION_KEY, False))

    def test_ensures_csrf_cookie_with_middleware(self):
        """
        The ensure_csrf_cookie() decorator works with the CsrfViewMiddleware
        enabled.
        """
        req = self._get_GET_no_csrf_cookie_request()
        CsrfViewMiddleware().process_view(req, ensure_csrf_cookie_view, (), {})
        resp = ensure_csrf_cookie_view(req)
        CsrfViewMiddleware().process_response(req, resp)
        self.assertTrue(req.session.get(CSRF_SESSION_KEY, False))

    def test_token_node_with_new_csrf_cookie(self):
        """
        CsrfTokenNode works when a CSRF cookie is created by the middleware
        (when one was not already present).
        """
        req = self._get_GET_no_csrf_cookie_request()
        CsrfViewMiddleware().process_view(req, token_view, (), {})
        resp = token_view(req)
        CsrfViewMiddleware().process_response(req, resp)
        csrf_cookie = req.session[CSRF_SESSION_KEY]
        self._check_token_present(resp, csrf_id=csrf_cookie)

    @override_settings(
        ALLOWED_HOSTS=['www.example.com'],
        SESSION_COOKIE_DOMAIN='.example.com',
        USE_X_FORWARDED_PORT=True,
        DEBUG=True,
    )
    def test_https_good_referer_behind_proxy(self):
        """
        A POST HTTPS request is accepted when USE_X_FORWARDED_PORT=True.
        """
        self._test_https_good_referer_behind_proxy()

    @override_settings(ALLOWED_HOSTS=['www.example.com'], SESSION_COOKIE_DOMAIN='.example.com')
    def test_https_good_referer_matches_cookie_domain(self):
        """
        A POST HTTPS request with a good referer should be accepted from a
        subdomain that's allowed by SESSION_COOKIE_DOMAIN.
        """
        self._test_https_good_referer_matches_cookie_domain()

    @override_settings(ALLOWED_HOSTS=['www.example.com'], SESSION_COOKIE_DOMAIN='.example.com')
    def test_https_good_referer_matches_cookie_domain_with_different_port(self):
        """
        A POST HTTPS request with a good referer should be accepted from a
        subdomain that's allowed by SESSION_COOKIE_DOMAIN and a non-443 port.
        """
        self._test_https_good_referer_matches_cookie_domain_with_different_port()

    @override_settings(SESSION_COOKIE_DOMAIN='.example.com', DEBUG=True)
    def test_https_reject_insecure_referer(self):
        """
        A POST HTTPS request from an insecure referer should be rejected.
        """
        req = self._get_POST_request_with_token()
        req._is_secure_override = True
        req.META['HTTP_REFERER'] = 'http://example.com/'
        req.META['SERVER_PORT'] = '443'
        response = CsrfViewMiddleware().process_view(req, post_form_view, (), {})
        self.assertContains(
            response,
            'Referer checking failed - Referer is insecure while host is secure.',
            status_code=403,
        )
