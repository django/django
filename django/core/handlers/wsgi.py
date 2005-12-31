from django.core.handlers.base import BaseHandler
from django.core import signals
from django.dispatch import dispatcher
from django.utils import datastructures, httpwrappers
from pprint import pformat

# See http://www.w3.org/Protocols/rfc2616/rfc2616-sec10.html
STATUS_CODE_TEXT = {
    100: 'CONTINUE',
    101: 'SWITCHING PROTOCOLS',
    200: 'OK',
    201: 'CREATED',
    202: 'ACCEPTED',
    203: 'NON-AUTHORITATIVE INFORMATION',
    204: 'NO CONTENT',
    205: 'RESET CONTENT',
    206: 'PARTIAL CONTENT',
    300: 'MULTIPLE CHOICES',
    301: 'MOVED PERMANENTLY',
    302: 'FOUND',
    303: 'SEE OTHER',
    304: 'NOT MODIFIED',
    305: 'USE PROXY',
    306: 'RESERVED',
    307: 'TEMPORARY REDIRECT',
    400: 'BAD REQUEST',
    401: 'UNAUTHORIZED',
    402: 'PAYMENT REQUIRED',
    403: 'FORBIDDEN',
    404: 'NOT FOUND',
    405: 'METHOD NOT ALLOWED',
    406: 'NOT ACCEPTABLE',
    407: 'PROXY AUTHENTICATION REQUIRED',
    408: 'REQUEST TIMEOUT',
    409: 'CONFLICT',
    410: 'GONE',
    411: 'LENGTH REQUIRED',
    412: 'PRECONDITION FAILED',
    413: 'REQUEST ENTITY TOO LARGE',
    414: 'REQUEST-URI TOO LONG',
    415: 'UNSUPPORTED MEDIA TYPE',
    416: 'REQUESTED RANGE NOT SATISFIABLE',
    417: 'EXPECTATION FAILED',
    500: 'INTERNAL SERVER ERROR',
    501: 'NOT IMPLEMENTED',
    502: 'BAD GATEWAY',
    503: 'SERVICE UNAVAILABLE',
    504: 'GATEWAY TIMEOUT',
    505: 'HTTP VERSION NOT SUPPORTED',
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
            if self.environ.get('CONTENT_TYPE', '').startswith('multipart'):
                header_dict = dict([(k, v) for k, v in self.environ.items() if k.startswith('HTTP_')])
                header_dict['Content-Type'] = self.environ.get('CONTENT_TYPE', '')
                self._post, self._files = httpwrappers.parse_file_upload(header_dict, self.raw_post_data)
            else:
                self._post, self._files = httpwrappers.QueryDict(self.raw_post_data), datastructures.MultiValueDict()
        else:
            self._post, self._files = httpwrappers.QueryDict(''), datastructures.MultiValueDict()

    def _get_request(self):
        if not hasattr(self, '_request'):
           self._request = datastructures.MergeDict(self.POST, self.GET)
        return self._request

    def _get_get(self):
        if not hasattr(self, '_get'):
            # The WSGI spec says 'QUERY_STRING' may be absent.
            self._get = httpwrappers.QueryDict(self.environ.get('QUERY_STRING', ''))
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

    def _get_raw_post_data(self):
        try:
            return self._raw_post_data
        except AttributeError:
            self._raw_post_data = self.environ['wsgi.input'].read(int(self.environ["CONTENT_LENGTH"]))
            return self._raw_post_data

    def _get_user(self):
        if not hasattr(self, '_user'):
            from django.models.auth import User, SESSION_KEY
            try:
                user_id = self.session[SESSION_KEY]
                if not user_id:
                    raise ValueError
                self._user = User.objects.get_object(pk=user_id)
            except (AttributeError, KeyError, ValueError, User.DoesNotExist):
                from django.parts.auth import anonymoususers
                self._user = anonymoususers.AnonymousUser()
        return self._user

    def _set_user(self, user):
        self._user = user

    GET = property(_get_get, _set_get)
    POST = property(_get_post, _set_post)
    COOKIES = property(_get_cookies, _set_cookies)
    FILES = property(_get_files)
    REQUEST = property(_get_request)
    raw_post_data = property(_get_raw_post_data)
    user = property(_get_user, _set_user)

class WSGIHandler(BaseHandler):
    def __call__(self, environ, start_response):
        from django.conf import settings

        # Set up middleware if needed. We couldn't do this earlier, because
        # settings weren't available.
        if self._request_middleware is None:
            self.load_middleware()

        dispatcher.send(signal=signals.request_started)
        try:
            request = WSGIRequest(environ)
            response = self.get_response(request.path, request)
        finally:
            dispatcher.send(signal=signals.request_finished)

        # Apply response middleware
        for middleware_method in self._response_middleware:
            response = middleware_method(request, response)

        try:
            status_text = STATUS_CODE_TEXT[response.status_code]
        except KeyError:
            status_text = 'UNKNOWN STATUS CODE'
        status = '%s %s' % (response.status_code, status_text)
        response_headers = response.headers.items()
        for c in response.cookies.values():
            response_headers.append(('Set-Cookie', c.output(header='')))
        output = [response.get_content_as_string(settings.DEFAULT_CHARSET)]
        start_response(status, response_headers)
        return output
