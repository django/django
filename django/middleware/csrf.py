"""
Cross Site Request Forgery Middleware.

This module provides a middleware that implements protection
against request forgeries from other sites.
"""
from __future__ import unicode_literals

import logging
import re

from django.conf import settings
from django.core.signing import get_cookie_signer, FutureTimestampSigner, BadSignature,\
    SignatureExpired
from django.core.urlresolvers import get_callable
from django.utils.cache import patch_vary_headers
from django.utils.encoding import force_text, force_str
from django.utils.http import same_origin
from django.utils.crypto import constant_time_compare, get_random_string


logger = logging.getLogger('django.request')

REASON_NO_REFERER = "Referer checking failed - no Referer."
REASON_BAD_REFERER = "Referer checking failed - %s does not match %s."
REASON_NO_CSRF_COOKIE = "CSRF cookie not set."
REASON_BAD_TOKEN = "CSRF token missing or incorrect."
REASON_TOKEN_EXPIRED = "CSRF token expired."

CSRF_KEY_LENGTH = 32

def _get_failure_view():
    """
    Returns the view to be used for CSRF rejections
    """
    return get_callable(settings.CSRF_FAILURE_VIEW)


def _get_new_csrf_key():
    return get_random_string(CSRF_KEY_LENGTH)


class _CSRFTokenSigner(FutureTimestampSigner):
    """
    Same as FutureTimestampSigner, except that the signature is appended as well as prepended
    """
    def sign(self, value):
        signed = super(_CSRFTokenSigner, self).sign(value)
        signed = force_str(signed)
        _,signature = signed.rsplit(self.sep, 1)
        return str("%s%s%s") % (signature, self.sep, signed)
     
    def unsign(self, signed_value):
        signed_value = force_str(signed_value)
        if not self.sep in signed_value:
            raise BadSignature('No "%s" found in value' % self.sep)
        prefix_sig, signed_value = signed_value.split(self.sep, 1)
        _, suffix_sig = signed_value.rsplit(self.sep, 1)
        if not constant_time_compare(prefix_sig, suffix_sig):
            raise BadSignature("prefix and suffix signatures do not match")
        return super(_CSRFTokenSigner, self).unsign(signed_value)

def get_token(request, max_age=None):
    """
    Returns the CSRF token required for a POST form. The token is signed,
    and optinally timestamped.

    A side effect of calling this function is to make the csrf_protect
    decorator and the CsrfViewMiddleware add a CSRF cookie and a 'Vary: Cookie'
    header to the outgoing response.  For this reason, you may need to use this
    function lazily, as is done by the csrf context processor.
    """
    request.META["CSRF_COOKIE_USED"] = True
    csrf_token = request.META.get("CSRF_COOKIE", None)
    if csrf_token is None:
        return None
    if max_age is None:
        max_age = settings.CSRF_TOKEN_MAX_AGE
    signer = _CSRFTokenSigner(max_age) if max_age else get_cookie_signer() 
    signed_token = signer.sign(csrf_token)
    return signed_token

def validate_token(request, request_csrf_token, csrf_token):
    time_limited = request.META.get("CSRF_TIME_LIMITED", None)
    signer = _CSRFTokenSigner() if time_limited else get_cookie_signer() 
    try:
        request_token = signer.unsign(request_csrf_token)
        if not constant_time_compare(request_token, csrf_token):
            return REASON_BAD_TOKEN
        else:
            return None
    except SignatureExpired:
        return REASON_TOKEN_EXPIRED
    except BadSignature:
        return REASON_BAD_TOKEN

def rotate_token(request):
    """
    Changes the CSRF token in use for a request - should be done on login
    for security purposes.
    """
    request.META["CSRF_COOKIE"] = _get_new_csrf_key()


def _sanitize_token(token):
    # Check signature
    token = get_cookie_signer().unsign(token)
    # Allow only alphanum
    if len(token) > CSRF_KEY_LENGTH:
        return _get_new_csrf_key()
    token = re.sub('[^a-zA-Z0-9]+', '', force_text(token))
    if token == "":
        # In case the cookie has been truncated to nothing at some point.
        return _get_new_csrf_key()
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
        logger.warning('Forbidden (%s): %s',
                       reason, request.path,
            extra={
                'status_code': 403,
                'request': request,
            }
        )
        return _get_failure_view()(request, reason=reason)

    def process_view(self, request, callback, callback_args, callback_kwargs):

        if getattr(request, 'csrf_processing_done', False):
            return None

        try:
            csrf_token = _sanitize_token(
                request.COOKIES[settings.CSRF_COOKIE_NAME])
            # Use same token next time
            request.META['CSRF_COOKIE'] = csrf_token
        except KeyError, BadSignature:
            # Having an invalid token cookie is the same as having no cookie
            # As this could happen with no user involvement (e.g. site rotated SECRET_KEY)
            csrf_token = None
            # Generate token and store it in the request, so it's
            # available to the view.
            request.META["CSRF_COOKIE"] = _get_new_csrf_key()

        # Wait until request.META["CSRF_COOKIE"] has been manipulated before
        # bailing out, so that get_token still works
        if getattr(callback, 'csrf_exempt', False):
            return None

        # Assume that anything not defined as 'safe' by RFC2616 needs protection
        if request.method not in ('GET', 'HEAD', 'OPTIONS', 'TRACE'):
            if getattr(request, '_dont_enforce_csrf_checks', False):
                # Mechanism to turn off CSRF checks for test suite.
                # It comes after the creation of CSRF cookies, so that
                # everything else continues to work exactly the same
                # (e.g. cookies are sent, etc.), but before any
                # branches that call reject().
                return self._accept(request)

            if request.is_secure():
                # Suppose user visits http://example.com/
                # An active network attacker (man-in-the-middle, MITM) sends a
                # POST form that targets https://example.com/detonate-bomb/ and
                # submits it via JavaScript.
                #
                # The attacker will need to provide a CSRF cookie and token, but
                # that's no problem for a MITM and the session-independent
                # nonce we're using. So the MITM can circumvent the CSRF
                # protection. This is true for any HTTP connection, but anyone
                # using HTTPS expects better! For this reason, for
                # https://example.com/ we need additional protection that treats
                # http://example.com/ as completely untrusted. Under HTTPS,
                # Barth et al. found that the Referer header is missing for
                # same-domain requests in only about 0.2% of cases or less, so
                # we can use strict Referer checking.
                referer = request.META.get('HTTP_REFERER')
                if referer is None:
                    return self._reject(request, REASON_NO_REFERER)

                # Note that request.get_host() includes the port.
                good_referer = 'https://%s/' % request.get_host()
                if not same_origin(referer, good_referer):
                    reason = REASON_BAD_REFERER % (referer, good_referer)
                    return self._reject(request, reason)

            if csrf_token is None:
                # No CSRF cookie. For POST requests, we insist on a CSRF cookie,
                # and in this way we can avoid all CSRF attacks, including login
                # CSRF.
                return self._reject(request, REASON_NO_CSRF_COOKIE)

            # Check non-cookie token for match.
            request_csrf_token = ""
            if request.method == "POST":
                request_csrf_token = request.POST.get('csrfmiddlewaretoken', '')

            if request_csrf_token == "":
                # Fall back to X-CSRFToken, to make things easier for AJAX,
                # and possible for PUT/DELETE.
                request_csrf_token = request.META.get('HTTP_X_CSRFTOKEN', '')

            reason = validate_token(request_csrf_token, csrf_token)
            if reason:
                return self._reject(request, reason)

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

        # Set the CSRF cookie even if it's already set, so we renew
        # the expiry timer.
        signed_csrf_token = get_cookie_signer().sign(request.META["CSRF_COOKIE"])
        response.set_cookie(settings.CSRF_COOKIE_NAME,
                            signed_csrf_token,
                            max_age = 60 * 60 * 24 * 7 * 52,
                            domain=settings.CSRF_COOKIE_DOMAIN,
                            path=settings.CSRF_COOKIE_PATH,
                            secure=settings.CSRF_COOKIE_SECURE,
                            httponly=settings.CSRF_COOKIE_HTTPONLY
                            )
        # Content varies with the CSRF cookie, so set the Vary header.
        patch_vary_headers(response, ('Cookie',))
        response.csrf_processing_done = True
        return response
