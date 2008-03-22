import os
from Cookie import SimpleCookie, CookieError
from pprint import pformat
from urllib import urlencode
from urlparse import urljoin
try:
    # The mod_python version is more efficient, so try importing it first.
    from mod_python.util import parse_qsl
except ImportError:
    from cgi import parse_qsl

from django.utils.datastructures import MultiValueDict, FileDict
from django.utils.encoding import smart_str, iri_to_uri, force_unicode

from utils import *

RESERVED_CHARS="!*'();:@&=+$,/?%#[]"


class Http404(Exception):
    pass

class HttpRequest(object):
    """A basic HTTP request."""

    # The encoding used in GET/POST dicts. None means use default setting.
    _encoding = None

    def __init__(self):
        self.GET, self.POST, self.COOKIES, self.META, self.FILES = {}, {}, {}, {}, {}
        self.path = ''
        self.method = None

    def __repr__(self):
        return '<HttpRequest\nGET:%s,\nPOST:%s,\nCOOKIES:%s,\nMETA:%s>' % \
            (pformat(self.GET), pformat(self.POST), pformat(self.COOKIES),
            pformat(self.META))

    def __getitem__(self, key):
        for d in (self.POST, self.GET):
            if key in d:
                return d[key]
        raise KeyError, "%s not found in either POST or GET" % key

    def has_key(self, key):
        return key in self.GET or key in self.POST

    __contains__ = has_key

    def get_host(self):
        """Returns the HTTP host using the environment or request headers."""
        # We try three options, in order of decreasing preference.
        if 'HTTP_X_FORWARDED_HOST' in self.META:
            host = self.META['HTTP_X_FORWARDED_HOST']
        elif 'HTTP_HOST' in self.META:
            host = self.META['HTTP_HOST']
        else:
            # Reconstruct the host using the algorithm from PEP 333.
            host = self.META['SERVER_NAME']
            server_port = self.META['SERVER_PORT']
            if server_port != (self.is_secure() and 443 or 80):
                host = '%s:%s' % (host, server_port)
        return host

    def get_full_path(self):
        return ''

    def build_absolute_uri(self, location=None):
        """
        Builds an absolute URI from the location and the variables available in
        this request. If no location is specified, the absolute URI is built on
        ``request.get_full_path()``.
        """
        if not location:
            location = self.get_full_path()
        if not ':' in location:
            current_uri = '%s://%s%s' % (self.is_secure() and 'https' or 'http',
                                         self.get_host(), self.path)
            location = urljoin(current_uri, location)
        return location

    def is_secure(self):
        return os.environ.get("HTTPS") == "on"

    def is_ajax(self):
        return self.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'

    def _set_encoding(self, val):
        """
        Sets the encoding used for GET/POST accesses. If the GET or POST
        dictionary has already been created, it is removed and recreated on the
        next access (so that it is decoded correctly).
        """
        self._encoding = val
        if hasattr(self, '_get'):
            del self._get
        if hasattr(self, '_post'):
            del self._post

    def _get_encoding(self):
        return self._encoding

    encoding = property(_get_encoding, _set_encoding)

def parse_file_upload(header_dict, post_data):
    """Returns a tuple of (POST QueryDict, FILES MultiValueDict)."""
    import email, email.Message
    from cgi import parse_header
    raw_message = '\r\n'.join(['%s:%s' % pair for pair in header_dict.items()])
    raw_message += '\r\n\r\n' + post_data
    msg = email.message_from_string(raw_message)
    POST = QueryDict('', mutable=True)
    FILES = MultiValueDict()
    for submessage in msg.get_payload():
        if submessage and isinstance(submessage, email.Message.Message):
            name_dict = parse_header(submessage['Content-Disposition'])[1]
            # name_dict is something like {'name': 'file', 'filename': 'test.txt'} for file uploads
            # or {'name': 'blah'} for POST fields
            # We assume all uploaded files have a 'filename' set.
            if 'filename' in name_dict:
                assert type([]) != type(submessage.get_payload()), "Nested MIME messages are not supported"
                if not name_dict['filename'].strip():
                    continue
                # IE submits the full path, so trim everything but the basename.
                # (We can't use os.path.basename because that uses the server's
                # directory separator, which may not be the same as the
                # client's one.)
                filename = name_dict['filename'][name_dict['filename'].rfind("\\")+1:]
                FILES.appendlist(name_dict['name'], FileDict({
                    'filename': filename,
                    'content-type': 'Content-Type' in submessage and submessage['Content-Type'] or None,
                    'content': submessage.get_payload(),
                }))
            else:
                POST.appendlist(name_dict['name'], submessage.get_payload())
    return POST, FILES


class QueryDict(MultiValueDict):
    """
    A specialized MultiValueDict that takes a query string when initialized.
    This is immutable unless you create a copy of it.

    Values retrieved from this class are converted from the given encoding
    (DEFAULT_CHARSET by default) to unicode.
    """
    def __init__(self, query_string, mutable=False, encoding=None):
        MultiValueDict.__init__(self)
        if not encoding:
            # *Important*: do not import settings any earlier because of note
            # in core.handlers.modpython.
            from django.conf import settings
            encoding = settings.DEFAULT_CHARSET
        self.encoding = encoding
        self._mutable = True
        for key, value in parse_qsl((query_string or ''), True): # keep_blank_values=True
            self.appendlist(force_unicode(key, encoding, errors='replace'),
                            force_unicode(value, encoding, errors='replace'))
        self._mutable = mutable

    def _assert_mutable(self):
        if not self._mutable:
            raise AttributeError("This QueryDict instance is immutable")

    def __setitem__(self, key, value):
        self._assert_mutable()
        key = str_to_unicode(key, self.encoding)
        value = str_to_unicode(value, self.encoding)
        MultiValueDict.__setitem__(self, key, value)

    def __delitem__(self, key):
        self._assert_mutable()
        super(QueryDict, self).__delitem__(key)

    def __copy__(self):
        result = self.__class__('', mutable=True)
        for key, value in dict.items(self):
            dict.__setitem__(result, key, value)
        return result

    def __deepcopy__(self, memo):
        import copy
        result = self.__class__('', mutable=True)
        memo[id(self)] = result
        for key, value in dict.items(self):
            dict.__setitem__(result, copy.deepcopy(key, memo), copy.deepcopy(value, memo))
        return result

    def setlist(self, key, list_):
        self._assert_mutable()
        key = str_to_unicode(key, self.encoding)
        list_ = [str_to_unicode(elt, self.encoding) for elt in list_]
        MultiValueDict.setlist(self, key, list_)

    def setlistdefault(self, key, default_list=()):
        self._assert_mutable()
        if key not in self:
            self.setlist(key, default_list)
        return MultiValueDict.getlist(self, key)

    def appendlist(self, key, value):
        self._assert_mutable()
        key = str_to_unicode(key, self.encoding)
        value = str_to_unicode(value, self.encoding)
        MultiValueDict.appendlist(self, key, value)

    def update(self, other_dict):
        self._assert_mutable()
        f = lambda s: str_to_unicode(s, self.encoding)
        d = dict([(f(k), f(v)) for k, v in other_dict.items()])
        MultiValueDict.update(self, d)

    def pop(self, key, *args):
        self._assert_mutable()
        return MultiValueDict.pop(self, key, *args)

    def popitem(self):
        self._assert_mutable()
        return MultiValueDict.popitem(self)

    def clear(self):
        self._assert_mutable()
        MultiValueDict.clear(self)

    def setdefault(self, key, default=None):
        self._assert_mutable()
        key = str_to_unicode(key, self.encoding)
        default = str_to_unicode(default, self.encoding)
        return MultiValueDict.setdefault(self, key, default)

    def copy(self):
        """Returns a mutable copy of this object."""
        return self.__deepcopy__({})

    def urlencode(self):
        output = []
        for k, list_ in self.lists():
            k = smart_str(k, self.encoding)
            output.extend([urlencode({k: smart_str(v, self.encoding)}) for v in list_])
        return '&'.join(output)

def parse_cookie(cookie):
    if cookie == '':
        return {}
    try:
        c = SimpleCookie()
        c.load(cookie)
    except CookieError:
        # Invalid cookie
        return {}

    cookiedict = {}
    for key in c.keys():
        cookiedict[key] = c.get(key).value
    return cookiedict

class HttpResponse(object):
    """A basic HTTP response, with content and dictionary-accessed headers."""

    status_code = 200

    def __init__(self, content='', mimetype=None, status=None,
            content_type=None):
        from django.conf import settings
        self._charset = settings.DEFAULT_CHARSET
        if mimetype:
            content_type = mimetype     # For backwards compatibility
        if not content_type:
            content_type = "%s; charset=%s" % (settings.DEFAULT_CONTENT_TYPE,
                    settings.DEFAULT_CHARSET)
        if not isinstance(content, basestring) and hasattr(content, '__iter__'):
            self._container = content
            self._is_string = False
        else:
            self._container = [content]
            self._is_string = True
        self.cookies = SimpleCookie()
        if status:
            self.status_code = status

        # _headers is a mapping of the lower-case name to the original case of
        # the header (required for working with legacy systems) and the header
        # value.
        self._headers = {'content-type': ('Content-Type', content_type)}

    def __str__(self):
        """Full HTTP message, including headers."""
        return '\n'.join(['%s: %s' % (key, value)
            for key, value in self._headers.values()]) \
            + '\n\n' + self.content

    def _convert_to_ascii(self, *values):
        """Converts all values to ascii strings."""
        for value in values:
            if isinstance(value, unicode):
                try:
                    yield value.encode('us-ascii')
                except UnicodeError, e:
                    e.reason += ', HTTP response headers must be in US-ASCII format'
                    raise
            else:
                yield str(value)

    def __setitem__(self, header, value):
        header, value = self._convert_to_ascii(header, value)
        self._headers[header.lower()] = (header, value)

    def __delitem__(self, header):
        try:
            del self._headers[header.lower()]
        except KeyError:
            pass

    def __getitem__(self, header):
        return self._headers[header.lower()][1]

    def has_header(self, header):
        """Case-insensitive check for a header."""
        return self._headers.has_key(header.lower())

    __contains__ = has_header

    def items(self):
        return self._headers.values()

    def get(self, header, alternate):
        return self._headers.get(header.lower(), (None, alternate))[1]

    def set_cookie(self, key, value='', max_age=None, expires=None, path='/',
                   domain=None, secure=False):
        self.cookies[key] = value
        if max_age is not None:
            self.cookies[key]['max-age'] = max_age
        if expires is not None:
            self.cookies[key]['expires'] = expires
        if path is not None:
            self.cookies[key]['path'] = path
        if domain is not None:
            self.cookies[key]['domain'] = domain
        if secure:
            self.cookies[key]['secure'] = True

    def delete_cookie(self, key, path='/', domain=None):
        self.set_cookie(key, max_age=0, path=path, domain=domain,
                        expires='Thu, 01-Jan-1970 00:00:00 GMT')

    def _get_content(self):
        if self.has_header('Content-Encoding'):
            return ''.join(self._container)
        return smart_str(''.join(self._container), self._charset)

    def _set_content(self, value):
        self._container = [value]
        self._is_string = True

    content = property(_get_content, _set_content)

    def __iter__(self):
        self._iterator = iter(self._container)
        return self

    def next(self):
        chunk = self._iterator.next()
        if isinstance(chunk, unicode):
            chunk = chunk.encode(self._charset)
        return str(chunk)

    def close(self):
        if hasattr(self._container, 'close'):
            self._container.close()

    # The remaining methods partially implement the file-like object interface.
    # See http://docs.python.org/lib/bltin-file-objects.html
    def write(self, content):
        if not self._is_string:
            raise Exception("This %s instance is not writable" % self.__class__)
        self._container.append(content)

    def flush(self):
        pass

    def tell(self):
        if not self._is_string:
            raise Exception("This %s instance cannot tell its position" % self.__class__)
        return sum([len(chunk) for chunk in self._container])

class HttpResponseRedirect(HttpResponse):
    status_code = 302

    def __init__(self, redirect_to):
        HttpResponse.__init__(self)
        self['Location'] = iri_to_uri(redirect_to)

class HttpResponsePermanentRedirect(HttpResponse):
    status_code = 301

    def __init__(self, redirect_to):
        HttpResponse.__init__(self)
        self['Location'] = iri_to_uri(redirect_to)

class HttpResponseNotModified(HttpResponse):
    status_code = 304

class HttpResponseBadRequest(HttpResponse):
    status_code = 400

class HttpResponseNotFound(HttpResponse):
    status_code = 404

class HttpResponseForbidden(HttpResponse):
    status_code = 403

class HttpResponseNotAllowed(HttpResponse):
    status_code = 405

    def __init__(self, permitted_methods):
        HttpResponse.__init__(self)
        self['Allow'] = ', '.join(permitted_methods)

class HttpResponseGone(HttpResponse):
    status_code = 410

    def __init__(self, *args, **kwargs):
        HttpResponse.__init__(self, *args, **kwargs)

class HttpResponseServerError(HttpResponse):
    status_code = 500

    def __init__(self, *args, **kwargs):
        HttpResponse.__init__(self, *args, **kwargs)

# A backwards compatible alias for HttpRequest.get_host.
def get_host(request):
    return request.get_host()

# It's neither necessary nor appropriate to use
# django.utils.encoding.smart_unicode for parsing URLs and form inputs. Thus,
# this slightly more restricted function.
def str_to_unicode(s, encoding):
    """
    Converts basestring objects to unicode, using the given encoding. Illegally
    encoded input characters are replaced with Unicode "unknown" codepoint
    (\ufffd).

    Returns any non-basestring objects without change.
    """
    if isinstance(s, str):
        return unicode(s, encoding, 'replace')
    else:
        return s
