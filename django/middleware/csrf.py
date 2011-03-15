"""
Cross Site Request Forgery Middleware.

This module provides a middleware that implements protection
against request forgeries from other sites.
"""

import itertools
import re
import random

from django.conf import settings
from django.core.urlresolvers import get_callable
from django.utils.cache import patch_vary_headers
from django.utils.hashcompat import md5_constructor
from django.utils.http import same_origin
from django.utils.safestring import mark_safe

_POST_FORM_RE = \
    re.compile(r'(<form\W[^>]*\bmethod\s*=\s*(\'|"|)POST(\'|"|)\b[^>]*>)', re.IGNORECASE)

_HTML_TYPES = ('text/html', 'application/xhtml+xml')

# Use the system (hardware-based) random number generator if it exists.
if hasattr(random, 'SystemRandom'):
    randrange = random.SystemRandom().randrange
else:
    randrange = random.randrange
_MAX_CSRF_KEY = 18446744073709551616L     # 2 << 63

REASON_NO_REFERER = "Referer checking failed - no Referer."
REASON_BAD_REFERER = "Referer checking failed - %s does not match %s."
REASON_NO_COOKIE = "No CSRF or session cookie."
REASON_NO_CSRF_COOKIE = "CSRF cookie not set."
REASON_BAD_TOKEN = "CSRF token missing or incorrect."


def _get_failure_view():
    """
    Returns the view to be used for CSRF rejections
    """
    return get_callable(settings.CSRF_FAILURE_VIEW)


def _get_new_csrf_key():
    return md5_constructor("%s%s"
                % (randrange(0, _MAX_CSRF_KEY), settings.SECRET_KEY)).hexdigest()


def _make_legacy_session_token(session_id):
    return md5_constructor(settings.SECRET_KEY + session_id).hexdigest()


def get_token(request):
    """
    Returns the the CSRF token required for a POST form. The token is an
    alphanumeric value.

    A side effect of calling this function is to make the the csrf_protect
    decorator and the CsrfViewMiddleware add a CSRF cookie and a 'Vary: Cookie'
    header to the outgoing response.  For this reason, you may need to use this
    function lazily, as is done by the csrf context processor.
    """
    request.META["CSRF_COOKIE_USED"] = True
    return request.META.get("CSRF_COOKIE", None)


def _sanitize_token(token):
    # Allow only alphanum, and ensure we return a 'str' for the sake of the post
    # processing middleware.
    token = re.sub('[^a-zA-Z0-9]', '', str(token.decode('ascii', 'ignore')))
    if token == "":
        # In case the cookie has been truncated to nothing at some point.
        return _get_new_csrf_key()
    else:
        return token


class CsrfViewMiddleware(object):
    """
    Middleware that requires a present and correct csrfmiddlewaretoken
    for POST requests that have a CSRF cookie, and sets an outgoing
    CSRF cookie.

    This middleware should be used in conjunction with the csrf_token template
    tag.
    """
    # The _accept and _reject methods currently only exist for the sake of the
    # requires_csrf_token decorator.
    def _accept(self, request):
        # Avoid checking the request twice by adding a custom attribute to
        # request.  This will be relevant when both decorator and middleware
        # are used.
        request.csrf_processing_done = True
        return None

    def _reject(self, request, reason):
        return _get_failure_view()(request, reason=reason)

    def process_view(self, request, callback, callback_args, callback_kwargs):

        if getattr(request, 'csrf_processing_done', False):
            return None

        # If the user doesn't have a CSRF cookie, generate one and store it in the
        # request, so it's available to the view.  We'll store it in a cookie when
        # we reach the response.
        try:
            # In case of cookies from untrusted sources, we strip anything
            # dangerous at this point, so that the cookie + token will have the
            # same, sanitized value.
            request.META["CSRF_COOKIE"] = _sanitize_token(request.COOKIES[settings.CSRF_COOKIE_NAME])
            cookie_is_new = False
        except KeyError:
            # No cookie, so create one.  This will be sent with the next
            # response.
            request.META["CSRF_COOKIE"] = _get_new_csrf_key()
            # Set a flag to allow us to fall back and allow the session id in
            # place of a CSRF cookie for this request only.
            cookie_is_new = True

        # Wait until request.META["CSRF_COOKIE"] has been manipulated before
        # bailing out, so that get_token still works
        if getattr(callback, 'csrf_exempt', False):
            return None

        if request.method == 'POST':
            if getattr(request, '_dont_enforce_csrf_checks', False):
                # Mechanism to turn off CSRF checks for test suite.  It comes after
                # the creation of CSRF cookies, so that everything else continues to
                # work exactly the same (e.g. cookies are sent etc), but before the
                # any branches that call reject()
                return self._accept(request)

            if request.is_secure():
                # Strict referer checking for HTTPS
                referer = request.META.get('HTTP_REFERER')
                if referer is None:
                    return self._reject(request, REASON_NO_REFERER)

                # Note that request.get_host() includes the port
                good_referer = 'https://%s/' % request.get_host()
                if not same_origin(referer, good_referer):
                    return self._reject(request, REASON_BAD_REFERER %
                                        (referer, good_referer))

            # If the user didn't already have a CSRF cookie, then fall back to
            # the Django 1.1 method (hash of session ID), so a request is not
            # rejected if the form was sent to the user before upgrading to the
            # Django 1.2 method (session independent nonce)
            if cookie_is_new:
                try:
                    session_id = request.COOKIES[settings.SESSION_COOKIE_NAME]
                    csrf_token = _make_legacy_session_token(session_id)
                except KeyError:
                    # No CSRF cookie and no session cookie. For POST requests,
                    # we insist on a CSRF cookie, and in this way we can avoid
                    # all CSRF attacks, including login CSRF.
                    return self._reject(request, REASON_NO_COOKIE)
            else:
                csrf_token = request.META["CSRF_COOKIE"]

            # check incoming token
            request_csrf_token = request.POST.get('csrfmiddlewaretoken', "")
            if request_csrf_token == "":
                # Fall back to X-CSRFToken, to make things easier for AJAX
                request_csrf_token = request.META.get('HTTP_X_CSRFTOKEN', '')

            if request_csrf_token != csrf_token:
                if cookie_is_new:
                    # probably a problem setting the CSRF cookie
                    return self._reject(request, REASON_NO_CSRF_COOKIE)
                else:
                    return self._reject(request, REASON_BAD_TOKEN)

        return self._accept(request)

    def process_response(self, request, response):
        if getattr(response, 'csrf_processing_done', False):
            return response

        # If CSRF_COOKIE is unset, then CsrfViewMiddleware.process_view was
        # never called, probaby because a request middleware returned a response
        # (for example, contrib.auth redirecting to a login page).
        if request.META.get("CSRF_COOKIE") is None:
            return response

        if not request.META.get("CSRF_COOKIE_USED", False):
            return response

        # Set the CSRF cookie even if it's already set, so we renew the expiry timer.
        response.set_cookie(settings.CSRF_COOKIE_NAME,
                request.META["CSRF_COOKIE"], max_age = 60 * 60 * 24 * 7 * 52,
                domain=settings.CSRF_COOKIE_DOMAIN)
        # Content varies with the CSRF cookie, so set the Vary header.
        patch_vary_headers(response, ('Cookie',))
        response.csrf_processing_done = True
        return response


class CsrfResponseMiddleware(object):
    """
    DEPRECATED
    Middleware that post-processes a response to add a csrfmiddlewaretoken.

    This exists for backwards compatibility and as an interim measure until
    applications are converted to using use the csrf_token template tag
    instead. It will be removed in Django 1.4.
    """
    def __init__(self):
        import warnings
        warnings.warn(
            "CsrfResponseMiddleware and CsrfMiddleware are deprecated; use CsrfViewMiddleware and the template tag instead (see CSRF documentation).",
            PendingDeprecationWarning
        )

    def process_response(self, request, response):
        if getattr(response, 'csrf_exempt', False):
            return response

        if response['Content-Type'].split(';')[0] in _HTML_TYPES:
            csrf_token = get_token(request)
            # If csrf_token is None, we have no token for this request, which probably
            # means that this is a response from a request middleware.
            if csrf_token is None:
                return response

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
            response.content, n = _POST_FORM_RE.subn(add_csrf_field, response.content)
            if n > 0:
                # Content varies with the CSRF cookie, so set the Vary header.
                patch_vary_headers(response, ('Cookie',))

                # Since the content has been modified, any Etag will now be
                # incorrect.  We could recalculate, but only if we assume that
                # the Etag was set by CommonMiddleware. The safest thing is just
                # to delete. See bug #9163
                del response['ETag']
        return response


class CsrfMiddleware(object):
    """
    Django middleware that adds protection against Cross Site
    Request Forgeries by adding hidden form fields to POST forms and
    checking requests for the correct value.

    CsrfMiddleware uses two middleware, CsrfViewMiddleware and
    CsrfResponseMiddleware, which can be used independently.  It is recommended
    to use only CsrfViewMiddleware and use the csrf_token template tag in
    templates for inserting the token.
    """
    # We can't just inherit from CsrfViewMiddleware and CsrfResponseMiddleware
    # because both have process_response methods.
    def __init__(self):
        self.response_middleware = CsrfResponseMiddleware()
        self.view_middleware = CsrfViewMiddleware()

    def process_response(self, request, resp):
        # We must do the response post-processing first, because that calls
        # get_token(), which triggers a flag saying that the CSRF cookie needs
        # to be sent (done in CsrfViewMiddleware.process_response)
        resp2 = self.response_middleware.process_response(request, resp)
        return self.view_middleware.process_response(request, resp2)

    def process_view(self, request, callback, callback_args, callback_kwargs):
        return self.view_middleware.process_view(request, callback, callback_args,
                                                 callback_kwargs)
