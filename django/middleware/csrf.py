"""
Cross Site Request Forgery Middleware.

This module provides a middleware that implements protection
against request forgeries from other sites.
"""

import re

from django.conf import settings
from django.core.urlresolvers import get_callable
from django.utils.cache import patch_vary_headers
from django.utils.http import domain_permitted
from django.utils.log import getLogger
from django.utils.crypto import constant_time_compare, get_random_string

logger = getLogger('django.request')

REASON_NO_REFERER = "Referer checking failed - no Referer."
REASON_BAD_REFERER = "Referer checking failed - %s is not permitted."
REASON_NO_CSRF_COOKIE = "CSRF cookie not set."
REASON_BAD_TOKEN = "CSRF token missing or incorrect."
REASON_BAD_ORIGIN = "Origin checking failed - %s is not permitted."

CSRF_KEY_LENGTH = 32

def _get_failure_view():
    """
    Returns the view to be used for CSRF rejections
    """
    return get_callable(settings.CSRF_FAILURE_VIEW)


def _get_new_csrf_key():
    return get_random_string(CSRF_KEY_LENGTH)


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
    # Allow only alphanum, and ensure we return a 'str' for the sake
    # of the post processing middleware.
    if len(token) > CSRF_KEY_LENGTH:
        return _get_new_csrf_key()
    token = re.sub('[^a-zA-Z0-9]+', '', str(token.decode('ascii', 'ignore')))
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
        return _get_failure_view()(request, reason=reason)

    def process_view(self, request, callback, callback_args, callback_kwargs):

        if getattr(request, 'csrf_processing_done', False):
            return None

        try:
            csrf_token = _sanitize_token(
                request.COOKIES[settings.CSRF_COOKIE_NAME])
            # Use same token next time
            request.META['CSRF_COOKIE'] = csrf_token
        except KeyError:
            csrf_token = None
            # Generate token and store it in the request, so it's
            # available to the view.
            request.META["CSRF_COOKIE"] = _get_new_csrf_key()

        # Wait until request.META["CSRF_COOKIE"] has been manipulated before
        # bailing out, so that get_token still works
        if getattr(callback, 'csrf_exempt', False):
            return None

        # Assume that anything not defined as 'safe' by RC2616 needs protection
        if request.method not in ('GET', 'HEAD', 'OPTIONS', 'TRACE'):

            if getattr(request, '_dont_enforce_csrf_checks', False):
                # Mechanism to turn off CSRF checks for test suite.
                # It comes after the creation of CSRF cookies, so that
                # everything else continues to work exactly the same
                # (e.g. cookies are sent, etc.), but before any
                # branches that call reject().
                return self._accept(request)

            host = request.META.get('HTTP_HOST', '')
            # Note that host includes the port, so we split that out.
            # If the host has port specified (checked with ':') then, grab the
            # host domain from the string before the last ':'.
            host = host.split(':')[-2] if ':' in host else host

            origin = request.META.get('HTTP_ORIGIN')
            permitted_domains = getattr(settings, 'CSRF_PERMITTED_DOMAINS', [host])

            # If origin header exists, use it to check for csrf attacks.
            # Origin header is being compared to None here because we need to
            # reject requests with origin header as '' too, which otherwise is
            # treated as null.
            if origin is not None:
                if not domain_permitted(origin, permitted_domains):
                    reason = REASON_BAD_ORIGIN % (origin)
                    logger.warning('Forbidden (%s): %s',
                                   reason, request.path,
                        extra={
                            'status_code': 403,
                            'request': request,
                        }
                    )

                    return self._reject(request, reason)
            else:
                # Do a strict referer check in case an origin check succeds.
                # As far as CSRF is concerned, attackers who are in a position
                # to perform CSRF attack are not in a position to fake referer
                # headers.

                referer = request.META.get('HTTP_REFERER')
                if referer is None:
                    logger.warning('Forbidden (%s): %s',
                                   REASON_NO_REFERER, request.path,
                        extra={
                            'status_code': 403,
                            'request': request,
                        }
                    )

                    return self._reject(request, REASON_NO_REFERER)

                # Make sure that the http referer matches the permitted domains
                # pattern.
                if not domain_permitted(referer, permitted_domains):
                    reason = REASON_BAD_REFERER % (referer)
                    logger.warning('Forbidden (%s): %s', reason, request.path,
                        extra={
                            'status_code': 403,
                            'request': request,
                        }
                    )
                    return self._reject(request, reason)

            # Legacy token checking method.
            # TODO: Handle this with permitted domains. Cookies won't work
            # there, invalidating the whole point of permitted domains
            # functionality.
            if csrf_token is None:
                # No CSRF cookie. For POST requests, we insist on a CSRF cookie,
                # and in this way we can avoid all CSRF attacks, including login
                # CSRF.
                logger.warning('Forbidden (%s): %s',
                               REASON_NO_CSRF_COOKIE, request.path,
                    extra={
                        'status_code': 403,
                        'request': request,
                    }
                )
                return self._reject(request, REASON_NO_CSRF_COOKIE)

            # Check non-cookie token for match.
            request_csrf_token = ""
            if request.method == "POST":
                request_csrf_token = request.POST.get('csrfmiddlewaretoken', '')

            if request_csrf_token == "":
                # Fall back to X-CSRFToken, to make things easier for AJAX,
                # and possible for PUT/DELETE.
                request_csrf_token = request.META.get('HTTP_X_CSRFTOKEN', '')

            if not constant_time_compare(request_csrf_token, csrf_token):
                logger.warning('Forbidden (%s): %s',
                               REASON_BAD_TOKEN, request.path,
                    extra={
                        'status_code': 403,
                        'request': request,
                    }
                )

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

        # Set the CSRF cookie even if it's already set, so we renew
        # the expiry timer.
        response.set_cookie(settings.CSRF_COOKIE_NAME,
                            request.META["CSRF_COOKIE"],
                            max_age = 60 * 60 * 24 * 7 * 52,
                            domain=settings.CSRF_COOKIE_DOMAIN,
                            path=settings.CSRF_COOKIE_PATH,
                            secure=settings.CSRF_COOKIE_SECURE
                            )
        # Content varies with the CSRF cookie, so set the Vary header.
        patch_vary_headers(response, ('Cookie',))
        response.csrf_processing_done = True
        return response
