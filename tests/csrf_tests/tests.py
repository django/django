# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
import re
import warnings

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.middleware.csrf import (
    CSRF_TOKEN_LENGTH, CsrfViewMiddleware,
    _compare_salted_tokens as equivalent_tokens, get_token,
)
from django.template import RequestContext, Template
from django.template.context_processors import csrf
from django.test import SimpleTestCase, override_settings
from django.utils.encoding import force_bytes
from django.utils.six import text_type
from django.views.decorators.csrf import (
    csrf_exempt, ensure_csrf_cookie, requires_csrf_token,
)


# Response/views used for CsrfResponseMiddleware and CsrfViewMiddleware tests
def post_form_response():
    resp = HttpResponse(content="""
<html><body><h1>\u00a1Unicode!<form method="post"><input type="text" /></form></body></html>
""", mimetype="text/html")
    return resp


def post_form_view(request):
    """A view that returns a POST form (without a token)"""
    return post_form_response()


# Response/views used for template tag tests

def token_view(request):
    """A view that uses {% csrf_token %}"""
    context = RequestContext(request, processors=[csrf])
    template = Template("{% csrf_token %}")
    return HttpResponse(template.render(context))


def non_token_view_using_request_processor(request):
    """
    A view that doesn't use the token, but does use the csrf view processor.
    """
    context = RequestContext(request, processors=[csrf])
    template = Template("")
    return HttpResponse(template.render(context))


class TestingHttpRequest(HttpRequest):
    """
    A version of HttpRequest that allows us to change some things
    more easily
    """
    def is_secure(self):
        return getattr(self, '_is_secure_override', False)


class CsrfViewMiddlewareTest(SimpleTestCase):
    _csrf_id = _csrf_id_cookie = '1bcdefghij2bcdefghij3bcdefghij4bcdefghij5bcdefghij6bcdefghijABCD'

    def _get_GET_no_csrf_cookie_request(self):
        return TestingHttpRequest()

    def _get_GET_csrf_cookie_request(self):
        req = TestingHttpRequest()
        req.COOKIES[settings.CSRF_COOKIE_NAME] = self._csrf_id_cookie
        return req

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

    def _get_POST_bare_secret_csrf_cookie_request(self):
        req = self._get_POST_no_csrf_cookie_request()
        req.COOKIES[settings.CSRF_COOKIE_NAME] = self._csrf_id_cookie[:32]
        return req

    def _get_POST_bare_secret_csrf_cookie_request_with_token(self):
        req = self._get_POST_bare_secret_csrf_cookie_request()
        req.POST['csrfmiddlewaretoken'] = self._csrf_id_cookie[:32]
        return req

    def _check_token_present(self, response, csrf_id=None):
        text = text_type(response.content, response.charset)
        match = re.search("name='csrfmiddlewaretoken' value='(.*?)'", text)
        csrf_token = csrf_id or self._csrf_id
        self.assertTrue(
            match and equivalent_tokens(csrf_token, match.group(1)),
            "Could not find csrfmiddlewaretoken to match %s" % csrf_token
        )

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

    def test_process_view_token_invalid_bytes(self):
        """
        If the token contains improperly encoded unicode, it is ignored and a
        new token is created.
        """
        token = (b"<1>\xc2\xa1" + force_bytes(self._csrf_id, 'ascii'))[:CSRF_TOKEN_LENGTH]
        req = self._get_GET_no_csrf_cookie_request()
        req.COOKIES[settings.CSRF_COOKIE_NAME] = token
        # We expect a UnicodeWarning here, because we used broken utf-8 on purpose
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=UnicodeWarning)
            CsrfViewMiddleware().process_view(req, token_view, (), {})
        resp = token_view(req)
        resp2 = CsrfViewMiddleware().process_response(req, resp)
        csrf_cookie = resp2.cookies.get(settings.CSRF_COOKIE_NAME, False)
        self.assertEqual(len(csrf_cookie.value), CSRF_TOKEN_LENGTH)
        self.assertNotEqual(csrf_cookie.value, token)

    def test_process_response_get_token_used(self):
        """
        When get_token is used, check that the cookie is created and headers
        patched.
        """
        req = self._get_GET_no_csrf_cookie_request()

        # Put tests for CSRF_COOKIE_* settings here
        with self.settings(CSRF_COOKIE_NAME='myname',
                           CSRF_COOKIE_DOMAIN='.example.com',
                           CSRF_COOKIE_PATH='/test/',
                           CSRF_COOKIE_SECURE=True,
                           CSRF_COOKIE_HTTPONLY=True):
            # token_view calls get_token() indirectly
            CsrfViewMiddleware().process_view(req, token_view, (), {})
            resp = token_view(req)
            resp2 = CsrfViewMiddleware().process_response(req, resp)
        csrf_cookie = resp2.cookies.get('myname', False)
        self.assertNotEqual(csrf_cookie, False)
        self.assertEqual(csrf_cookie['domain'], '.example.com')
        self.assertEqual(csrf_cookie['secure'], True)
        self.assertEqual(csrf_cookie['httponly'], True)
        self.assertEqual(csrf_cookie['path'], '/test/')
        self.assertIn('Cookie', resp2.get('Vary', ''))

    def test_process_response_get_token_not_used(self):
        """
        Check that if get_token() is not called, the view middleware does not
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
        self.assertEqual(csrf_cookie, False)

    # Check the request processing
    def test_process_request_no_csrf_cookie(self):
        """
        Check that if no CSRF cookies is present, the middleware rejects the
        incoming request.  This will stop login CSRF.
        """
        req = self._get_POST_no_csrf_cookie_request()
        req2 = CsrfViewMiddleware().process_view(req, post_form_view, (), {})
        self.assertEqual(403, req2.status_code)

    def test_process_request_csrf_cookie_no_token(self):
        """
        Check that if a CSRF cookie is present but no token, the middleware
        rejects the incoming request.
        """
        req = self._get_POST_csrf_cookie_request()
        req2 = CsrfViewMiddleware().process_view(req, post_form_view, (), {})
        self.assertEqual(403, req2.status_code)

    def test_process_request_csrf_cookie_and_token(self):
        """
        Check that if both a cookie and a token is present, the middleware lets it through.
        """
        req = self._get_POST_request_with_token()
        req2 = CsrfViewMiddleware().process_view(req, post_form_view, (), {})
        self.assertIsNone(req2)

    def test_process_request_csrf_cookie_no_token_exempt_view(self):
        """
        Check that if a CSRF cookie is present and no token, but the csrf_exempt
        decorator has been applied to the view, the middleware lets it through
        """
        req = self._get_POST_csrf_cookie_request()
        req2 = CsrfViewMiddleware().process_view(req, csrf_exempt(post_form_view), (), {})
        self.assertIsNone(req2)

    def test_csrf_token_in_header(self):
        """
        Check that we can pass in the token in a header instead of in the form
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
        Tests that HTTP PUT and DELETE methods have protection
        """
        req = TestingHttpRequest()
        req.method = 'PUT'
        req2 = CsrfViewMiddleware().process_view(req, post_form_view, (), {})
        self.assertEqual(403, req2.status_code)

        req = TestingHttpRequest()
        req.method = 'DELETE'
        req2 = CsrfViewMiddleware().process_view(req, post_form_view, (), {})
        self.assertEqual(403, req2.status_code)

    def test_put_and_delete_allowed(self):
        """
        Tests that HTTP PUT and DELETE methods can get through with
        X-CSRFToken and a cookie
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
        Check that CsrfTokenNode works when no CSRF cookie is set
        """
        req = self._get_GET_no_csrf_cookie_request()
        resp = token_view(req)

        token = get_token(req)
        self.assertIsNotNone(token)
        self._check_token_present(resp, token)

    def test_token_node_empty_csrf_cookie(self):
        """
        Check that we get a new token if the csrf_cookie is the empty string
        """
        req = self._get_GET_no_csrf_cookie_request()
        req.COOKIES[settings.CSRF_COOKIE_NAME] = b""
        CsrfViewMiddleware().process_view(req, token_view, (), {})
        resp = token_view(req)

        token = get_token(req)
        self.assertIsNotNone(token)
        self._check_token_present(resp, token)

    def test_token_node_with_csrf_cookie(self):
        """
        Check that CsrfTokenNode works when a CSRF cookie is set
        """
        req = self._get_GET_csrf_cookie_request()
        CsrfViewMiddleware().process_view(req, token_view, (), {})
        resp = token_view(req)
        self._check_token_present(resp)

    def test_get_token_for_exempt_view(self):
        """
        Check that get_token still works for a view decorated with 'csrf_exempt'.
        """
        req = self._get_GET_csrf_cookie_request()
        CsrfViewMiddleware().process_view(req, csrf_exempt(token_view), (), {})
        resp = token_view(req)
        self._check_token_present(resp)

    def test_get_token_for_requires_csrf_token_view(self):
        """
        Check that get_token works for a view decorated solely with requires_csrf_token
        """
        req = self._get_GET_csrf_cookie_request()
        resp = requires_csrf_token(token_view)(req)
        self._check_token_present(resp)

    def test_token_node_with_new_csrf_cookie(self):
        """
        Check that CsrfTokenNode works when a CSRF cookie is created by
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

    @override_settings(DEBUG=True)
    def test_https_bad_referer(self):
        """
        Test that a POST HTTPS request with a bad referer is rejected
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
        req.META['HTTP_REFERER'] = b'\xd8B\xf6I\xdf'
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

    @override_settings(ALLOWED_HOSTS=['www.example.com'], CSRF_COOKIE_DOMAIN='.example.com', USE_X_FORWARDED_PORT=True)
    def test_https_good_referer_behind_proxy(self):
        """
        A POST HTTPS request is accepted when USE_X_FORWARDED_PORT=True.
        """
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

    @override_settings(ALLOWED_HOSTS=['www.example.com'], CSRF_COOKIE_DOMAIN='.example.com')
    def test_https_good_referer_matches_cookie_domain(self):
        """
        A POST HTTPS request with a good referer should be accepted from a
        subdomain that's allowed by CSRF_COOKIE_DOMAIN.
        """
        req = self._get_POST_request_with_token()
        req._is_secure_override = True
        req.META['HTTP_REFERER'] = 'https://foo.example.com/'
        req.META['SERVER_PORT'] = '443'
        response = CsrfViewMiddleware().process_view(req, post_form_view, (), {})
        self.assertIsNone(response)

    @override_settings(ALLOWED_HOSTS=['www.example.com'], CSRF_COOKIE_DOMAIN='.example.com')
    def test_https_good_referer_matches_cookie_domain_with_different_port(self):
        """
        A POST HTTPS request with a good referer should be accepted from a
        subdomain that's allowed by CSRF_COOKIE_DOMAIN and a non-443 port.
        """
        req = self._get_POST_request_with_token()
        req._is_secure_override = True
        req.META['HTTP_HOST'] = 'www.example.com'
        req.META['HTTP_REFERER'] = 'https://foo.example.com:4443/'
        req.META['SERVER_PORT'] = '4443'
        response = CsrfViewMiddleware().process_view(req, post_form_view, (), {})
        self.assertIsNone(response)

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

    def test_ensures_csrf_cookie_no_middleware(self):
        """
        The ensure_csrf_cookie() decorator works without middleware.
        """
        @ensure_csrf_cookie
        def view(request):
            # Doesn't insert a token or anything
            return HttpResponse(content="")

        req = self._get_GET_no_csrf_cookie_request()
        resp = view(req)
        self.assertTrue(resp.cookies.get(settings.CSRF_COOKIE_NAME, False))
        self.assertIn('Cookie', resp.get('Vary', ''))

    def test_ensures_csrf_cookie_with_middleware(self):
        """
        The ensure_csrf_cookie() decorator works with the CsrfViewMiddleware
        enabled.
        """
        @ensure_csrf_cookie
        def view(request):
            # Doesn't insert a token or anything
            return HttpResponse(content="")

        req = self._get_GET_no_csrf_cookie_request()
        CsrfViewMiddleware().process_view(req, view, (), {})
        resp = view(req)
        resp2 = CsrfViewMiddleware().process_response(req, resp)
        self.assertTrue(resp2.cookies.get(settings.CSRF_COOKIE_NAME, False))
        self.assertIn('Cookie', resp2.get('Vary', ''))

    def test_ensures_csrf_cookie_no_logging(self):
        """
        ensure_csrf_cookie() doesn't log warnings (#19436).
        """
        @ensure_csrf_cookie
        def view(request):
            # Doesn't insert a token or anything
            return HttpResponse(content="")

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
            view(req)
        finally:
            logger.removeHandler(test_handler)
            logger.setLevel(old_log_level)

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
                super(CsrfPostRequest, self).__init__()
                self.method = 'POST'

                self.raise_error = False
                self.COOKIES[settings.CSRF_COOKIE_NAME] = token
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
        resp = CsrfViewMiddleware().process_view(req, post_form_view, (), {})
        self.assertEqual(resp.status_code, 403)
