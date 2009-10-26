# -*- coding: utf-8 -*-

from django.test import TestCase
from django.http import HttpRequest, HttpResponse
from django.contrib.csrf.middleware import CsrfMiddleware, CsrfViewMiddleware, csrf_exempt
from django.contrib.csrf.context_processors import csrf
from django.contrib.sessions.middleware import SessionMiddleware
from django.utils.importlib import import_module
from django.conf import settings
from django.template import RequestContext, Template

# Response/views used for CsrfResponseMiddleware and CsrfViewMiddleware tests
def post_form_response():
    resp = HttpResponse(content="""
<html><body><form method="POST"><input type="text" /></form></body></html>
""", mimetype="text/html")
    return resp

def post_form_response_non_html():
    resp = post_form_response()
    resp["Content-Type"] = "application/xml"
    return resp

def post_form_view(request):
    """A view that returns a POST form (without a token)"""
    return post_form_response()

# Response/views used for template tag tests
def _token_template():
    return Template("{% csrf_token %}")

def _render_csrf_token_template(req):
    context = RequestContext(req, processors=[csrf])
    template = _token_template()
    return template.render(context)

def token_view(request):
    """A view that uses {% csrf_token %}"""
    return HttpResponse(_render_csrf_token_template(request))

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
        return getattr(self, '_is_secure', False)

class CsrfMiddlewareTest(TestCase):
    _csrf_id = "1"

    # This is a valid session token for this ID and secret key.  This was generated using
    # the old code that we're to be backwards-compatible with.  Don't use the CSRF code
    # to generate this hash, or we're merely testing the code against itself and not
    # checking backwards-compatibility.  This is also the output of (echo -n test1 | md5sum).
    _session_token = "5a105e8b9d40e1329780d62ea2265d8a"
    _session_id = "1"
    _secret_key_for_session_test= "test"

    def _get_GET_no_csrf_cookie_request(self):
        return TestingHttpRequest()

    def _get_GET_csrf_cookie_request(self):
        req = TestingHttpRequest()
        req.COOKIES[settings.CSRF_COOKIE_NAME] = self._csrf_id
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

    def _get_POST_session_request_with_token(self):
        req = self._get_POST_no_csrf_cookie_request()
        req.COOKIES[settings.SESSION_COOKIE_NAME] = self._session_id
        req.POST['csrfmiddlewaretoken'] = self._session_token
        return req

    def _get_POST_session_request_no_token(self):
        req = self._get_POST_no_csrf_cookie_request()
        req.COOKIES[settings.SESSION_COOKIE_NAME] = self._session_id
        return req

    def _check_token_present(self, response, csrf_id=None):
        self.assertContains(response, "name='csrfmiddlewaretoken' value='%s'" % (csrf_id or self._csrf_id))

    # Check the post processing and outgoing cookie
    def test_process_response_no_csrf_cookie(self):
        """
        When no prior CSRF cookie exists, check that the cookie is created and a
        token is inserted.
        """
        req = self._get_GET_no_csrf_cookie_request()
        CsrfMiddleware().process_view(req, post_form_view, (), {})

        resp = post_form_response()
        resp_content = resp.content # needed because process_response modifies resp
        resp2 = CsrfMiddleware().process_response(req, resp)

        csrf_cookie = resp2.cookies.get(settings.CSRF_COOKIE_NAME, False)
        self.assertNotEqual(csrf_cookie, False)
        self.assertNotEqual(resp_content, resp2.content)
        self._check_token_present(resp2, csrf_cookie.value)
        # Check the Vary header got patched correctly
        self.assert_('Cookie' in resp2.get('Vary',''))

    def test_process_response_no_csrf_cookie_view_only_get_token_used(self):
        """
        When no prior CSRF cookie exists, check that the cookie is created, even
        if only CsrfViewMiddleware is used.
        """
        # This is checking that CsrfViewMiddleware has the cookie setting
        # code. Most of the other tests use CsrfMiddleware.
        req = self._get_GET_no_csrf_cookie_request()
        # token_view calls get_token() indirectly
        CsrfViewMiddleware().process_view(req, token_view, (), {})
        resp = token_view(req)
        resp2 = CsrfViewMiddleware().process_response(req, resp)

        csrf_cookie = resp2.cookies.get(settings.CSRF_COOKIE_NAME, False)
        self.assertNotEqual(csrf_cookie, False)

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

    def test_process_response_existing_csrf_cookie(self):
        """
        Check that the token is inserted when a prior CSRF cookie exists
        """
        req = self._get_GET_csrf_cookie_request()
        CsrfMiddleware().process_view(req, post_form_view, (), {})

        resp = post_form_response()
        resp_content = resp.content # needed because process_response modifies resp
        resp2 = CsrfMiddleware().process_response(req, resp)
        self.assertNotEqual(resp_content, resp2.content)
        self._check_token_present(resp2)

    def test_process_response_non_html(self):
        """
        Check the the post-processor does nothing for content-types not in _HTML_TYPES.
        """
        req = self._get_GET_no_csrf_cookie_request()
        CsrfMiddleware().process_view(req, post_form_view, (), {})
        resp = post_form_response_non_html()
        resp_content = resp.content # needed because process_response modifies resp
        resp2 = CsrfMiddleware().process_response(req, resp)
        self.assertEquals(resp_content, resp2.content)

    def test_process_response_exempt_view(self):
        """
        Check that no post processing is done for an exempt view
        """
        req = self._get_POST_csrf_cookie_request()
        resp = csrf_exempt(post_form_view)(req)
        resp_content = resp.content
        resp2 = CsrfMiddleware().process_response(req, resp)
        self.assertEquals(resp_content, resp2.content)

    # Check the request processing
    def test_process_request_no_session_no_csrf_cookie(self):
        """
        Check that if neither a CSRF cookie nor a session cookie are present,
        the middleware rejects the incoming request.  This will stop login CSRF.
        """
        req = self._get_POST_no_csrf_cookie_request()
        req2 = CsrfMiddleware().process_view(req, post_form_view, (), {})
        self.assertEquals(403, req2.status_code)

    def test_process_request_csrf_cookie_no_token(self):
        """
        Check that if a CSRF cookie is present but no token, the middleware
        rejects the incoming request.
        """
        req = self._get_POST_csrf_cookie_request()
        req2 = CsrfMiddleware().process_view(req, post_form_view, (), {})
        self.assertEquals(403, req2.status_code)

    def test_process_request_csrf_cookie_and_token(self):
        """
        Check that if both a cookie and a token is present, the middleware lets it through.
        """
        req = self._get_POST_request_with_token()
        req2 = CsrfMiddleware().process_view(req, post_form_view, (), {})
        self.assertEquals(None, req2)

    def test_process_request_session_cookie_no_csrf_cookie_token(self):
        """
        When no CSRF cookie exists, but the user has a session, check that a token
        using the session cookie as a legacy CSRF cookie is accepted.
        """
        orig_secret_key = settings.SECRET_KEY
        settings.SECRET_KEY = self._secret_key_for_session_test
        try:
            req = self._get_POST_session_request_with_token()
            req2 = CsrfMiddleware().process_view(req, post_form_view, (), {})
            self.assertEquals(None, req2)
        finally:
            settings.SECRET_KEY = orig_secret_key

    def test_process_request_session_cookie_no_csrf_cookie_no_token(self):
        """
        Check that if a session cookie is present but no token and no CSRF cookie,
        the request is rejected.
        """
        req = self._get_POST_session_request_no_token()
        req2 = CsrfMiddleware().process_view(req, post_form_view, (), {})
        self.assertEquals(403, req2.status_code)

    def test_process_request_csrf_cookie_no_token_exempt_view(self):
        """
        Check that if a CSRF cookie is present and no token, but the csrf_exempt
        decorator has been applied to the view, the middleware lets it through
        """
        req = self._get_POST_csrf_cookie_request()
        req2 = CsrfMiddleware().process_view(req, csrf_exempt(post_form_view), (), {})
        self.assertEquals(None, req2)

    def test_ajax_exemption(self):
        """
        Check that AJAX requests are automatically exempted.
        """
        req = self._get_POST_csrf_cookie_request()
        req.META['HTTP_X_REQUESTED_WITH'] = 'XMLHttpRequest'
        req2 = CsrfMiddleware().process_view(req, post_form_view, (), {})
        self.assertEquals(None, req2)

    # Tests for the template tag method
    def test_token_node_no_csrf_cookie(self):
        """
        Check that CsrfTokenNode works when no CSRF cookie is set
        """
        req = self._get_GET_no_csrf_cookie_request()
        resp = token_view(req)
        self.assertEquals(u"", resp.content)

    def test_token_node_with_csrf_cookie(self):
        """
        Check that CsrfTokenNode works when a CSRF cookie is set
        """
        req = self._get_GET_csrf_cookie_request()
        CsrfViewMiddleware().process_view(req, token_view, (), {})
        resp = token_view(req)
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

    def test_response_middleware_without_view_middleware(self):
        """
        Check that CsrfResponseMiddleware finishes without error if the view middleware
        has not been called, as is the case if a request middleware returns a response.
        """
        req = self._get_GET_no_csrf_cookie_request()
        resp = post_form_view(req)
        CsrfMiddleware().process_response(req, resp)

    def test_https_bad_referer(self):
        """
        Test that a POST HTTPS request with a bad referer is rejected
        """
        req = self._get_POST_request_with_token()
        req._is_secure = True
        req.META['HTTP_HOST'] = 'www.example.com'
        req.META['HTTP_REFERER'] = 'https://www.evil.org/somepage'
        req2 = CsrfViewMiddleware().process_view(req, post_form_view, (), {})
        self.assertNotEqual(None, req2)
        self.assertEquals(403, req2.status_code)

    def test_https_good_referer(self):
        """
        Test that a POST HTTPS request with a good referer is accepted
        """
        req = self._get_POST_request_with_token()
        req._is_secure = True
        req.META['HTTP_HOST'] = 'www.example.com'
        req.META['HTTP_REFERER'] = 'https://www.example.com/somepage'
        req2 = CsrfViewMiddleware().process_view(req, post_form_view, (), {})
        self.assertEquals(None, req2)
