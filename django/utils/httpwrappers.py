from Cookie import SimpleCookie
from pprint import pformat
import datastructures

DEFAULT_MIME_TYPE = 'text/html'

class HttpRequest(object): # needs to be new-style class because subclasses define "property"s
    "A basic HTTP request"
    def __init__(self):
        self.GET, self.POST, self.COOKIES, self.META, self.FILES = {}, {}, {}, {}, {}
        self.path = ''

    def __repr__(self):
        return '<HttpRequest\nGET:%s,\nPOST:%s,\nCOOKIES:%s,\nMETA:%s>' % \
            (pformat(self.GET), pformat(self.POST), pformat(self.COOKIES),
            pformat(self.META))

    def __getitem__(self, key):
        for d in (self.POST, self.GET):
            if d.has_key(key):
                return d[key]
        raise KeyError, "%s not found in either POST or GET" % key

    def get_full_path(self):
        return ''

class ModPythonRequest(HttpRequest):
    def __init__(self, req):
        self._req = req
        self.path = req.uri

    def __repr__(self):
        return '<ModPythonRequest\nGET:%s,\nPOST:%s,\nCOOKIES:%s,\nMETA:%s>' % \
            (pformat(self.GET), pformat(self.POST), pformat(self.COOKIES),
            pformat(self.META))

    def get_full_path(self):
        return '%s%s' % (self.path, self._req.args and ('?' + self._req.args) or '')

    def _load_post_and_files(self):
        "Populates self._post and self._files"
        if self._req.headers_in.has_key('content-type') and self._req.headers_in['content-type'].startswith('multipart'):
            self._post, self._files = parse_file_upload(self._req.headers_in, self._req.read())
        else:
            self._post, self._files = QueryDict(self._req.read()), datastructures.MultiValueDict()

    def _get_request(self):
        if not hasattr(self, '_request'):
           self._request = datastructures.MergeDict(self.POST, self.GET)
        return self._request

    def _get_get(self):
        if not hasattr(self, '_get'):
            self._get = QueryDict(self._req.args)
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
            self._cookies = parse_cookie(self._req.headers_in.get('cookie', ''))
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

    GET = property(_get_get, _set_get)
    POST = property(_get_post, _set_post)
    COOKIES = property(_get_cookies, _set_cookies)
    FILES = property(_get_files)
    META = property(_get_meta)
    REQUEST = property(_get_request)

def parse_file_upload(header_dict, post_data):
    "Returns a tuple of (POST MultiValueDict, FILES MultiValueDict)"
    import email, email.Message
    from cgi import parse_header
    raw_message = '\r\n'.join(['%s:%s' % pair for pair in header_dict.items()])
    raw_message += '\r\n\r\n' + post_data
    msg = email.message_from_string(raw_message)
    POST = datastructures.MultiValueDict()
    FILES = datastructures.MultiValueDict()
    for submessage in msg.get_payload():
        if isinstance(submessage, email.Message.Message):
            name_dict = parse_header(submessage['Content-Disposition'])[1]
            # name_dict is something like {'name': 'file', 'filename': 'test.txt'} for file uploads
            # or {'name': 'blah'} for POST fields
            # We assume all uploaded files have a 'filename' set.
            if name_dict.has_key('filename'):
                assert type([]) != type(submessage.get_payload()), "Nested MIME messages are not supported"
                if not name_dict['filename'].strip():
                    continue
                # IE submits the full path, so trim everything but the basename.
                # (We can't use os.path.basename because it expects Linux paths.)
                filename = name_dict['filename'][name_dict['filename'].rfind("\\")+1:]
                FILES.appendlist(name_dict['name'], {
                    'filename': filename,
                    'content-type': (submessage.has_key('Content-Type') and submessage['Content-Type'] or None),
                    'content': submessage.get_payload(),
                })
            else:
                POST.appendlist(name_dict['name'], submessage.get_payload())
    return POST, FILES

class QueryDict(datastructures.MultiValueDict):
    """A specialized MultiValueDict that takes a query string when initialized.
    This is immutable unless you create a copy of it."""
    def __init__(self, query_string):
        try:
            from mod_python.util import parse_qsl
        except ImportError:
            from cgi import parse_qsl
        if not query_string:
            self.data = {}
            self._keys = []
        else:
            self.data = {}
            self._keys = []
            for name, value in parse_qsl(query_string, True): # keep_blank_values=True
                if name in self.data:
                    self.data[name].append(value)
                else:
                    self.data[name] = [value]
                if name not in self._keys:
                    self._keys.append(name)
        self._mutable = False

    def __setitem__(self, key, value):
        if not self._mutable:
            raise AttributeError, "This QueryDict instance is immutable"
        else:
            self.data[key] = [value]
            if not key in self._keys:
                self._keys.append(key)

    def setlist(self, key, list_):
        if not self._mutable:
            raise AttributeError, "This QueryDict instance is immutable"
        else:
            self.data[key] = list_
            if not key in self._keys:
                self._keys.append(key)

    def copy(self):
        "Returns a mutable copy of this object"
        cp = datastructures.MultiValueDict.copy(self)
        cp._mutable = True
        return cp

    def assert_synchronized(self):
        assert(len(self._keys) == len(self.data.keys())), \
            "QueryDict data structure is out of sync: %s %s" % (str(self._keys), str(self.data))

    def items(self):
        "Respect order preserved by self._keys"
        self.assert_synchronized()
        items = []
        for key in self._keys:
            if key in self.data:
                items.append((key, self.data[key][0]))
        return items

    def keys(self):
        self.assert_synchronized()
        return self._keys

def parse_cookie(cookie):
    if cookie == '':
        return {}
    c = SimpleCookie()
    c.load(cookie)
    cookiedict = {}
    for key in c.keys():
        cookiedict[key] = c.get(key).value
    return cookiedict

class HttpResponse:
    "A basic HTTP response, with content and dictionary-accessed headers"
    def __init__(self, content='', mimetype=DEFAULT_MIME_TYPE):
        self.content = content
        self.headers = {'Content-Type':mimetype}
        self.cookies = SimpleCookie()
        self.status_code = 200

    def __str__(self):
        "Full HTTP message, including headers"
        return '\n'.join(['%s: %s' % (key, value)
            for key, value in self.headers.items()]) \
            + '\n\n' + self.content

    def __setitem__(self, header, value):
        self.headers[header] = value

    def __delitem__(self, header):
        try:
            del self.headers[header]
        except KeyError:
            pass

    def __getitem__(self, header):
        return self.headers[header]

    def has_header(self, header):
        "Case-insensitive check for a header"
        header = header.lower()
        for key in self.headers.keys():
            if key.lower() == header:
                return True
        return False

    def set_cookie(self, key, value='', max_age=None, path='/', domain=None, secure=None):
        self.cookies[key] = value
        for var in ('max_age', 'path', 'domain', 'secure'):
            val = locals()[var]
            if val is not None:
                self.cookies[key][var.replace('_', '-')] = val

    def get_content_as_string(self, encoding):
        """
        Returns the content as a string, encoding it from a Unicode object if
        necessary.
        """
        if isinstance(self.content, unicode):
            return self.content.encode(encoding)
        return self.content

    # The remaining methods partially implement the file-like object interface.
    # See http://docs.python.org/lib/bltin-file-objects.html
    def write(self, content):
        self.content += content

    def flush(self):
        pass

    def tell(self):
        return len(self.content)

class HttpResponseRedirect(HttpResponse):
    def __init__(self, redirect_to):
        HttpResponse.__init__(self)
        self['Location'] = redirect_to
        self.status_code = 302

class HttpResponseNotModified(HttpResponse):
    def __init__(self):
        HttpResponse.__init__(self)
        self.status_code = 304

class HttpResponseNotFound(HttpResponse):
    def __init__(self, content='', mimetype=DEFAULT_MIME_TYPE):
        HttpResponse.__init__(self, content, mimetype)
        self.status_code = 404

class HttpResponseForbidden(HttpResponse):
    def __init__(self, content='', mimetype=DEFAULT_MIME_TYPE):
        HttpResponse.__init__(self, content, mimetype)
        self.status_code = 403

class HttpResponseGone(HttpResponse):
    def __init__(self, content='', mimetype=DEFAULT_MIME_TYPE):
        HttpResponse.__init__(self, content, mimetype)
        self.status_code = 410

class HttpResponseServerError(HttpResponse):
    def __init__(self, content='', mimetype=DEFAULT_MIME_TYPE):
        HttpResponse.__init__(self, content, mimetype)
        self.status_code = 500

def populate_apache_request(http_response, mod_python_req):
    "Populates the mod_python request object with an HttpResponse"
    mod_python_req.content_type = http_response['Content-Type'] or DEFAULT_MIME_TYPE
    del http_response['Content-Type']
    if http_response.cookies:
        mod_python_req.headers_out['Set-Cookie'] = http_response.cookies.output(header='')
    for key, value in http_response.headers.items():
        mod_python_req.headers_out[key] = value
    mod_python_req.status = http_response.status_code
    mod_python_req.write(http_response.get_content_as_string('utf-8'))
