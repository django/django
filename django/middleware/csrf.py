"""
Cross Site Request Forgery Middleware.

This module provides a middleware that implements protection
against request forgeries from other sites.
"""
import logging
import string
from collections import defaultdict
from urllib.parse import urlparse

from django.conf import settings
from django.core.exceptions import DisallowedHost, ImproperlyConfigured
from django.http import UnreadablePostError
from django.http.request import HttpHeaders
from django.urls import get_callable
from django.utils.cache import patch_vary_headers
from django.utils.crypto import constant_time_compare, get_random_string
from django.utils.deprecation import MiddlewareMixin
from django.utils.functional import cached_property
from django.utils.http import is_same_domain
from django.utils.log import log_response
from django.utils.regex_helper import _lazy_re_compile

logger = logging.getLogger("django.security.csrf")
# This matches if any character is not in CSRF_ALLOWED_CHARS.
invalid_token_chars_re = _lazy_re_compile("[^a-zA-Z0-9]")

REASON_BAD_ORIGIN = "Origin checking failed - %s does not match any trusted origins."
REASON_NO_REFERER = "Referer checking failed - no Referer."
REASON_BAD_REFERER = "Referer checking failed - %s does not match any trusted origins."
REASON_NO_CSRF_COOKIE = "CSRF cookie not set."
REASON_CSRF_TOKEN_MISSING = "CSRF token missing."
REASON_MALFORMED_REFERER = "Referer checking failed - Referer is malformed."
REASON_INSECURE_REFERER = (
    "Referer checking failed - Referer is insecure while host is secure."
)
# The reason strings below are for passing to InvalidTokenFormat. They are
# phrases without a subject because they can be in reference to either the CSRF
# cookie or non-cookie token.
REASON_INCORRECT_LENGTH = "has incorrect length"
REASON_INVALID_CHARACTERS = "has invalid characters"

CSRF_SECRET_LENGTH = 32
CSRF_TOKEN_LENGTH = 2 * CSRF_SECRET_LENGTH
CSRF_ALLOWED_CHARS = string.ascii_letters + string.digits
CSRF_SESSION_KEY = "_csrftoken"


def _get_failure_view():
    """Return the view to be used for CSRF rejections."""
    return get_callable(settings.CSRF_FAILURE_VIEW)


def _get_new_csrf_string():
    return get_random_string(CSRF_SECRET_LENGTH, allowed_chars=CSRF_ALLOWED_CHARS)


def _mask_cipher_secret(secret):
    """
    Given a secret (assumed to be a string of CSRF_ALLOWED_CHARS), generate a
    token by adding a mask and applying it to the secret.
    """
    mask = _get_new_csrf_string()
    chars = CSRF_ALLOWED_CHARS
    pairs = zip((chars.index(x) for x in secret), (chars.index(x) for x in mask))
    cipher = "".join(chars[(x + y) % len(chars)] for x, y in pairs)
    return mask + cipher


def _unmask_cipher_token(token):
    """
    Given a token (assumed to be a string of CSRF_ALLOWED_CHARS, of length
    CSRF_TOKEN_LENGTH, and that its first half is a mask), use it to decrypt
    the second half to produce the original secret.
    """
    mask = token[:CSRF_SECRET_LENGTH]
    token = token[CSRF_SECRET_LENGTH:]
    chars = CSRF_ALLOWED_CHARS
    pairs = zip((chars.index(x) for x in token), (chars.index(x) for x in mask))
    return "".join(chars[x - y] for x, y in pairs)  # Note negative values are ok


def _add_new_csrf_cookie(request):
    """Generate a new random CSRF_COOKIE value, and add it to request.META."""
    csrf_secret = _get_new_csrf_string()
    request.META.update(
        {
            # RemovedInDjango50Warning: when the deprecation ends, replace
            # with: 'CSRF_COOKIE': csrf_secret
            "CSRF_COOKIE": (
                _mask_cipher_secret(csrf_secret)
                if settings.CSRF_COOKIE_MASKED
                else csrf_secret
            ),
            "CSRF_COOKIE_NEEDS_UPDATE": True,
        }
    )
    return csrf_secret


def get_token(request):
    """
    Return the CSRF token required for a POST form. The token is an
    alphanumeric value. A new token is created if one is not already set.

    A side effect of calling this function is to make the csrf_protect
    decorator and the CsrfViewMiddleware add a CSRF cookie and a 'Vary: Cookie'
    header to the outgoing response.  For this reason, you may need to use this
    function lazily, as is done by the csrf context processor.
    """
    if "CSRF_COOKIE" in request.META:
        csrf_secret = request.META["CSRF_COOKIE"]
        # Since the cookie is being used, flag to send the cookie in
        # process_response() (even if the client already has it) in order to
        # renew the expiry timer.
        request.META["CSRF_COOKIE_NEEDS_UPDATE"] = True
    else:
        csrf_secret = _add_new_csrf_cookie(request)
    return _mask_cipher_secret(csrf_secret)


def rotate_token(request):
    """
    Change the CSRF token in use for a request - should be done on login
    for security purposes.
    """
    _add_new_csrf_cookie(request)


class InvalidTokenFormat(Exception):
    def __init__(self, reason):
        self.reason = reason


def _check_token_format(token):
    """
    Raise an InvalidTokenFormat error if the token has an invalid length or
    characters that aren't allowed. The token argument can be a CSRF cookie
    secret or non-cookie CSRF token, and either masked or unmasked.
    """
    if len(token) not in (CSRF_TOKEN_LENGTH, CSRF_SECRET_LENGTH):
        raise InvalidTokenFormat(REASON_INCORRECT_LENGTH)
    # Make sure all characters are in CSRF_ALLOWED_CHARS.
    if invalid_token_chars_re.search(token):
        raise InvalidTokenFormat(REASON_INVALID_CHARACTERS)


def _does_token_match(request_csrf_token, csrf_secret):
    """
    Return whether the given CSRF token matches the given CSRF secret, after
    unmasking the token if necessary.

    This function assumes that the request_csrf_token argument has been
    validated to have the correct length (CSRF_SECRET_LENGTH or
    CSRF_TOKEN_LENGTH characters) and allowed characters, and that if it has
    length CSRF_TOKEN_LENGTH, it is a masked secret.
    """
    # Only unmask tokens that are exactly CSRF_TOKEN_LENGTH characters long.
    if len(request_csrf_token) == CSRF_TOKEN_LENGTH:
        request_csrf_token = _unmask_cipher_token(request_csrf_token)
    assert len(request_csrf_token) == CSRF_SECRET_LENGTH
    return constant_time_compare(request_csrf_token, csrf_secret)


class RejectRequest(Exception):
    def __init__(self, reason):
        self.reason = reason


class CsrfViewMiddleware(MiddlewareMixin):
    """
    Require a present and correct csrfmiddlewaretoken for POST requests that
    have a CSRF cookie, and set an outgoing CSRF cookie.

    This middleware should be used in conjunction with the {% csrf_token %}
    template tag.
    """

    @cached_property
    def csrf_trusted_origins_hosts(self):
        return [
            urlparse(origin).netloc.lstrip("*")
            for origin in settings.CSRF_TRUSTED_ORIGINS
        ]

    @cached_property
    def allowed_origins_exact(self):
        return {origin for origin in settings.CSRF_TRUSTED_ORIGINS if "*" not in origin}

    @cached_property
    def allowed_origin_subdomains(self):
        """
        A mapping of allowed schemes to list of allowed netlocs, where all
        subdomains of the netloc are allowed.
        """
        allowed_origin_subdomains = defaultdict(list)
        for parsed in (
            urlparse(origin)
            for origin in settings.CSRF_TRUSTED_ORIGINS
            if "*" in origin
        ):
            allowed_origin_subdomains[parsed.scheme].append(parsed.netloc.lstrip("*"))
        return allowed_origin_subdomains

    # The _accept and _reject methods currently only exist for the sake of the
    # requires_csrf_token decorator.
    def _accept(self, request):
        # Avoid checking the request twice by adding a custom attribute to
        # request.  This will be relevant when both decorator and middleware
        # are used.
        request.csrf_processing_done = True
        return None

    def _reject(self, request, reason):
        response = _get_failure_view()(request, reason=reason)
        log_response(
            "Forbidden (%s): %s",
            reason,
            request.path,
            response=response,
            request=request,
            logger=logger,
        )
        return response

    def _get_secret(self, request):
        """
        Return the CSRF secret originally associated with the request, or None
        if it didn't have one.

        If the CSRF_USE_SESSIONS setting is false, raises InvalidTokenFormat if
        the request's secret has invalid characters or an invalid length.
        """
        if settings.CSRF_USE_SESSIONS:
            try:
                csrf_secret = request.session.get(CSRF_SESSION_KEY)
            except AttributeError:
                raise ImproperlyConfigured(
                    "CSRF_USE_SESSIONS is enabled, but request.session is not "
                    "set. SessionMiddleware must appear before CsrfViewMiddleware "
                    "in MIDDLEWARE."
                )
        else:
            try:
                csrf_secret = request.COOKIES[settings.CSRF_COOKIE_NAME]
            except KeyError:
                csrf_secret = None
            else:
                # This can raise InvalidTokenFormat.
                _check_token_format(csrf_secret)
        if csrf_secret is None:
            return None
        # Django versions before 4.0 masked the secret before storing.
        if len(csrf_secret) == CSRF_TOKEN_LENGTH:
            csrf_secret = _unmask_cipher_token(csrf_secret)
        return csrf_secret

    def _set_csrf_cookie(self, request, response):
        if settings.CSRF_USE_SESSIONS:
            if request.session.get(CSRF_SESSION_KEY) != request.META["CSRF_COOKIE"]:
                request.session[CSRF_SESSION_KEY] = request.META["CSRF_COOKIE"]
        else:
            response.set_cookie(
                settings.CSRF_COOKIE_NAME,
                request.META["CSRF_COOKIE"],
                max_age=settings.CSRF_COOKIE_AGE,
                domain=settings.CSRF_COOKIE_DOMAIN,
                path=settings.CSRF_COOKIE_PATH,
                secure=settings.CSRF_COOKIE_SECURE,
                httponly=settings.CSRF_COOKIE_HTTPONLY,
                samesite=settings.CSRF_COOKIE_SAMESITE,
            )
            # Set the Vary header since content varies with the CSRF cookie.
            patch_vary_headers(response, ("Cookie",))

    def _origin_verified(self, request):
        request_origin = request.META["HTTP_ORIGIN"]
        try:
            good_host = request.get_host()
        except DisallowedHost:
            pass
        else:
            good_origin = "%s://%s" % (
                "https" if request.is_secure() else "http",
                good_host,
            )
            if request_origin == good_origin:
                return True
        if request_origin in self.allowed_origins_exact:
            return True
        try:
            parsed_origin = urlparse(request_origin)
        except ValueError:
            return False
        request_scheme = parsed_origin.scheme
        request_netloc = parsed_origin.netloc
        return any(
            is_same_domain(request_netloc, host)
            for host in self.allowed_origin_subdomains.get(request_scheme, ())
        )

    def _check_referer(self, request):
        referer = request.META.get("HTTP_REFERER")
        if referer is None:
            raise RejectRequest(REASON_NO_REFERER)

        try:
            referer = urlparse(referer)
        except ValueError:
            raise RejectRequest(REASON_MALFORMED_REFERER)

        # Make sure we have a valid URL for Referer.
        if "" in (referer.scheme, referer.netloc):
            raise RejectRequest(REASON_MALFORMED_REFERER)

        # Ensure that our Referer is also secure.
        if referer.scheme != "https":
            raise RejectRequest(REASON_INSECURE_REFERER)

        if any(
            is_same_domain(referer.netloc, host)
            for host in self.csrf_trusted_origins_hosts
        ):
            return
        # Allow matching the configured cookie domain.
        good_referer = (
            settings.SESSION_COOKIE_DOMAIN
            if settings.CSRF_USE_SESSIONS
            else settings.CSRF_COOKIE_DOMAIN
        )
        if good_referer is None:
            # If no cookie domain is configured, allow matching the current
            # host:port exactly if it's permitted by ALLOWED_HOSTS.
            try:
                # request.get_host() includes the port.
                good_referer = request.get_host()
            except DisallowedHost:
                raise RejectRequest(REASON_BAD_REFERER % referer.geturl())
        else:
            server_port = request.get_port()
            if server_port not in ("443", "80"):
                good_referer = "%s:%s" % (good_referer, server_port)

        if not is_same_domain(referer.netloc, good_referer):
            raise RejectRequest(REASON_BAD_REFERER % referer.geturl())

    def _bad_token_message(self, reason, token_source):
        if token_source != "POST":
            # Assume it is a settings.CSRF_HEADER_NAME value.
            header_name = HttpHeaders.parse_header_name(token_source)
            token_source = f"the {header_name!r} HTTP header"
        return f"CSRF token from {token_source} {reason}."

    def _check_token(self, request):
        # Access csrf_secret via self._get_secret() as rotate_token() may have
        # been called by an authentication middleware during the
        # process_request() phase.
        try:
            csrf_secret = self._get_secret(request)
        except InvalidTokenFormat as exc:
            raise RejectRequest(f"CSRF cookie {exc.reason}.")

        if csrf_secret is None:
            # No CSRF cookie. For POST requests, we insist on a CSRF cookie,
            # and in this way we can avoid all CSRF attacks, including login
            # CSRF.
            raise RejectRequest(REASON_NO_CSRF_COOKIE)

        # Check non-cookie token for match.
        request_csrf_token = ""
        if request.method == "POST":
            try:
                request_csrf_token = request.POST.get("csrfmiddlewaretoken", "")
            except UnreadablePostError:
                # Handle a broken connection before we've completed reading the
                # POST data. process_view shouldn't raise any exceptions, so
                # we'll ignore and serve the user a 403 (assuming they're still
                # listening, which they probably aren't because of the error).
                pass

        if request_csrf_token == "":
            # Fall back to X-CSRFToken, to make things easier for AJAX, and
            # possible for PUT/DELETE.
            try:
                # This can have length CSRF_SECRET_LENGTH or CSRF_TOKEN_LENGTH,
                # depending on whether the client obtained the token from
                # the DOM or the cookie (and if the cookie, whether the cookie
                # was masked or unmasked).
                request_csrf_token = request.META[settings.CSRF_HEADER_NAME]
            except KeyError:
                raise RejectRequest(REASON_CSRF_TOKEN_MISSING)
            token_source = settings.CSRF_HEADER_NAME
        else:
            token_source = "POST"

        try:
            _check_token_format(request_csrf_token)
        except InvalidTokenFormat as exc:
            reason = self._bad_token_message(exc.reason, token_source)
            raise RejectRequest(reason)

        if not _does_token_match(request_csrf_token, csrf_secret):
            reason = self._bad_token_message("incorrect", token_source)
            raise RejectRequest(reason)

    def process_request(self, request):
        try:
            csrf_secret = self._get_secret(request)
        except InvalidTokenFormat:
            _add_new_csrf_cookie(request)
        else:
            if csrf_secret is not None:
                # Use the same secret next time. If the secret was originally
                # masked, this also causes it to be replaced with the unmasked
                # form, but only in cases where the secret is already getting
                # saved anyways.
                request.META["CSRF_COOKIE"] = csrf_secret

    def process_view(self, request, callback, callback_args, callback_kwargs):
        if getattr(request, "csrf_processing_done", False):
            return None

        # Wait until request.META["CSRF_COOKIE"] has been manipulated before
        # bailing out, so that get_token still works
        if getattr(callback, "csrf_exempt", False):
            return None

        # Assume that anything not defined as 'safe' by RFC7231 needs protection
        if request.method in ("GET", "HEAD", "OPTIONS", "TRACE"):
            return self._accept(request)

        if getattr(request, "_dont_enforce_csrf_checks", False):
            # Mechanism to turn off CSRF checks for test suite. It comes after
            # the creation of CSRF cookies, so that everything else continues
            # to work exactly the same (e.g. cookies are sent, etc.), but
            # before any branches that call the _reject method.
            return self._accept(request)

        # Reject the request if the Origin header doesn't match an allowed
        # value.
        if "HTTP_ORIGIN" in request.META:
            if not self._origin_verified(request):
                return self._reject(
                    request, REASON_BAD_ORIGIN % request.headers["Origin"]
                )
        elif request.is_secure():
            # If the Origin header wasn't provided, reject HTTPS requests if
            # the Referer header doesn't match an allowed value.
            #
            # Suppose user visits http://example.com/
            # An active network attacker (man-in-the-middle, MITM) sends a
            # POST form that targets https://example.com/detonate-bomb/ and
            # submits it via JavaScript.
            #
            # The attacker will need to provide a CSRF cookie and token, but
            # that's no problem for a MITM and the session-independent secret
            # we're using. So the MITM can circumvent the CSRF protection. This
            # is true for any HTTP connection, but anyone using HTTPS expects
            # better! For this reason, for https://example.com/ we need
            # additional protection that treats http://example.com/ as
            # completely untrusted. Under HTTPS, Barth et al. found that the
            # Referer header is missing for same-domain requests in only about
            # 0.2% of cases or less, so we can use strict Referer checking.
            try:
                self._check_referer(request)
            except RejectRequest as exc:
                return self._reject(request, exc.reason)

        try:
            self._check_token(request)
        except RejectRequest as exc:
            return self._reject(request, exc.reason)

        return self._accept(request)

    def process_response(self, request, response):
        if request.META.get("CSRF_COOKIE_NEEDS_UPDATE"):
            self._set_csrf_cookie(request, response)
            # Unset the flag to prevent _set_csrf_cookie() from being
            # unnecessarily called again in process_response() by other
            # instances of CsrfViewMiddleware. This can happen e.g. when both a
            # decorator and middleware are used. However,
            # CSRF_COOKIE_NEEDS_UPDATE is still respected in subsequent calls
            # e.g. in case rotate_token() is called in process_response() later
            # by custom middleware but before those subsequent calls.
            request.META["CSRF_COOKIE_NEEDS_UPDATE"] = False

        return response
