"""
Cross Site Request Forgery Middleware.

This module provides a middleware that implements protection
against request forgeries from other sites.
"""

import re
import itertools
try:
    from functools import wraps
except ImportError:
    from django.utils.functional import wraps  # Python 2.3, 2.4 fallback.

from django.conf import settings
from django.http import HttpResponseForbidden
from django.utils.hashcompat import md5_constructor
from django.utils.safestring import mark_safe

_ERROR_MSG = mark_safe('<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en"><body><h1>403 Forbidden</h1><p>Cross Site Request Forgery detected. Request aborted.</p></body></html>')

_POST_FORM_RE = \
    re.compile(r'(<form\W[^>]*\bmethod=(\'|"|)POST(\'|"|)\b[^>]*>)', re.IGNORECASE)

_HTML_TYPES = ('text/html', 'application/xhtml+xml')

def _make_token(session_id):
    return md5_constructor(settings.SECRET_KEY + session_id).hexdigest()

class CsrfViewMiddleware(object):
    """
    Middleware that requires a present and correct csrfmiddlewaretoken
    for POST requests that have an active session.
    """
    def process_view(self, request, callback, callback_args, callback_kwargs):
        if request.method == 'POST':
            if getattr(callback, 'csrf_exempt', False):
                return None

            if request.is_ajax():
                return None

            try:
                session_id = request.COOKIES[settings.SESSION_COOKIE_NAME]
            except KeyError:
                # No session, no check required
                return None

            csrf_token = _make_token(session_id)
            # check incoming token
            try:
                request_csrf_token = request.POST['csrfmiddlewaretoken']
            except KeyError:
                return HttpResponseForbidden(_ERROR_MSG)

            if request_csrf_token != csrf_token:
                return HttpResponseForbidden(_ERROR_MSG)

        return None

class CsrfResponseMiddleware(object):
    """
    Middleware that post-processes a response to add a
    csrfmiddlewaretoken if the response/request have an active
    session.
    """
    def process_response(self, request, response):
	if getattr(response, 'csrf_exempt', False):
	    return response

        csrf_token = None
        try:
            # This covers a corner case in which the outgoing response
            # both contains a form and sets a session cookie.  This
            # really should not be needed, since it is best if views
            # that create a new session (login pages) also do a
            # redirect, as is done by all such view functions in
            # Django.
            cookie = response.cookies[settings.SESSION_COOKIE_NAME]
            csrf_token = _make_token(cookie.value)
        except KeyError:
            # Normal case - look for existing session cookie
            try:
                session_id = request.COOKIES[settings.SESSION_COOKIE_NAME]
                csrf_token = _make_token(session_id)
            except KeyError:
                # no incoming or outgoing cookie
                pass

        if csrf_token is not None and \
                response['Content-Type'].split(';')[0] in _HTML_TYPES:

            # ensure we don't add the 'id' attribute twice (HTML validity)
            idattributes = itertools.chain(("id='csrfmiddlewaretoken'",),
                                            itertools.repeat(''))
            def add_csrf_field(match):
                """Returns the matched <form> tag plus the added <input> element"""
                return mark_safe(match.group() + "<div style='display:none;'>" + \
                "<input type='hidden' " + idattributes.next() + \
                " name='csrfmiddlewaretoken' value='" + csrf_token + \
                "' /></div>")

            # Modify any POST forms
            response.content = _POST_FORM_RE.sub(add_csrf_field, response.content)
        return response

class CsrfMiddleware(CsrfViewMiddleware, CsrfResponseMiddleware):
    """Django middleware that adds protection against Cross Site
    Request Forgeries by adding hidden form fields to POST forms and
    checking requests for the correct value.

    In the list of middlewares, SessionMiddleware is required, and
    must come after this middleware.  CsrfMiddleWare must come after
    compression middleware.

    If a session ID cookie is present, it is hashed with the
    SECRET_KEY setting to create an authentication token.  This token
    is added to all outgoing POST forms and is expected on all
    incoming POST requests that have a session ID cookie.

    If you are setting cookies directly, instead of using Django's
    session framework, this middleware will not work.

    CsrfMiddleWare is composed of two middleware, CsrfViewMiddleware
    and CsrfResponseMiddleware which can be used independently.
    """
    pass

def csrf_response_exempt(view_func):
    """
    Modifies a view function so that its response is exempt
    from the post-processing of the CSRF middleware.
    """
    def wrapped_view(*args, **kwargs):
        resp = view_func(*args, **kwargs)
	resp.csrf_exempt = True
	return resp
    return wraps(view_func)(wrapped_view)

def csrf_view_exempt(view_func):
    """
    Marks a view function as being exempt from CSRF view protection.
    """
    # We could just do view_func.csrf_exempt = True, but decorators
    # are nicer if they don't have side-effects, so we return a new
    # function.
    def wrapped_view(*args, **kwargs):
        return view_func(*args, **kwargs)
    wrapped_view.csrf_exempt = True
    return wraps(view_func)(wrapped_view)

def csrf_exempt(view_func):
    """
    Marks a view function as being exempt from the CSRF checks
    and post processing.

    This is the same as using both the csrf_view_exempt and
    csrf_response_exempt decorators.
    """
    return csrf_response_exempt(csrf_view_exempt(view_func))
