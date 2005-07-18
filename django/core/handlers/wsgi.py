from django.utils import datastructures, httpwrappers
from pprint import pformat

class WSGIRequest(httpwrappers.HttpRequest):
    def __init__(self, environ):
        self.environ = environ
        self.path = environ['PATH_INFO']
        self.META = environ

    def __repr__(self):
        from pprint import pformat
        return '<DjangoRequest\nGET:%s,\nPOST:%s,\nCOOKIES:%s,\nMETA:%s>' % \
            (pformat(self.GET), pformat(self.POST), pformat(self.COOKIES),
            pformat(self.META))

    def get_full_path(self):
        return '%s%s' % (self.path, self.environ['QUERY_STRING'] and ('?' + self.environ['QUERY_STRING']) or '')

    def _load_post_and_files(self):
        # Populates self._post and self._files
        if self.environ['REQUEST_METHOD'] == 'POST':
            post_data = self.environ['wsgi.input'].read(int(self.environ["CONTENT_LENGTH"]))
            if self.environ.get('CONTENT_TYPE', '').startswith('multipart'):
                header_dict = dict([(k, v) for k, v in self.environ.items() if k.startswith('HTTP_')])
                self._post, self._files = httpwrappers.parse_file_upload(header_dict, post_data)
            else:
                self._post, self._files = httpwrappers.QueryDict(post_data), datastructures.MultiValueDict()
        else:
            self._post, self._files = httpwrappers.QueryDict(''), datastructures.MultiValueDict()

    def _get_request(self):
        if not hasattr(self, '_request'):
           self._request = datastructures.MergeDict(self.POST, self.GET)
        return self._request

    def _get_get(self):
        if not hasattr(self, '_get'):
            self._get = httpwrappers.QueryDict(self.environ['QUERY_STRING'])
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
            self._cookies = httpwrappers.parse_cookie(self.environ.get('HTTP_COOKIE', ''))
        return self._cookies

    def _set_cookies(self, cookies):
        self._cookies = cookies

    def _get_files(self):
        if not hasattr(self, '_files'):
            self._load_post_and_files()
        return self._files

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
    REQUEST = property(_get_request)
    session = property(_get_session, _set_session)
    user = property(_get_user, _set_user)

class WSGIHandler:
    def __init__(self):
        self._request_middleware = self._view_middleware = self._response_middleware = None

    def __call__(self, environ, start_response):
        from django.conf import settings
        from django.core import db

        # Set up middleware if needed. We couldn't do this earlier, because
        # settings weren't available.
        if self._request_middleware is None:
            self.load_middleware()

        try:
            request = WSGIRequest(environ)
            response = self.get_response(request.path, request)
        finally:
            db.db.close()

        # Apply response middleware
        for middleware_method in self._response_middleware:
            response = middleware_method(request, response)

        status = str(response.status_code) + ' ' # TODO: Extra space here is a hack.
        response_headers = response.headers
        if response.cookies:
            response_headers['Set-Cookie'] = response.cookies.output(header='')
        output = [response.get_content_as_string('utf-8')]
        start_response(status, response_headers.items())
        return output

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
                raise exceptions.ImproperlyConfigured, \
                    'Error importing middleware %s: "%s"' % (mw_module, e)
            try:
                mw_class = getattr(mod, mw_classname)
            except AttributeError:
                raise exceptions.ImproperlyConfigured, \
                    'Middleware module "%s" does not define a "%s" class' % (mw_module, mw_classname)

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
                subject = 'Database error (%s IP)' % \
                    (request.META['REMOTE_ADDR'] in INTERNAL_IPS and 'internal' or 'EXTERNAL')
                message = "%s\n\n%s" % (self._get_traceback(), request)
                mail_admins(subject, message, fail_silently=True)
                return self.get_friendly_error_response(request, conf_module)
        except exceptions.PermissionDenied:
            return httpwrappers.HttpResponseForbidden('<h1>Permission denied</h1>')
        except: # Handle everything else, including SuspiciousOperation, etc.
            if DEBUG:
                return self.get_technical_error_response()
            else:
                subject = 'Coding error (%s IP)' % \
                    (request.META['REMOTE_ADDR'] in INTERNAL_IPS and 'internal' or 'EXTERNAL')
                message = "%s\n\n%s" % (self._get_traceback(), request)
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

class AdminMediaHandler:
    """
    WSGI middleware that intercepts calls to the admin media directory, as
    defined by the ADMIN_MEDIA_PREFIX setting, and serves those images.
    Use this ONLY LOCALLY, for development! This hasn't been tested for
    security and is not super efficient.
    """
    def __init__(self, application):
        from django.conf import settings
        import django
        self.application = application
        self.media_dir = django.__path__[0] + '/conf/admin_media'
        self.media_url = settings.ADMIN_MEDIA_PREFIX

    def __call__(self, environ, start_response):
        import os.path

        # Ignore requests that aren't under ADMIN_MEDIA_PREFIX. Also ignore
        # all requests if ADMIN_MEDIA_PREFIX isn't a relative URL.
        if self.media_url.startswith('http://') or self.media_url.startswith('https://') \
            or not environ['PATH_INFO'].startswith(self.media_url):
            return self.application(environ, start_response)

        # Find the admin file and serve it up, if it exists and is readable.
        relative_url = environ['PATH_INFO'][len(self.media_url):]
        file_path = os.path.join(self.media_dir, relative_url)
        if not os.path.exists(file_path):
            status = '404 NOT FOUND'
            headers = {'Content-type': 'text/plain'}
            output = ['Page not found: %s' % file_path]
        else:
            try:
                fp = open(file_path, 'r')
            except IOError:
                status = '401 UNAUTHORIZED'
                headers = {'Content-type': 'text/plain'}
                output = ['Permission denied: %s' % file_path]
            else:
                status = '200 OK'
                headers = {}
                output = [fp.read()]
                fp.close()
        start_response(status, headers.items())
        return output
