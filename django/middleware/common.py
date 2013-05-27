import hashlib
import logging
import re
import warnings

from django.conf import settings
from django.core.mail import mail_managers
from django.core import urlresolvers
from django import http
from django.utils.encoding import force_text
from django.utils.http import urlquote
from django.utils import six


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

        - ETags: If the USE_ETAGS setting is set, ETags will be calculated from
          the entire page content and Not Modified responses will be returned
          appropriately.
    """

    def process_request(self, request):
        """
        Check for denied User-Agents and rewrite the URL based on
        settings.APPEND_SLASH and settings.PREPEND_WWW
        """

        # Check for denied User-Agents
        if 'HTTP_USER_AGENT' in request.META:
            for user_agent_regex in settings.DISALLOWED_USER_AGENTS:
                if user_agent_regex.search(request.META['HTTP_USER_AGENT']):
                    logger.warning('Forbidden (User agent): %s', request.path,
                        extra={
                            'status_code': 403,
                            'request': request
                        }
                    )
                    return http.HttpResponseForbidden('<h1>Forbidden</h1>')

        # Check for a redirect based on settings.APPEND_SLASH
        # and settings.PREPEND_WWW
        host = request.get_host()
        old_url = [host, request.path]
        new_url = old_url[:]

        if (settings.PREPEND_WWW and old_url[0] and
                not old_url[0].startswith('www.')):
            new_url[0] = 'www.' + old_url[0]

        # Append a slash if APPEND_SLASH is set and the URL doesn't have a
        # trailing slash and there is no pattern for the current path
        if settings.APPEND_SLASH and (not old_url[1].endswith('/')):
            urlconf = getattr(request, 'urlconf', None)
            if (not urlresolvers.is_valid_path(request.path_info, urlconf) and
                    urlresolvers.is_valid_path("%s/" % request.path_info, urlconf)):
                new_url[1] = new_url[1] + '/'
                if settings.DEBUG and request.method == 'POST':
                    raise RuntimeError((""
                    "You called this URL via POST, but the URL doesn't end "
                    "in a slash and you have APPEND_SLASH set. Django can't "
                    "redirect to the slash URL while maintaining POST data. "
                    "Change your form to point to %s%s (note the trailing "
                    "slash), or set APPEND_SLASH=False in your Django "
                    "settings.") % (new_url[0], new_url[1]))

        if new_url == old_url:
            # No redirects required.
            return
        if new_url[0]:
            newurl = "%s://%s%s" % (
                'https' if request.is_secure() else 'http',
                new_url[0], urlquote(new_url[1]))
        else:
            newurl = urlquote(new_url[1])
        if request.META.get('QUERY_STRING', ''):
            if six.PY3:
                newurl += '?' + request.META['QUERY_STRING']
            else:
                # `query_string` is a bytestring. Appending it to the unicode
                # string `newurl` will fail if it isn't ASCII-only. This isn't
                # allowed; only broken software generates such query strings.
                # Better drop the invalid query string than crash (#15152).
                try:
                    newurl += '?' + request.META['QUERY_STRING'].decode()
                except UnicodeDecodeError:
                    pass
        return http.HttpResponsePermanentRedirect(newurl)

    def process_response(self, request, response):
        """
        Calculate the ETag, if needed.
        """
        if settings.SEND_BROKEN_LINK_EMAILS:
            warnings.warn("SEND_BROKEN_LINK_EMAILS is deprecated. "
                "Use BrokenLinkEmailsMiddleware instead.",
                PendingDeprecationWarning, stacklevel=2)
            BrokenLinkEmailsMiddleware().process_response(request, response)

        if settings.USE_ETAGS:
            if response.has_header('ETag'):
                etag = response['ETag']
            elif response.streaming:
                etag = None
            else:
                etag = '"%s"' % hashlib.md5(response.content).hexdigest()
            if etag is not None:
                if (200 <= response.status_code < 300
                    and request.META.get('HTTP_IF_NONE_MATCH') == etag):
                    cookies = response.cookies
                    response = http.HttpResponseNotModified()
                    response.cookies = cookies
                else:
                    response['ETag'] = etag

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
                ua = request.META.get('HTTP_USER_AGENT', '<none>')
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
        Returns True if the given request *shouldn't* notify the site managers.
        """
        # '?' in referer is identified as search engine source
        if (not referer or
                (not self.is_internal_request(domain, referer) and '?' in referer)):
            return True
        return any(pattern.search(uri) for pattern in settings.IGNORABLE_404_URLS)
