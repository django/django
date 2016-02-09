import logging
import re

from django import http
from django.conf import settings
from django.core import urlresolvers
from django.core.exceptions import PermissionDenied
from django.core.mail import mail_managers
from django.utils.cache import get_conditional_response, set_response_etag
from django.utils.encoding import force_text
from django.utils.http import unquote_etag
from django.utils.six.moves.urllib.parse import urlparse

logger = logging.getLogger('django.request')


class CommonMiddleware(object):
    """
    "Common" middleware for taking care of some basic operations:

        - Forbids access to User-Agents in settings.DISALLOWED_USER_AGENTS

        - URL rewriting: Based on the APPEND_SLASH and PREPEND_WWW settings,
          this middleware appends missing slashes and/or prepends missing
          "www."s.

            - If APPEND_SLASH is set and the initial URL doesn't end with a
              slash, and it is not found in urlpatterns, a new URL is formed by
              appending a slash at the end. If this new URL is found in
              urlpatterns, then an HTTP-redirect is returned to this new URL;
              otherwise the initial URL is processed as usual.

          This behavior can be customized by subclassing CommonMiddleware and
          overriding the response_redirect_class attribute.

        - ETags: If the USE_ETAGS setting is set, ETags will be calculated from
          the entire page content and Not Modified responses will be returned
          appropriately.
    """

    response_redirect_class = http.HttpResponsePermanentRedirect

    def process_request(self, request):
        """
        Check for denied User-Agents and rewrite the URL based on
        settings.APPEND_SLASH and settings.PREPEND_WWW
        """

        # Check for denied User-Agents
        if 'HTTP_USER_AGENT' in request.META:
            for user_agent_regex in settings.DISALLOWED_USER_AGENTS:
                if user_agent_regex.search(request.META['HTTP_USER_AGENT']):
                    raise PermissionDenied('Forbidden user agent')

        # Check for a redirect based on settings.PREPEND_WWW
        host = request.get_host()

        if settings.PREPEND_WWW and host and not host.startswith('www.'):
            host = 'www.' + host

            # Check if we also need to append a slash so we can do it all
            # with a single redirect.
            if self.should_redirect_with_slash(request):
                path = self.get_full_path_with_slash(request)
            else:
                path = request.get_full_path()

            return self.response_redirect_class('%s://%s%s' % (request.scheme, host, path))

    def should_redirect_with_slash(self, request):
        """
        Return True if settings.APPEND_SLASH is True and appending a slash to
        the request path turns an invalid path into a valid one.
        """
        if settings.APPEND_SLASH and not request.get_full_path().endswith('/'):
            urlconf = getattr(request, 'urlconf', None)
            return (
                not urlresolvers.is_valid_path(request.path_info, urlconf)
                and urlresolvers.is_valid_path('%s/' % request.path_info, urlconf)
            )
        return False

    def get_full_path_with_slash(self, request):
        """
        Return the full path of the request with a trailing slash appended.

        Raise a RuntimeError if settings.DEBUG is True and request.method is
        POST, PUT, or PATCH.
        """
        new_path = request.get_full_path(force_append_slash=True)
        if settings.DEBUG and request.method in ('POST', 'PUT', 'PATCH'):
            raise RuntimeError(
                "You called this URL via %(method)s, but the URL doesn't end "
                "in a slash and you have APPEND_SLASH set. Django can't "
                "redirect to the slash URL while maintaining %(method)s data. "
                "Change your form to point to %(url)s (note the trailing "
                "slash), or set APPEND_SLASH=False in your Django settings." % {
                    'method': request.method,
                    'url': request.get_host() + new_path,
                }
            )
        return new_path

    def process_response(self, request, response):
        """
        Calculate the ETag, if needed.

        When the status code of the response is 404, it may redirect to a path
        with an appended slash if should_redirect_with_slash() returns True.
        """
        # If the given URL is "Not Found", then check if we should redirect to
        # a path with a slash appended.
        if response.status_code == 404:
            if self.should_redirect_with_slash(request):
                return self.response_redirect_class(self.get_full_path_with_slash(request))

        if settings.USE_ETAGS:
            if not response.has_header('ETag'):
                set_response_etag(response)

            if response.has_header('ETag'):
                return get_conditional_response(
                    request,
                    etag=unquote_etag(response['ETag']),
                    response=response,
                )

        return response


class BrokenLinkEmailsMiddleware(object):

    def process_response(self, request, response):
        """
        Send broken link emails for relevant 404 NOT FOUND responses.
        """
        if response.status_code == 404 and not settings.DEBUG:
            domain = request.get_host()
            path = request.get_full_path()
            referer = force_text(request.META.get('HTTP_REFERER', ''), errors='replace')

            if not self.is_ignorable_request(request, path, domain, referer):
                ua = force_text(request.META.get('HTTP_USER_AGENT', '<none>'), errors='replace')
                ip = request.META.get('REMOTE_ADDR', '<none>')
                mail_managers(
                    "Broken %slink on %s" % (
                        ('INTERNAL ' if self.is_internal_request(domain, referer) else ''),
                        domain
                    ),
                    "Referrer: %s\nRequested URL: %s\nUser agent: %s\n"
                    "IP address: %s\n" % (referer, path, ua, ip),
                    fail_silently=True)
        return response

    def is_internal_request(self, domain, referer):
        """
        Returns True if the referring URL is the same domain as the current request.
        """
        # Different subdomains are treated as different domains.
        return bool(re.match("^https?://%s/" % re.escape(domain), referer))

    def is_ignorable_request(self, request, uri, domain, referer):
        """
        Return True if the given request *shouldn't* notify the site managers
        according to project settings or in three specific situations:
         - If the referer is empty.
         - If a '?' in referer is identified as a search engine source.
         - If the referer is equal to the current URL, ignoring the scheme
           (assumed to be a poorly implemented bot).
        """
        if not referer:
            return True

        if not self.is_internal_request(domain, referer) and '?' in referer:
            return True

        parsed_referer = urlparse(referer)
        if parsed_referer.netloc in ['', domain] and parsed_referer.path == uri:
            return True

        return any(pattern.search(uri) for pattern in settings.IGNORABLE_404_URLS)
