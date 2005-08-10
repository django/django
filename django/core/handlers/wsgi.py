from django.core.handlers.base import BaseHandler
from django.utils import datastructures, httpwrappers
from pprint import pformat

STATUS_CODE_TEXT = {
    200: 'OK',
    404: 'NOT FOUND',
    500: 'INTERNAL SERVER ERROR',
}

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
                header_dict['Content-Type'] = self.environ.get('CONTENT_TYPE', '')
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

class WSGIHandler(BaseHandler):
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

        try:
            status_text = STATUS_CODE_TEXT[response.status_code]
        except KeyError:
            status_text = 'UNKNOWN STATUS CODE'
        status = '%s %s' % (response.status_code, status_text)
        response_headers = response.headers
        if response.cookies:
            response_headers['Set-Cookie'] = response.cookies.output(header='')
        output = [response.get_content_as_string('utf-8')]
        start_response(status, response_headers.items())
        return output

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
