from Cookie import SimpleCookie
from pprint import pformat
from urllib import urlencode
from django.utils.datastructures import MultiValueDict

try:
    # The mod_python version is more efficient, so try importing it first.
    from mod_python.util import parse_qsl
except ImportError:
    from cgi import parse_qsl

class Http404(Exception):
    pass

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

    def has_key(self, key):
        return self.GET.has_key(key) or self.POST.has_key(key)

    def get_full_path(self):
        return ''

def parse_file_upload(header_dict, post_data):
    "Returns a tuple of (POST MultiValueDict, FILES MultiValueDict)"
    import email, email.Message
    from cgi import parse_header
    raw_message = '\r\n'.join(['%s:%s' % pair for pair in header_dict.items()])
    raw_message += '\r\n\r\n' + post_data
    msg = email.message_from_string(raw_message)
    POST = MultiValueDict()
    FILES = MultiValueDict()
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

class QueryDict(MultiValueDict):
    """A specialized MultiValueDict that takes a query string when initialized.
    This is immutable unless you create a copy of it."""
    def __init__(self, query_string, mutable=False):
        MultiValueDict.__init__(self)
        self._mutable = True
        for key, value in parse_qsl((query_string or ''), True): # keep_blank_values=True
            self.appendlist(key, value)
        self._mutable = mutable

    def _assert_mutable(self):
        if not self._mutable:
            raise AttributeError, "This QueryDict instance is immutable"

    def __setitem__(self, key, value):
        self._assert_mutable()
        MultiValueDict.__setitem__(self, key, value)

    def __copy__(self):
        result = self.__class__('', mutable=True)
        for key, value in dict.items(self):
            dict.__setitem__(result, key, value)
        return result

    def __deepcopy__(self, memo={}):
        import copy
        result = self.__class__('', mutable=True)
        memo[id(self)] = result
        for key, value in dict.items(self):
            dict.__setitem__(result, copy.deepcopy(key, memo), copy.deepcopy(value, memo))
        return result

    def setlist(self, key, list_):
        self._assert_mutable()
        MultiValueDict.setlist(self, key, list_)

    def appendlist(self, key, value):
        self._assert_mutable()
        MultiValueDict.appendlist(self, key, value)

    def update(self, other_dict):
        self._assert_mutable()
        MultiValueDict.update(self, other_dict)

    def pop(self, key):
        self._assert_mutable()
        return MultiValueDict.pop(self, key)

    def popitem(self):
        self._assert_mutable()
        return MultiValueDict.popitem(self)

    def clear(self):
        self._assert_mutable()
        MultiValueDict.clear(self)

    def setdefault(self, *args):
        self._assert_mutable()
        return MultiValueDict.setdefault(self, *args)

    def copy(self):
        "Returns a mutable copy of this object."
        return self.__deepcopy__()

    def urlencode(self):
        output = []
        for k, list_ in self.lists():
            output.extend([urlencode({k: v}) for v in list_])
        return '&'.join(output)

def parse_cookie(cookie):
    if cookie == '':
        return {}
    c = SimpleCookie()
    c.load(cookie)
    cookiedict = {}
    for key in c.keys():
        cookiedict[key] = c.get(key).value
    return cookiedict

class HttpResponse(object):
    "A basic HTTP response, with content and dictionary-accessed headers"
    def __init__(self, content='', mimetype=None):
        from django.conf import settings
        self._charset = settings.DEFAULT_CHARSET
        if not mimetype:
            mimetype = "%s; charset=%s" % (settings.DEFAULT_CONTENT_TYPE, settings.DEFAULT_CHARSET)
        if hasattr(content, '__iter__'):
            self._iterator = content
            self._is_string = False
        else:
            self._iterator = [content]
            self._is_string = True
        self.headers = {'Content-Type': mimetype}
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

    def set_cookie(self, key, value='', max_age=None, expires=None, path='/', domain=None, secure=None):
        self.cookies[key] = value
        for var in ('max_age', 'path', 'domain', 'secure', 'expires'):
            val = locals()[var]
            if val is not None:
                self.cookies[key][var.replace('_', '-')] = val

    def delete_cookie(self, key):
        try:
            self.cookies[key]['max_age'] = 0
        except KeyError:
            pass

    def _get_content(self):
        content = ''.join(self._iterator)
        if isinstance(content, unicode):
            content = content.encode(self._charset)
        return content

    def _set_content(self, value):
        self._iterator = [value]
        self._is_string = True

    content = property(_get_content, _set_content)

    def _get_iterator(self):
        "Output iterator. Converts data into client charset if necessary."
        for chunk in self._iterator:
            if isinstance(chunk, unicode):
                chunk = chunk.encode(self._charset)
            yield chunk

    iterator = property(_get_iterator)

    # The remaining methods partially implement the file-like object interface.
    # See http://docs.python.org/lib/bltin-file-objects.html
    def write(self, content):
        if not self._is_string:
            raise Exception, "This %s instance is not writable" % self.__class__
        self._iterator.append(content)

    def flush(self):
        pass

    def tell(self):
        if not self._is_string:
            raise Exception, "This %s instance cannot tell its position" % self.__class__
        return sum([len(chunk) for chunk in self._iterator])

class HttpResponseRedirect(HttpResponse):
    def __init__(self, redirect_to):
        HttpResponse.__init__(self)
        self['Location'] = redirect_to
        self.status_code = 302

class HttpResponsePermanentRedirect(HttpResponse):
    def __init__(self, redirect_to):
        HttpResponse.__init__(self)
        self['Location'] = redirect_to
        self.status_code = 301

class HttpResponseNotModified(HttpResponse):
    def __init__(self):
        HttpResponse.__init__(self)
        self.status_code = 304

class HttpResponseNotFound(HttpResponse):
    def __init__(self, *args, **kwargs):
        HttpResponse.__init__(self, *args, **kwargs)
        self.status_code = 404

class HttpResponseForbidden(HttpResponse):
    def __init__(self, *args, **kwargs):
        HttpResponse.__init__(self, *args, **kwargs)
        self.status_code = 403

class HttpResponseNotAllowed(HttpResponse):
    def __init__(self, permitted_methods):
        HttpResponse.__init__(self)
        self['Allow'] = ', '.join(permitted_methods)
        self.status_code = 405

class HttpResponseGone(HttpResponse):
    def __init__(self, *args, **kwargs):
        HttpResponse.__init__(self, *args, **kwargs)
        self.status_code = 410

class HttpResponseServerError(HttpResponse):
    def __init__(self, *args, **kwargs):
        HttpResponse.__init__(self, *args, **kwargs)
        self.status_code = 500

def get_host(request):
    """Gets the HTTP host from the environment or request headers."""
    host = request.META.get('HTTP_X_FORWARDED_HOST', '')
    if not host:
        host = request.META.get('HTTP_HOST', '')
    return host
