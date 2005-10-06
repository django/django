from django.core.handlers.base import BaseHandler
from django.utils import datastructures, httpwrappers
from pprint import pformat
import os

# NOTE: do *not* import settings (or any module which eventually imports
# settings) until after ModPythonHandler has been called; otherwise os.environ
# won't be set up correctly (with respect to settings).

class ModPythonRequest(httpwrappers.HttpRequest):
    def __init__(self, req):
        self._req = req
        self.path = req.uri

    def __repr__(self):
        return '<ModPythonRequest\npath:%s,\nGET:%s,\nPOST:%s,\nCOOKIES:%s,\nMETA:%s,\nuser:%s>' % \
            (self.path, pformat(self.GET), pformat(self.POST), pformat(self.COOKIES),
            pformat(self.META), pformat(self.user))

    def get_full_path(self):
        return '%s%s' % (self.path, self._req.args and ('?' + self._req.args) or '')

    def _load_post_and_files(self):
        "Populates self._post and self._files"
        if self._req.headers_in.has_key('content-type') and self._req.headers_in['content-type'].startswith('multipart'):
            self._post, self._files = httpwrappers.parse_file_upload(self._req.headers_in, self.raw_post_data)
        else:
            self._post, self._files = httpwrappers.QueryDict(self.raw_post_data), datastructures.MultiValueDict()

    def _get_request(self):
        if not hasattr(self, '_request'):
           self._request = datastructures.MergeDict(self.POST, self.GET)
        return self._request

    def _get_get(self):
        if not hasattr(self, '_get'):
            self._get = httpwrappers.QueryDict(self._req.args)
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
            self._cookies = httpwrappers.parse_cookie(self._req.headers_in.get('cookie', ''))
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
                'CONTENT_LENGTH':    self._req.clength, # This may be wrong
                'CONTENT_TYPE':      self._req.content_type, # This may be wrong
                'GATEWAY_INTERFACE': 'CGI/1.1',
                'PATH_INFO':         self._req.path_info,
                'PATH_TRANSLATED':   None, # Not supported
                'QUERY_STRING':      self._req.args,
                'REMOTE_ADDR':       self._req.connection.remote_ip,
                'REMOTE_HOST':       None, # DNS lookups not supported
                'REMOTE_IDENT':      self._req.connection.remote_logname,
                'REMOTE_USER':       self._req.user,
                'REQUEST_METHOD':    self._req.method,
                'SCRIPT_NAME':       None, # Not supported
                'SERVER_NAME':       self._req.server.server_hostname,
                'SERVER_PORT':       self._req.server.port,
                'SERVER_PROTOCOL':   self._req.protocol,
                'SERVER_SOFTWARE':   'mod_python'
            }
            for key, value in self._req.headers_in.items():
                key = 'HTTP_' + key.upper().replace('-', '_')
                self._meta[key] = value
        return self._meta

    def _get_raw_post_data(self):
        try:
            return self._raw_post_data
        except AttributeError:
            self._raw_post_data = self._req.read()
            return self._raw_post_data

    def _get_user(self):
        if not hasattr(self, '_user'):
            from django.models.auth import users
            try:
                user_id = self.session[users.SESSION_KEY]
                if not user_id:
                    raise ValueError
                self._user = users.get_object(pk=user_id)
            except (AttributeError, KeyError, ValueError, users.UserDoesNotExist):
                from django.parts.auth import anonymoususers
                self._user = anonymoususers.AnonymousUser()
        return self._user

    def _set_user(self, user):
        self._user = user

    GET = property(_get_get, _set_get)
    POST = property(_get_post, _set_post)
    COOKIES = property(_get_cookies, _set_cookies)
    FILES = property(_get_files)
    META = property(_get_meta)
    REQUEST = property(_get_request)
    raw_post_data = property(_get_raw_post_data)
    user = property(_get_user, _set_user)

class ModPythonHandler(BaseHandler):
    def __call__(self, req):
        # mod_python fakes the environ, and thus doesn't process SetEnv.  This fixes that
        os.environ.update(req.subprocess_env)

        # now that the environ works we can see the correct settings, so imports
        # that use settings now can work
        from django.conf import settings
        from django.core import db

        # if we need to set up middleware, now that settings works we can do it now.
        if self._request_middleware is None:
            self.load_middleware()

        try:
            request = ModPythonRequest(req)
            response = self.get_response(req.uri, request)
        finally:
            db.db.close()

        # Apply response middleware
        for middleware_method in self._response_middleware:
            response = middleware_method(request, response)

        # Convert our custom HttpResponse object back into the mod_python req.
        populate_apache_request(response, req)
        return 0 # mod_python.apache.OK

def populate_apache_request(http_response, mod_python_req):
    "Populates the mod_python request object with an HttpResponse"
    from django.conf import settings
    mod_python_req.content_type = http_response['Content-Type']
    for key, value in http_response.headers.items():
        if key != 'Content-Type':
            mod_python_req.headers_out[key] = value
    for c in http_response.cookies.values():
        mod_python_req.headers_out.add('Set-Cookie', c.output(header=''))
    mod_python_req.status = http_response.status_code
    mod_python_req.write(http_response.get_content_as_string(settings.DEFAULT_CHARSET))

def handler(req):
    # mod_python hooks into this function.
    return ModPythonHandler()(req)
