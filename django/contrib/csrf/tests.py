# -*- coding: utf-8 -*-

from django.test import TestCase
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden
from django.contrib.csrf.middleware import CsrfMiddleware, _make_token, csrf_exempt
from django.conf import settings


def post_form_response():
    resp = HttpResponse(content="""
<html><body><form method="POST"><input type="text" /></form></body></html>
""", mimetype="text/html")
    return resp

def test_view(request):
    return post_form_response()

class CsrfMiddlewareTest(TestCase):

    _session_id = "1"

    def _get_GET_no_session_request(self):
        return HttpRequest()

    def _get_GET_session_request(self):
        req = self._get_GET_no_session_request()
        req.COOKIES[settings.SESSION_COOKIE_NAME] = self._session_id
        return req

    def _get_POST_session_request(self):
        req = self._get_GET_session_request()
        req.method = "POST"
        return req

    def _get_POST_no_session_request(self):
        req = self._get_GET_no_session_request()
        req.method = "POST"
        return req

    def _get_POST_session_request_with_token(self):
        req = self._get_POST_session_request()
        req.POST['csrfmiddlewaretoken'] = _make_token(self._session_id)
        return req

    def _get_post_form_response(self):
        return post_form_response()

    def _get_new_session_response(self):
        resp = self._get_post_form_response()
        resp.cookies[settings.SESSION_COOKIE_NAME] = self._session_id
        return resp

    def _check_token_present(self, response):
        self.assertContains(response, "name='csrfmiddlewaretoken' value='%s'" % _make_token(self._session_id))

    def get_view(self):
        return test_view

    # Check the post processing
    def test_process_response_no_session(self):
        """
        Check the post-processor does nothing if no session active
        """
        req = self._get_GET_no_session_request()
        resp = self._get_post_form_response()
        resp_content = resp.content # needed because process_response modifies resp
        resp2 = CsrfMiddleware().process_response(req, resp)
        self.assertEquals(resp_content, resp2.content)

    def test_process_response_existing_session(self):
        """
        Check that the token is inserted if there is an existing session
        """
        req = self._get_GET_session_request()
        resp = self._get_post_form_response()
        resp_content = resp.content # needed because process_response modifies resp
        resp2 = CsrfMiddleware().process_response(req, resp)
        self.assertNotEqual(resp_content, resp2.content)
        self._check_token_present(resp2)

    def test_process_response_new_session(self):
        """
        Check that the token is inserted if there is a new session being started
        """
        req = self._get_GET_no_session_request() # no session in request
        resp = self._get_new_session_response() # but new session started
        resp_content = resp.content # needed because process_response modifies resp
        resp2 = CsrfMiddleware().process_response(req, resp)
        self.assertNotEqual(resp_content, resp2.content)
        self._check_token_present(resp2)

    def test_process_response_exempt_view(self):
        """
        Check that no post processing is done for an exempt view
        """
        req = self._get_POST_session_request()
        resp = csrf_exempt(self.get_view())(req)
        resp_content = resp.content
        resp2 = CsrfMiddleware().process_response(req, resp)
        self.assertEquals(resp_content, resp2.content)

    # Check the request processing
    def test_process_request_no_session(self):
        """
        Check that if no session is present, the middleware does nothing.
        to the incoming request.
        """
        req = self._get_POST_no_session_request()
        req2 = CsrfMiddleware().process_view(req, self.get_view(), (), {})
        self.assertEquals(None, req2)

    def test_process_request_session_no_token(self):
        """
        Check that if a session is present but no token, we get a 'forbidden'
        """
        req = self._get_POST_session_request()
        req2 = CsrfMiddleware().process_view(req, self.get_view(), (), {})
        self.assertEquals(HttpResponseForbidden, req2.__class__)

    def test_process_request_session_and_token(self):
        """
        Check that if a session is present and a token, the middleware lets it through
        """
        req = self._get_POST_session_request_with_token()
        req2 = CsrfMiddleware().process_view(req, self.get_view(), (), {})
        self.assertEquals(None, req2)

    def test_process_request_session_no_token_exempt_view(self):
        """
        Check that if a session is present and no token, but the csrf_exempt
        decorator has been applied to the view, the middleware lets it through
        """
        req = self._get_POST_session_request()
        req2 = CsrfMiddleware().process_view(req, csrf_exempt(self.get_view()), (), {})
        self.assertEquals(None, req2)

    def test_ajax_exemption(self):
        """
        Check that AJAX requests are automatically exempted.
        """
        req = self._get_POST_session_request()
        req.META['HTTP_X_REQUESTED_WITH'] = 'XMLHttpRequest'
        req2 = CsrfMiddleware().process_view(req, self.get_view(), (), {})
        self.assertEquals(None, req2)
