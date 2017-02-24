"""
This module contains helper functions for controlling caching. It does so by
managing the "Vary" header of responses. It includes functions to patch the
header of response objects directly and decorators that change functions to do
that header-patching themselves.

For information on the Vary header, see:

    https://tools.ietf.org/html/rfc7231#section-7.1.4

Essentially, the "Vary" HTTP header defines which headers a cache should take
into account when building its cache key. Requests with the same path but
different header content for headers named in "Vary" need to get different
cache keys to prevent delivery of wrong content.

An example: i18n middleware would need to distinguish caches by the
"Accept-language" header.
"""
import hashlib
import logging
import re
import time
import warnings

from django.conf import settings
from django.core.cache import caches
from django.http import HttpResponse, HttpResponseNotModified
from django.utils.deprecation import RemovedInDjango21Warning
from django.utils.encoding import force_bytes, force_text, iri_to_uri
from django.utils.http import (
    http_date, parse_etags, parse_http_date_safe, quote_etag,
)
from django.utils.timezone import get_current_timezone_name
from django.utils.translation import get_language

cc_delim_re = re.compile(r'\s*,\s*')

logger = logging.getLogger('django.request')


def patch_cache_control(response, **kwargs):
    """
    Patch the Cache-Control header by adding all keyword arguments to it.
    The transformation is as follows:

    * All keyword parameter names are turned to lowercase, and underscores
      are converted to hyphens.
    * If the value of a parameter is True (exactly True, not just a
      true value), only the parameter name is added to the header.
    * All other parameters are added with their value, after applying
      str() to it.
    """
    def dictitem(s):
        t = s.split('=', 1)
        if len(t) > 1:
            return (t[0].lower(), t[1])
        else:
            return (t[0].lower(), True)

    def dictvalue(t):
        if t[1] is True:
            return t[0]
        else:
            return '%s=%s' % (t[0], t[1])

    if response.get('Cache-Control'):
        cc = cc_delim_re.split(response['Cache-Control'])
        cc = dict(dictitem(el) for el in cc)
    else:
        cc = {}

    # If there's already a max-age header but we're being asked to set a new
    # max-age, use the minimum of the two ages. In practice this happens when
    # a decorator and a piece of middleware both operate on a given view.
    if 'max-age' in cc and 'max_age' in kwargs:
        kwargs['max_age'] = min(int(cc['max-age']), kwargs['max_age'])

    # Allow overriding private caching and vice versa
    if 'private' in cc and 'public' in kwargs:
        del cc['private']
    elif 'public' in cc and 'private' in kwargs:
        del cc['public']

    for (k, v) in kwargs.items():
        cc[k.replace('_', '-')] = v
    cc = ', '.join(dictvalue(el) for el in cc.items())
    response['Cache-Control'] = cc


def get_max_age(response):
    """
    Return the max-age from the response Cache-Control header as an integer,
    or None if it wasn't found or wasn't an integer.
    """
    if not response.has_header('Cache-Control'):
        return
    cc = dict(_to_tuple(el) for el in cc_delim_re.split(response['Cache-Control']))
    if 'max-age' in cc:
        try:
            return int(cc['max-age'])
        except (ValueError, TypeError):
            pass


def set_response_etag(response):
    if not response.streaming:
        response['ETag'] = quote_etag(hashlib.md5(response.content).hexdigest())
    return response


def _precondition_failed(request):
    logger.warning(
        'Precondition Failed: %s', request.path,
        extra={
            'status_code': 412,
            'request': request,
        },
    )
    return HttpResponse(status=412)


def _not_modified(request, response=None):
    new_response = HttpResponseNotModified()
    if response:
        # Preserve the headers required by Section 4.1 of RFC 7232, as well as
        # Last-Modified.
        for header in ('Cache-Control', 'Content-Location', 'Date', 'ETag', 'Expires', 'Last-Modified', 'Vary'):
            if header in response:
                new_response[header] = response[header]

        # Preserve cookies as per the cookie specification: "If a proxy server
        # receives a response which contains a Set-cookie header, it should
        # propagate the Set-cookie header to the client, regardless of whether
        # the response was 304 (Not Modified) or 200 (OK).
        # https://curl.haxx.se/rfc/cookie_spec.html
        new_response.cookies = response.cookies
    return new_response


def get_conditional_response(request, etag=None, last_modified=None, response=None):
    # Only return conditional responses on successful requests.
    if response and not (200 <= response.status_code < 300):
        return response

    # Get HTTP request headers.
    if_match_etags = parse_etags(request.META.get('HTTP_IF_MATCH', ''))
    if_unmodified_since = request.META.get('HTTP_IF_UNMODIFIED_SINCE')
    if if_unmodified_since:
        if_unmodified_since = parse_http_date_safe(if_unmodified_since)
    if_none_match_etags = parse_etags(request.META.get('HTTP_IF_NONE_MATCH', ''))
    if_modified_since = request.META.get('HTTP_IF_MODIFIED_SINCE')
    if if_modified_since:
        if_modified_since = parse_http_date_safe(if_modified_since)

    # Step 1 of section 6 of RFC 7232: Test the If-Match precondition.
    if (if_match_etags and not _if_match_passes(etag, if_match_etags)):
        return _precondition_failed(request)

    # Step 2: Test the If-Unmodified-Since precondition.
    if (not if_match_etags and if_unmodified_since and
            not _if_unmodified_since_passes(last_modified, if_unmodified_since)):
        return _precondition_failed(request)

    # Step 3: Test the If-None-Match precondition.
    if (if_none_match_etags and not _if_none_match_passes(etag, if_none_match_etags)):
        if request.method in ('GET', 'HEAD'):
            return _not_modified(request, response)
        else:
            return _precondition_failed(request)

    # Step 4: Test the If-Modified-Since precondition.
    if (not if_none_match_etags and if_modified_since and
            not _if_modified_since_passes(last_modified, if_modified_since)):
        if request.method in ('GET', 'HEAD'):
            return _not_modified(request, response)

    # Step 5: Test the If-Range precondition (not supported).
    # Step 6: Return original response since there isn't a conditional response.
    return response


def _if_match_passes(target_etag, etags):
    """
    Test the If-Match comparison as defined in section 3.1 of RFC 7232.
    """
    if not target_etag:
        # If there isn't an ETag, then there can't be a match.
        return False
    elif etags == ['*']:
        # The existence of an ETag means that there is "a current
        # representation for the target resource", even if the ETag is weak,
        # so there is a match to '*'.
        return True
    elif target_etag.startswith('W/'):
        # A weak ETag can never strongly match another ETag.
        return False
    else:
        # Since the ETag is strong, this will only return True if there's a
        # strong match.
        return target_etag in etags


def _if_unmodified_since_passes(last_modified, if_unmodified_since):
    """
    Test the If-Unmodified-Since comparison as defined in section 3.4 of
    RFC 7232.
    """
    return last_modified and last_modified <= if_unmodified_since


def _if_none_match_passes(target_etag, etags):
    """
    Test the If-None-Match comparison as defined in section 3.2 of RFC 7232.
    """
    if not target_etag:
        # If there isn't an ETag, then there isn't a match.
        return True
    elif etags == ['*']:
        # The existence of an ETag means that there is "a current
        # representation for the target resource", so there is a match to '*'.
        return False
    else:
        # The comparison should be weak, so look for a match after stripping
        # off any weak indicators.
        target_etag = target_etag.strip('W/')
        etags = (etag.strip('W/') for etag in etags)
        return target_etag not in etags


def _if_modified_since_passes(last_modified, if_modified_since):
    """
    Test the If-Modified-Since comparison as defined in section 3.3 of RFC 7232.
    """
    return not last_modified or last_modified > if_modified_since


def patch_response_headers(response, cache_timeout=None):
    """
    Add HTTP caching headers to the given HttpResponse: Expires and
    Cache-Control.

    Each header is only added if it isn't already set.

    cache_timeout is in seconds. The CACHE_MIDDLEWARE_SECONDS setting is used
    by default.
    """
    if cache_timeout is None:
        cache_timeout = settings.CACHE_MIDDLEWARE_SECONDS
    if cache_timeout < 0:
        cache_timeout = 0  # Can't have max-age negative
    if settings.USE_ETAGS and not response.has_header('ETag'):
        warnings.warn(
            "The USE_ETAGS setting is deprecated in favor of "
            "ConditionalGetMiddleware which sets the ETag regardless of the "
            "setting. patch_response_headers() won't do ETag processing in "
            "Django 2.1.",
            RemovedInDjango21Warning
        )
        if hasattr(response, 'render') and callable(response.render):
            response.add_post_render_callback(set_response_etag)
        else:
            response = set_response_etag(response)
    if not response.has_header('Expires'):
        response['Expires'] = http_date(time.time() + cache_timeout)
    patch_cache_control(response, max_age=cache_timeout)


def add_never_cache_headers(response):
    """
    Add headers to a response to indicate that a page should never be cached.
    """
    patch_response_headers(response, cache_timeout=-1)
    patch_cache_control(response, no_cache=True, no_store=True, must_revalidate=True)


def patch_vary_headers(response, newheaders):
    """
    Add (or update) the "Vary" header in the given HttpResponse object.
    newheaders is a list of header names that should be in "Vary". Existing
    headers in "Vary" aren't removed.
    """
    # Note that we need to keep the original order intact, because cache
    # implementations may rely on the order of the Vary contents in, say,
    # computing an MD5 hash.
    if response.has_header('Vary'):
        vary_headers = cc_delim_re.split(response['Vary'])
    else:
        vary_headers = []
    # Use .lower() here so we treat headers as case-insensitive.
    existing_headers = set(header.lower() for header in vary_headers)
    additional_headers = [newheader for newheader in newheaders
                          if newheader.lower() not in existing_headers]
    response['Vary'] = ', '.join(vary_headers + additional_headers)


def has_vary_header(response, header_query):
    """
    Check to see if the response has a given header name in its Vary header.
    """
    if not response.has_header('Vary'):
        return False
    vary_headers = cc_delim_re.split(response['Vary'])
    existing_headers = set(header.lower() for header in vary_headers)
    return header_query.lower() in existing_headers


def _i18n_cache_key_suffix(request, cache_key):
    """If necessary, add the current locale or time zone to the cache key."""
    if settings.USE_I18N or settings.USE_L10N:
        # first check if LocaleMiddleware or another middleware added
        # LANGUAGE_CODE to request, then fall back to the active language
        # which in turn can also fall back to settings.LANGUAGE_CODE
        cache_key += '.%s' % getattr(request, 'LANGUAGE_CODE', get_language())
    if settings.USE_TZ:
        # The datetime module doesn't restrict the output of tzname().
        # Windows is known to use non-standard, locale-dependent names.
        # User-defined tzinfo classes may return absolutely anything.
        # Hence this paranoid conversion to create a valid cache key.
        tz_name = force_text(get_current_timezone_name(), errors='ignore')
        cache_key += '.%s' % tz_name.encode('ascii', 'ignore').decode('ascii').replace(' ', '_')
    return cache_key


def _generate_cache_key(request, method, headerlist, key_prefix):
    """Return a cache key from the headers given in the header list."""
    ctx = hashlib.md5()
    for header in headerlist:
        value = request.META.get(header)
        if value is not None:
            ctx.update(force_bytes(value))
    url = hashlib.md5(force_bytes(iri_to_uri(request.build_absolute_uri())))
    cache_key = 'views.decorators.cache.cache_page.%s.%s.%s.%s' % (
        key_prefix, method, url.hexdigest(), ctx.hexdigest())
    return _i18n_cache_key_suffix(request, cache_key)


def _generate_cache_header_key(key_prefix, request):
    """Return a cache key for the header cache."""
    url = hashlib.md5(force_bytes(iri_to_uri(request.build_absolute_uri())))
    cache_key = 'views.decorators.cache.cache_header.%s.%s' % (
        key_prefix, url.hexdigest())
    return _i18n_cache_key_suffix(request, cache_key)


def get_cache_key(request, key_prefix=None, method='GET', cache=None):
    """
    Return a cache key based on the request URL and query. It can be used
    in the request phase because it pulls the list of headers to take into
    account from the global URL registry and uses those to build a cache key
    to check against.

    If there isn't a headerlist stored, return None, indicating that the page
    needs to be rebuilt.
    """
    if key_prefix is None:
        key_prefix = settings.CACHE_MIDDLEWARE_KEY_PREFIX
    cache_key = _generate_cache_header_key(key_prefix, request)
    if cache is None:
        cache = caches[settings.CACHE_MIDDLEWARE_ALIAS]
    headerlist = cache.get(cache_key)
    if headerlist is not None:
        return _generate_cache_key(request, method, headerlist, key_prefix)
    else:
        return None


def learn_cache_key(request, response, cache_timeout=None, key_prefix=None, cache=None):
    """
    Learn what headers to take into account for some request URL from the
    response object. Store those headers in a global URL registry so that
    later access to that URL will know what headers to take into account
    without building the response object itself. The headers are named in the
    Vary header of the response, but we want to prevent response generation.

    The list of headers to use for cache key generation is stored in the same
    cache as the pages themselves. If the cache ages some data out of the
    cache, this just means that we have to build the response once to get at
    the Vary header and so at the list of headers to use for the cache key.
    """
    if key_prefix is None:
        key_prefix = settings.CACHE_MIDDLEWARE_KEY_PREFIX
    if cache_timeout is None:
        cache_timeout = settings.CACHE_MIDDLEWARE_SECONDS
    cache_key = _generate_cache_header_key(key_prefix, request)
    if cache is None:
        cache = caches[settings.CACHE_MIDDLEWARE_ALIAS]
    if response.has_header('Vary'):
        is_accept_language_redundant = settings.USE_I18N or settings.USE_L10N
        # If i18n or l10n are used, the generated cache key will be suffixed
        # with the current locale. Adding the raw value of Accept-Language is
        # redundant in that case and would result in storing the same content
        # under multiple keys in the cache. See #18191 for details.
        headerlist = []
        for header in cc_delim_re.split(response['Vary']):
            header = header.upper().replace('-', '_')
            if header == 'ACCEPT_LANGUAGE' and is_accept_language_redundant:
                continue
            headerlist.append('HTTP_' + header)
        headerlist.sort()
        cache.set(cache_key, headerlist, cache_timeout)
        return _generate_cache_key(request, request.method, headerlist, key_prefix)
    else:
        # if there is no Vary header, we still need a cache key
        # for the request.build_absolute_uri()
        cache.set(cache_key, [], cache_timeout)
        return _generate_cache_key(request, request.method, [], key_prefix)


def _to_tuple(s):
    t = s.split('=', 1)
    if len(t) == 2:
        return t[0].lower(), t[1]
    return t[0].lower(), True
