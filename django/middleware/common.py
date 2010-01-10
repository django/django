import re

from django.conf import settings
from django import http
from django.core.mail import mail_managers
from django.utils.http import urlquote
from django.core import urlresolvers
from django.utils.hashcompat import md5_constructor

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
            if (not _is_valid_path(request.path_info) and
                    _is_valid_path("%s/" % request.path_info)):
                new_url[1] = new_url[1] + '/'
                if settings.DEBUG and request.method == 'POST':
                    raise RuntimeError, (""
                    "You called this URL via POST, but the URL doesn't end "
                    "in a slash and you have APPEND_SLASH set. Django can't "
                    "redirect to the slash URL while maintaining POST data. "
                    "Change your form to point to %s%s (note the trailing "
                    "slash), or set APPEND_SLASH=False in your Django "
                    "settings.") % (new_url[0], new_url[1])

        if new_url == old_url:
            # No redirects required.
            return
        if new_url[0]:
            newurl = "%s://%s%s" % (
                request.is_secure() and 'https' or 'http',
                new_url[0], urlquote(new_url[1]))
        else:
            newurl = urlquote(new_url[1])
        if request.GET:
            newurl += '?' + request.META['QUERY_STRING']
        return http.HttpResponsePermanentRedirect(newurl)

    def process_response(self, request, response):
        "Check for a flat page (for 404s) and calculate the Etag, if needed."
        if response.status_code == 404:
            if settings.SEND_BROKEN_LINK_EMAILS:
                # If the referrer was from an internal link or a non-search-engine site,
                # send a note to the managers.
                domain = request.get_host()
                referer = request.META.get('HTTP_REFERER', None)
                is_internal = _is_internal_request(domain, referer)
                path = request.get_full_path()
                if referer and not _is_ignorable_404(path) and (is_internal or '?' not in referer):
                    ua = request.META.get('HTTP_USER_AGENT', '<none>')
                    ip = request.META.get('REMOTE_ADDR', '<none>')
                    mail_managers("Broken %slink on %s" % ((is_internal and 'INTERNAL ' or ''), domain),
                        "Referrer: %s\nRequested URL: %s\nUser agent: %s\nIP address: %s\n" \
                                  % (referer, request.get_full_path(), ua, ip))
                return response

        # Use ETags, if requested.
        if settings.USE_ETAGS:
            if response.has_header('ETag'):
                etag = response['ETag']
            else:
                etag = '"%s"' % md5_constructor(response.content).hexdigest()
            if response.status_code >= 200 and response.status_code < 300 and request.META.get('HTTP_IF_NONE_MATCH') == etag:
                cookies = response.cookies
                response = http.HttpResponseNotModified()
                response.cookies = cookies
            else:
                response['ETag'] = etag

        return response

def _is_ignorable_404(uri):
    """
    Returns True if a 404 at the given URL *shouldn't* notify the site managers.
    """
    for start in settings.IGNORABLE_404_STARTS:
        if uri.startswith(start):
            return True
    for end in settings.IGNORABLE_404_ENDS:
        if uri.endswith(end):
            return True
    return False

def _is_internal_request(domain, referer):
    """
    Returns true if the referring URL is the same domain as the current request.
    """
    # Different subdomains are treated as different domains.
    return referer is not None and re.match("^https?://%s/" % re.escape(domain), referer)

def _is_valid_path(path):
    """
    Returns True if the given path resolves against the default URL resolver,
    False otherwise.

    This is a convenience method to make working with "is this a match?" cases
    easier, avoiding unnecessarily indented try...except blocks.
    """
    try:
        urlresolvers.resolve(path)
        return True
    except urlresolvers.Resolver404:
        return False

