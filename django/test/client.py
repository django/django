from cStringIO import StringIO
from django.contrib.admin.views.decorators import LOGIN_FORM_KEY, _encode_post_data
from django.core.handlers.base import BaseHandler
from django.core.handlers.wsgi import WSGIRequest
from django.dispatch import dispatcher
from django.http import urlencode, SimpleCookie
from django.template import signals
from django.utils.functional import curry

class ClientHandler(BaseHandler):
    """
    A HTTP Handler that can be used for testing purposes. 
    Uses the WSGI interface to compose requests, but returns
    the raw HttpResponse object
    """
    def __call__(self, environ):
        from django.conf import settings
        from django.core import signals

        # Set up middleware if needed. We couldn't do this earlier, because
        # settings weren't available.
        if self._request_middleware is None:
            self.load_middleware()

        dispatcher.send(signal=signals.request_started)
        try:
            request = WSGIRequest(environ)
            response = self.get_response(request.path, request)

            # Apply response middleware
            for middleware_method in self._response_middleware:
                response = middleware_method(request, response)

        finally:
            dispatcher.send(signal=signals.request_finished)
        
        return response

def store_rendered_templates(store, signal, sender, template, context):
    "A utility function for storing templates and contexts that are rendered"
    store.setdefault('template',[]).append(template)
    store.setdefault('context',[]).append(context)

def encode_multipart(boundary, data):
    """
    A simple method for encoding multipart POST data from a dictionary of
    form values.
    
    The key will be used as the form data name; the value will be transmitted
    as content. If the value is a file, the contents of the file will be sent
    as an application/octet-stream; otherwise, str(value) will be sent.
    """
    lines = []
    for (key, value) in data.items():
        if isinstance(value, file):
            lines.extend([
                '--' + boundary,
                'Content-Disposition: form-data; name="%s"' % key,
                '',
                '--' + boundary,
                'Content-Disposition: form-data; name="%s_file"; filename="%s"' % (key, value.name),
                'Content-Type: application/octet-stream',
                '',
                value.read()
            ])
        else:
            lines.extend([
                '--' + boundary,
                'Content-Disposition: form-data; name="%s"' % key,
                '',
                str(value)
            ])
        
    lines.extend([
        '--' + boundary + '--',
        '',
    ])
    return '\r\n'.join(lines)

class Client:
    """
    A class that can act as a client for testing purposes. 
      
    It allows the user to compose GET and POST requests, and
    obtain the response that the server gave to those requests.
    The server Response objects are annotated with the details
    of the contexts and templates that were rendered during the
    process of serving the request.

    Client objects are stateful - they will retain cookie (and
    thus session) details for the lifetime of the Client instance.
    
    This is not intended as a replacement for Twill/Selenium or
    the like - it is here to allow testing against the
    contexts and templates produced by a view, rather than the
    HTML rendered to the end-user.
    """
    def __init__(self, **defaults):
        self.handler = TestHandler()
        self.defaults = defaults
        self.cookie = SimpleCookie()
        
    def request(self, **request):
        """
        The master request method. Composes the environment dictionary 
        and passes to the handler, returning the result of the handler.
        Assumes defaults for the query environment, which can be overridden
        using the arguments to the request.
        """

        environ = {
            'HTTP_COOKIE':      self.cookie,
            'PATH_INFO':         '/',
            'QUERY_STRING':      '',
            'REQUEST_METHOD':    'GET',
            'SCRIPT_NAME':       None, 
            'SERVER_NAME':       'testserver',
            'SERVER_PORT':       80,
            'SERVER_PROTOCOL':   'HTTP/1.1',
        }        
        environ.update(self.defaults)
        environ.update(request)        

        # Curry a data dictionary into an instance of
        # the template renderer callback function
        data = {}
        on_template_render = curry(store_rendered_templates, data)
        dispatcher.connect(on_template_render, signal=signals.template_rendered)

        response = self.handler(environ)
        
        # Add any rendered template detail to the response
        # If there was only one template rendered (the most likely case), 
        # flatten the list to a single element
        for detail in ('template', 'context'):
            if data.get(detail):
                if len(data[detail]) == 1:
                    setattr(response, detail, data[detail][0]);
                else:
                    setattr(response, detail, data[detail])
            else:
                setattr(response, detail, None)
        
        if response.cookies:
            self.cookie.update(response.cookies)

        return response
        
    def get(self, path, data={}, **extra):
        "Request a response from the server using GET."
        r = {
            'CONTENT_LENGTH':  None,
            'CONTENT_TYPE':    'text/html; charset=utf-8',
            'PATH_INFO':       path,
            'QUERY_STRING':    urlencode(data),
            'REQUEST_METHOD': 'GET',
        }
        r.update(extra)
        
        return self.request(**r)
    
    def post(self, path, data={}, **extra):
        "Request a response from the server using POST."
        
        BOUNDARY = 'BoUnDaRyStRiNg'

        encoded = encode_multipart(BOUNDARY, data)
        stream = StringIO(encoded)
        r = {
            'CONTENT_LENGTH': len(encoded),
            'CONTENT_TYPE':   'multipart/form-data; boundary=%s' % BOUNDARY,
            'PATH_INFO':      path,
            'REQUEST_METHOD': 'POST',
            'wsgi.input':     stream,
        }
        r.update(extra)
        
        return self.request(**r)

    def login(self, path, username, password, **extra):
        """
        A specialized sequence of GET and POST to log into a view that
        is protected by @login_required or a similar access decorator.
        
        path should be the URL of the login page, or of any page that
        is login protected.
        
        Returns True if login was successful; False if otherwise.        
        """
        # First, GET the login page. 
        # This is required to establish the session.
        response = self.get(path)
        if response.status_code != 200:
            return False

        # Set up the block of form data required by the login page.
        form_data = {
            'username': username,
            'password': password,
            'this_is_the_login_form': 1,
            'post_data': _encode_post_data({LOGIN_FORM_KEY: 1})
        }
        response = self.post(path, data=form_data, **extra)
        
        # login page should give response 200 (if you requested the login
        # page specifically), or 302 (if you requested a login
        # protected page, to which the login can redirect).
        return response.status_code in (200,302)
