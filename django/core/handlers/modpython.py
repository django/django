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
            self._post, self._files = httpwrappers.parse_file_upload(self._req.headers_in, self._req.read())
        else:
            self._post, self._files = httpwrappers.QueryDict(self._req.read()), datastructures.MultiValueDict()

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

    def _load_session_and_user(self):
        from django.models.auth import sessions
        from django.conf.settings import AUTH_SESSION_COOKIE
        session_cookie = self.COOKIES.get(AUTH_SESSION_COOKIE, '')
        try:
            self._session = sessions.get_session_from_cookie(session_cookie)
            self._user = self._session.get_user()
        except sessions.SessionDoesNotExist:
            from django.parts.auth import anonymoususers
            self._session = None
            self._user = anonymoususers.AnonymousUser()

    def _get_session(self):
        if not hasattr(self, '_session'):
            self._load_session_and_user()
        return self._session

    def _set_session(self, session):
        self._session = session

    def _get_user(self):
        if not hasattr(self, '_user'):
            self._load_session_and_user()
        return self._user

    def _set_user(self, user):
        self._user = user

    GET = property(_get_get, _set_get)
    POST = property(_get_post, _set_post)
    COOKIES = property(_get_cookies, _set_cookies)
    FILES = property(_get_files)
    META = property(_get_meta)
    REQUEST = property(_get_request)
    session = property(_get_session, _set_session)
    user = property(_get_user, _set_user)

class ModPythonHandler:
    def __init__(self):
        self._request_middleware = self._view_middleware = self._response_middleware = None

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

    def load_middleware(self):
        """
        Populate middleware lists from settings.MIDDLEWARE_CLASSES.

        Must be called after the environment is fixed (see __call__).
        """
        from django.conf import settings
        from django.core import exceptions
        self._request_middleware = []
        self._view_middleware = []
        self._response_middleware = []
        for middleware_path in settings.MIDDLEWARE_CLASSES:
            dot = middleware_path.rindex('.')
            mw_module, mw_classname = middleware_path[:dot], middleware_path[dot+1:]
            try:
                mod = __import__(mw_module, '', '', [''])
            except ImportError, e:
                raise exceptions.ImproperlyConfigured, 'Error importing middleware %s: "%s"' % (mw_module, e)
            try:
                mw_class = getattr(mod, mw_classname)
            except AttributeError:
                raise exceptions.ImproperlyConfigured, 'Middleware module "%s" does not define a "%s" class' % (mw_module, mw_classname)

            try:
                mw_instance = mw_class()
            except exceptions.MiddlewareNotUsed:
                continue

            if hasattr(mw_instance, 'process_request'):
                self._request_middleware.append(mw_instance.process_request)
            if hasattr(mw_instance, 'process_view'):
                self._view_middleware.append(mw_instance.process_view)
            if hasattr(mw_instance, 'process_response'):
                self._response_middleware.insert(0, mw_instance.process_response)

    def get_response(self, path, request):
        "Returns an HttpResponse object for the given HttpRequest"
        from django.core import db, exceptions, urlresolvers
        from django.core.mail import mail_admins
        from django.conf.settings import DEBUG, INTERNAL_IPS, ROOT_URLCONF

        # Apply request middleware
        for middleware_method in self._request_middleware:
            response = middleware_method(request)
            if response:
                return response

        conf_module = __import__(ROOT_URLCONF, '', '', [''])
        resolver = urlresolvers.RegexURLResolver(conf_module.urlpatterns)
        try:
            callback, param_dict = resolver.resolve(path)
            # Apply view middleware
            for middleware_method in self._view_middleware:
                response = middleware_method(request, callback, param_dict)
                if response:
                    return response
            return callback(request, **param_dict)
        except exceptions.Http404:
            if DEBUG:
                return self.get_technical_error_response(is404=True)
            else:
                resolver = urlresolvers.Error404Resolver(conf_module.handler404)
                callback, param_dict = resolver.resolve()
                return callback(request, **param_dict)
        except db.DatabaseError:
            db.db.rollback()
            if DEBUG:
                return self.get_technical_error_response()
            else:
                subject = 'Database error (%s IP)' % (request.META['REMOTE_ADDR'] in INTERNAL_IPS and 'internal' or 'EXTERNAL')
                message = "%s\n\n%s" % (self._get_traceback(), request)
                mail_admins(subject, message, fail_silently=True)
                return self.get_friendly_error_response(request, conf_module)
        except exceptions.PermissionDenied:
            return httpwrappers.HttpResponseForbidden('<h1>Permission denied</h1>')
        except: # Handle everything else, including SuspiciousOperation, etc.
            if DEBUG:
                return self.get_technical_error_response()
            else:
                subject = 'Coding error (%s IP)' % (request.META['REMOTE_ADDR'] in INTERNAL_IPS and 'internal' or 'EXTERNAL')
                try:
                    request_repr = repr(request)
                except:
                    request_repr = "Request repr() unavailable"
                message = "%s\n\n%s" % (self._get_traceback(), request_repr)
                mail_admins(subject, message, fail_silently=True)
                return self.get_friendly_error_response(request, conf_module)

    def get_friendly_error_response(self, request, conf_module):
        """
        Returns an HttpResponse that displays a PUBLIC error message for a
        fundamental database or coding error.
        """
        from django.core import urlresolvers
        resolver = urlresolvers.Error404Resolver(conf_module.handler500)
        callback, param_dict = resolver.resolve()
        return callback(request, **param_dict)

    def get_technical_error_response(self, is404=False):
        """
        Returns an HttpResponse that displays a TECHNICAL error message for a
        fundamental database or coding error.
        """
        error_string = "<pre>There's been an error:\n\n%s</pre>" % self._get_traceback()
        responseClass = is404 and httpwrappers.HttpResponseNotFound or httpwrappers.HttpResponseServerError
        return responseClass(error_string)

    def _get_traceback(self):
        "Helper function to return the traceback as a string"
        import sys, traceback
        return '\n'.join(traceback.format_exception(*sys.exc_info()))

def populate_apache_request(http_response, mod_python_req):
    "Populates the mod_python request object with an HttpResponse"
    mod_python_req.content_type = http_response['Content-Type'] or httpwrappers.DEFAULT_MIME_TYPE
    if http_response.cookies:
        mod_python_req.headers_out['Set-Cookie'] = http_response.cookies.output(header='')
    for key, value in http_response.headers.items():
        if key != 'Content-Type':
            mod_python_req.headers_out[key] = value
    mod_python_req.status = http_response.status_code
    mod_python_req.write(http_response.get_content_as_string('utf-8'))

def handler(req):
    # mod_python hooks into this function.
    return ModPythonHandler()(req)
