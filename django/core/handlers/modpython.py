import os
from pprint import pformat
import sys
from warnings import warn

from django import http
from django.core import signals
from django.core.handlers.base import BaseHandler
from django.core.urlresolvers import set_script_prefix
from django.utils import datastructures
from django.utils.encoding import force_unicode, smart_str, iri_to_uri
from django.utils.log import getLogger

logger = getLogger('django.request')


# NOTE: do *not* import settings (or any module which eventually imports
# settings) until after ModPythonHandler has been called; otherwise os.environ
# won't be set up correctly (with respect to settings).

class ModPythonRequest(http.HttpRequest):
    def __init__(self, req):
        self._req = req
        # FIXME: This isn't ideal. The request URI may be encoded (it's
        # non-normalized) slightly differently to the "real" SCRIPT_NAME
        # and PATH_INFO values. This causes problems when we compute path_info,
        # below. For now, don't use script names that will be subject to
        # encoding/decoding.
        self.path = force_unicode(req.uri)
        root = req.get_options().get('django.root', '')
        self.django_root = root
        # req.path_info isn't necessarily computed correctly in all
        # circumstances (it's out of mod_python's control a bit), so we use
        # req.uri and some string manipulations to get the right value.
        if root and req.uri.startswith(root):
            self.path_info = force_unicode(req.uri[len(root):])
        else:
            self.path_info = self.path
        if not self.path_info:
            # Django prefers empty paths to be '/', rather than '', to give us
            # a common start character for URL patterns. So this is a little
            # naughty, but also pretty harmless.
            self.path_info = u'/'
        self._post_parse_error = False
        self._stream = self._req
        self._read_started = False

    def __repr__(self):
        # Since this is called as part of error handling, we need to be very
        # robust against potentially malformed input.
        try:
            get = pformat(self.GET)
        except:
            get = '<could not parse>'
        if self._post_parse_error:
            post = '<could not parse>'
        else:
            try:
                post = pformat(self.POST)
            except:
                post = '<could not parse>'
        try:
            cookies = pformat(self.COOKIES)
        except:
            cookies = '<could not parse>'
        try:
            meta = pformat(self.META)
        except:
            meta = '<could not parse>'
        return smart_str(u'<ModPythonRequest\npath:%s,\nGET:%s,\nPOST:%s,\nCOOKIES:%s,\nMETA:%s>' %
                         (self.path, unicode(get), unicode(post),
                          unicode(cookies), unicode(meta)))

    def get_full_path(self):
        # RFC 3986 requires self._req.args to be in the ASCII range, but this
        # doesn't always happen, so rather than crash, we defensively encode it.
        return '%s%s' % (self.path, self._req.args and ('?' + iri_to_uri(self._req.args)) or '')

    def is_secure(self):
        try:
            return self._req.is_https()
        except AttributeError:
            # mod_python < 3.2.10 doesn't have req.is_https().
            return self._req.subprocess_env.get('HTTPS', '').lower() in ('on', '1')

    def _get_request(self):
        if not hasattr(self, '_request'):
            self._request = datastructures.MergeDict(self.POST, self.GET)
        return self._request

    def _get_get(self):
        if not hasattr(self, '_get'):
            self._get = http.QueryDict(self._req.args, encoding=self._encoding)
        return self._get

    def _set_get(self, get):
        self._get = get

    def _get_post(self):
        if not hasattr(self, '_post'):
            self._load_post_and_files()
        return self._post

    def _set_post(self, post):
        self._post = post

    def _get_cookies(self):
        if not hasattr(self, '_cookies'):
            self._cookies = http.parse_cookie(self._req.headers_in.get('cookie', ''))
        return self._cookies

    def _set_cookies(self, cookies):
        self._cookies = cookies

    def _get_files(self):
        if not hasattr(self, '_files'):
            self._load_post_and_files()
        return self._files

    def _get_meta(self):
        "Lazy loader that returns self.META dictionary"
        if not hasattr(self, '_meta'):
            self._meta = {
                'AUTH_TYPE':         self._req.ap_auth_type,
                'CONTENT_LENGTH':    self._req.headers_in.get('content-length', 0),
                'CONTENT_TYPE':      self._req.headers_in.get('content-type'),
                'GATEWAY_INTERFACE': 'CGI/1.1',
                'PATH_INFO':         self.path_info,
                'PATH_TRANSLATED':   None, # Not supported
                'QUERY_STRING':      self._req.args,
                'REMOTE_ADDR':       self._req.connection.remote_ip,
                'REMOTE_HOST':       None, # DNS lookups not supported
                'REMOTE_IDENT':      self._req.connection.remote_logname,
                'REMOTE_USER':       self._req.user,
                'REQUEST_METHOD':    self._req.method,
                'SCRIPT_NAME':       self.django_root,
                'SERVER_NAME':       self._req.server.server_hostname,
                'SERVER_PORT':       self._req.connection.local_addr[1],
                'SERVER_PROTOCOL':   self._req.protocol,
                'SERVER_SOFTWARE':   'mod_python'
            }
            for key, value in self._req.headers_in.items():
                key = 'HTTP_' + key.upper().replace('-', '_')
                self._meta[key] = value
        return self._meta

    def _get_method(self):
        return self.META['REQUEST_METHOD'].upper()

    GET = property(_get_get, _set_get)
    POST = property(_get_post, _set_post)
    COOKIES = property(_get_cookies, _set_cookies)
    FILES = property(_get_files)
    META = property(_get_meta)
    REQUEST = property(_get_request)
    method = property(_get_method)

class ModPythonHandler(BaseHandler):
    request_class = ModPythonRequest

    def __call__(self, req):
        warn(('The mod_python handler is deprecated; use a WSGI or FastCGI server instead.'),
             PendingDeprecationWarning)

        # mod_python fakes the environ, and thus doesn't process SetEnv.  This fixes that
        os.environ.update(req.subprocess_env)

        # now that the environ works we can see the correct settings, so imports
        # that use settings now can work
        from django.conf import settings

        # if we need to set up middleware, now that settings works we can do it now.
        if self._request_middleware is None:
            self.load_middleware()

        set_script_prefix(req.get_options().get('django.root', ''))
        signals.request_started.send(sender=self.__class__)
        try:
            try:
                request = self.request_class(req)
            except UnicodeDecodeError:
                logger.warning('Bad Request (UnicodeDecodeError)',
                    exc_info=sys.exc_info(),
                    extra={
                        'status_code': 400,
                    }
                )
                response = http.HttpResponseBadRequest()
            else:
                response = self.get_response(request)
        finally:
            signals.request_finished.send(sender=self.__class__)

        # Convert our custom HttpResponse object back into the mod_python req.
        req.content_type = response['Content-Type']
        for key, value in response.items():
            if key != 'content-type':
                req.headers_out[str(key)] = str(value)
        for c in response.cookies.values():
            req.headers_out.add('Set-Cookie', c.output(header=''))
        req.status = response.status_code
        try:
            for chunk in response:
                req.write(chunk)
        finally:
            response.close()

        return 0 # mod_python.apache.OK

def handler(req):
    # mod_python hooks into this function.
    return ModPythonHandler()(req)
