from django.conf import settings
from django.core import exceptions
from django.utils import httpwrappers
from django.core.mail import mail_managers
from django.views.core.flatfiles import flat_file
import md5, os
from urllib import urlencode

class CommonMiddleware:
    """
    "Common" middleware for taking care of some basic operations:

        - Forbids access to User-Agents in settings.DISALLOWED_USER_AGENTS

        - URL rewriting: based on the APPEND_SLASH and PREPEND_WWW settings,
          this middleware will -- shocking, isn't it -- append missing slashes
          and/or prepend missing "www."s.

        - ETags: if the USE_ETAGS setting is set, ETags will be calculated from
          the entire page content and Not Modified responses will be returned
          appropriately.

        - Flat files: for 404 responses, a flat file matching the given path
          will be looked up and used if found.

    You probably want the CommonMiddleware object to the first entry in your
    MIDDLEWARE_CLASSES setting;
    """

    def process_request(self, request):
        """
        Check for denied User-Agents and rewrite the URL based on
        settings.APPEND_SLASH and settings.PREPEND_WWW
        """

        # Check for denied User-Agents
        if request.META.has_key('HTTP_USER_AGENT'):
            for user_agent_regex in settings.DISALLOWED_USER_AGENTS:
                if user_agent_regex.search(request.META['HTTP_USER_AGENT']):
                    return httpwrappers.HttpResponseForbidden('<h1>Forbidden</h1>')

        # Check for a redirect based on settings.APPEND_SLASH and settings.PREPEND_WWW
        old_url = [request.META['HTTP_HOST'], request.path]
        new_url = old_url[:]
        if settings.PREPEND_WWW and not old_url[0].startswith('www.'):
            new_url[0] = 'www.' + old_url[0]
        # Append a slash if append_slash is set and the URL doesn't have a
        # trailing slash or a file extension.
        if settings.APPEND_SLASH and (old_url[1][-1] != '/') and ('.' not in old_url[1].split('/')[-1]):
            new_url[1] = new_url[1] + '/'
        if new_url != old_url:
            # Redirect
            newurl = "%s://%s%s" % (os.environ.get('HTTPS') == 'on' and 'https' or 'http', new_url[0], new_url[1])
            if request.GET:
                newurl += '?' + urlencode(request.GET)
            return httpwrappers.HttpResponseRedirect(newurl)

        return None

    def process_response(self, request, response):
        """
        Check for a flatfile (for 404s) and calculate the Etag, if needed.
        """

        # If this was a 404, check for a flat file
        if response.status_code == 404:
            try:
                response = flat_file(request, request.path)
            except exceptions.Http404:
                # If the referrer was from an internal link or a non-search-engine site,
                # send a note to the managers.
                if settings.SEND_BROKEN_LINK_EMAILS:
                    domain = request.META['HTTP_HOST']
                    referer = request.META.get('HTTP_REFERER', None)
                    is_internal = referer and (domain in referer)
                    path = request.get_full_path()
                    if referer and not _is_ignorable_404(path) and (is_internal or '?' not in referer):
                        mail_managers("Broken %slink on %s" % ((is_internal and 'INTERNAL ' or ''), domain),
                            "Referrer: %s\nRequested URL: %s\n" % (referer, request.get_full_path()))
                # If there's no flatfile we want to return the original 404 response
                return response

        # Use ETags, if requested
        if settings.USE_ETAGS:
            etag = md5.new(response.get_content_as_string('utf-8')).hexdigest()
            if request.META.get('HTTP_IF_NONE_MATCH') == etag:
                response = httpwrappers.HttpResponseNotModified()
            else:
                response['ETag'] = etag

        return response

def _is_ignorable_404(uri):
    "Returns True if a 404 at the given URL *shouldn't* notify the site managers"
    for start in settings.IGNORABLE_404_STARTS:
        if uri.startswith(start):
            return True
    for end in settings.IGNORABLE_404_ENDS:
        if uri.endswith(end):
            return True
    if '_files' in uri:
        # URI is probably from a locally-saved copy of the page.
        return True
    return False
