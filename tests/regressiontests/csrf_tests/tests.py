# -*- coding: utf-8 -*-

from django.conf import settings
from django.core.context_processors import csrf
from django.http import HttpRequest, HttpResponse
from django.middleware.csrf import CsrfViewMiddleware, CSRF_KEY_LENGTH
from django.template import RequestContext, Template
from django.test import TestCase
from django.views.decorators.csrf import csrf_exempt, requires_csrf_token, ensure_csrf_cookie


# Response/views used for CsrfResponseMiddleware and CsrfViewMiddleware tests
def post_form_response():
    resp = HttpResponse(content=u"""
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

class CsrfViewMiddlewareTest(TestCase):
    # The csrf token is potentially from an untrusted source, so could have
    # characters that need dealing with.
    _csrf_id_cookie = "<1>\xc2\xa1"
    _csrf_id = "1"

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

    def _check_token_present(self, response, csrf_id=None):
        self.assertContains(response, "name='csrfmiddlewaretoken' value='%s'" % (csrf_id or self._csrf_id))

    def test_process_view_token_too_long(self): 
        """ 
        Check that if the token is longer than expected, it is ignored and 
        a new token is created. 
        """ 
        req = self._get_GET_no_csrf_cookie_request() 
        req.COOKIES[settings.CSRF_COOKIE_NAME] = 'x' * 10000000 
        CsrfViewMiddleware().process_view(req, token_view, (), {}) 
        resp = token_view(req) 
        resp2 = CsrfViewMiddleware().process_response(req, resp) 
        csrf_cookie = resp2.cookies.get(settings.CSRF_COOKIE_NAME, False) 
        self.assertEqual(len(csrf_cookie.value), CSRF_KEY_LENGTH) 

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
                           CSRF_COOKIE_SECURE=True):
            # token_view calls get_token() indirectly
            CsrfViewMiddleware().process_view(req, token_view, (), {})
            resp = token_view(req)
            resp2 = CsrfViewMiddleware().process_response(req, resp)
        csrf_cookie = resp2.cookies.get('myname', False)
        self.assertNotEqual(csrf_cookie, False)
        self.assertEqual(csrf_cookie['domain'], '.example.com')
        self.assertEqual(csrf_cookie['secure'], True)
        self.assertEqual(csrf_cookie['path'], '/test/')
        self.assertTrue('Cookie' in resp2.get('Vary',''))

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
        self.assertEqual(None, req2)

    def test_process_request_csrf_cookie_no_token_exempt_view(self):
        """
        Check that if a CSRF cookie is present and no token, but the csrf_exempt
        decorator has been applied to the view, the middleware lets it through
        """
        req = self._get_POST_csrf_cookie_request()
        req2 = CsrfViewMiddleware().process_view(req, csrf_exempt(post_form_view), (), {})
        self.assertEqual(None, req2)

    def test_csrf_token_in_header(self):
        """
        Check that we can pass in the token in a header instead of in the form
        """
        req = self._get_POST_csrf_cookie_request()
        req.META['HTTP_X_CSRFTOKEN'] = self._csrf_id
        req2 = CsrfViewMiddleware().process_view(req, post_form_view, (), {})
        self.assertEqual(None, req2)

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
        self.assertEqual(None, req2)

        req = self._get_GET_csrf_cookie_request()
        req.method = 'DELETE'
        req.META['HTTP_X_CSRFTOKEN'] = self._csrf_id
        req2 = CsrfViewMiddleware().process_view(req, post_form_view, (), {})
        self.assertEqual(None, req2)

    # Tests for the template tag method
    def test_token_node_no_csrf_cookie(self):
        """
        Check that CsrfTokenNode works when no CSRF cookie is set
        """
        req = self._get_GET_no_csrf_cookie_request()
        resp = token_view(req)
        self.assertEqual(u"", resp.content)

    def test_token_node_empty_csrf_cookie(self):
        """
        Check that we get a new token if the csrf_cookie is the empty string
        """
        req = self._get_GET_no_csrf_cookie_request()
        req.COOKIES[settings.CSRF_COOKIE_NAME] = ""
        CsrfViewMiddleware().process_view(req, token_view, (), {})
        resp = token_view(req)

        self.assertNotEqual(u"", resp.content)

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

    def test_https_bad_referer(self):
        """
        Test that a POST HTTPS request with a bad referer is rejected
        """
        req = self._get_POST_request_with_token()
        req._is_secure_override = True
        req.META['HTTP_HOST'] = 'www.example.com'
        req.META['HTTP_REFERER'] = 'https://www.evil.org/somepage'
        req2 = CsrfViewMiddleware().process_view(req, post_form_view, (), {})
        self.assertNotEqual(None, req2)
        self.assertEqual(403, req2.status_code)

    def test_https_good_referer(self):
        """
        Test that a POST HTTPS request with a good referer is accepted
        """
        req = self._get_POST_request_with_token()
        req._is_secure_override = True
        req.META['HTTP_HOST'] = 'www.example.com'
        req.META['HTTP_REFERER'] = 'https://www.example.com/somepage'
        req2 = CsrfViewMiddleware().process_view(req, post_form_view, (), {})
        self.assertEqual(None, req2)

    def test_https_good_referer_2(self):
        """
        Test that a POST HTTPS request with a good referer is accepted
        where the referer contains no trailing slash
        """
        # See ticket #15617
        req = self._get_POST_request_with_token()
        req._is_secure_override = True
        req.META['HTTP_HOST'] = 'www.example.com'
        req.META['HTTP_REFERER'] = 'https://www.example.com'
        req2 = CsrfViewMiddleware().process_view(req, post_form_view, (), {})
        self.assertEqual(None, req2)

    def test_ensures_csrf_cookie_no_middleware(self):
        """
        Tests that ensures_csrf_cookie decorator fulfils its promise
        with no middleware
        """
        @ensure_csrf_cookie
        def view(request):
            # Doesn't insert a token or anything
            return HttpResponse(content="")

        req = self._get_GET_no_csrf_cookie_request()
        resp = view(req)
        self.assertTrue(resp.cookies.get(settings.CSRF_COOKIE_NAME, False))
        self.assertTrue('Cookie' in resp.get('Vary',''))

    def test_ensures_csrf_cookie_with_middleware(self):
        """
        Tests that ensures_csrf_cookie decorator fulfils its promise
        with the middleware enabled.
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
        self.assertTrue('Cookie' in resp2.get('Vary',''))
