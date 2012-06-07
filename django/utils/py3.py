# Compatibility layer for running Django both in 2.x and 3.x

import sys

if sys.version_info[0] < 3:
    PY3 = False
    # Changed module locations
    from urlparse import (urlparse, urlunparse, urljoin, urlsplit, urlunsplit,
                          urldefrag, parse_qsl)
    from urllib import (quote, unquote, quote_plus, urlopen, urlencode,
                        url2pathname, urlretrieve, unquote_plus)
    from urllib2 import (Request, OpenerDirector, UnknownHandler, HTTPHandler,
                         HTTPSHandler, HTTPDefaultErrorHandler, FTPHandler,
                         HTTPError, HTTPErrorProcessor)
    import urllib2
    import Cookie as cookies
    try:
        import cPickle as pickle
    except ImportError:
        import pickle
    try:
        import thread
    except ImportError:
        import dummy_thread as thread
    from htmlentitydefs import name2codepoint
    import HTMLParser
    from os import getcwdu
    from itertools import izip as zip
    unichr = unichr
    xrange = xrange
    maxsize = sys.maxint

    # Type aliases
    string_types = basestring,
    text_type = unicode
    integer_types = int, long
    long_type = long

    from io import BytesIO as OutputIO

    # Glue code for syntax differences
    def reraise(tp, value, tb=None):
        exec("raise tp, value, tb")

    def with_metaclass(meta, base=object):
        class _DjangoBase(base):
            __metaclass__ = meta
        return _DjangoBase

    iteritems = lambda o: o.iteritems()
    itervalues = lambda o: o.itervalues()
    iterkeys = lambda o: o.iterkeys()

    # n() is useful when python3 needs a str (unicode), and python2 str (bytes)
    n = lambda s: s.encode('utf-8')

else:
    PY3 = True
    import builtins

    # Changed module locations
    from urllib.parse import (urlparse, urlunparse, urlencode, urljoin,
                              urlsplit, urlunsplit, quote, unquote,
                              quote_plus, unquote_plus, parse_qsl,
                              urldefrag)
    from urllib.request import (urlopen, url2pathname, Request, OpenerDirector,
                                UnknownHandler, HTTPHandler, HTTPSHandler,
                                HTTPDefaultErrorHandler, FTPHandler,
                                HTTPError, HTTPErrorProcessor, urlretrieve)
    import urllib.request as urllib2
    import http.cookies as cookies
    import pickle
    try:
        import _thread as thread
    except ImportError:
        import _dummy_thread as thread
    from html.entities import name2codepoint
    import html.parser as HTMLParser
    from os import getcwd as getcwdu
    zip = zip
    unichr = chr
    xrange = range
    maxsize = sys.maxsize

    # Type aliases
    string_types = str,
    text_type = str
    integer_types = int,
    long_type = int

    from io import StringIO as OutputIO

    # Glue code for syntax differences
    def reraise(tp, value, tb=None):
        if value.__traceback__ is not tb:
            raise value.with_traceback(tb)
        raise value

    def with_metaclass(meta, base=object):
        ns = dict(base=base, meta=meta)
        exec("""class _DjangoBase(base, metaclass=meta):
    pass""", ns)
        return ns["_DjangoBase"]

    iteritems = lambda o: o.items()
    itervalues = lambda o: o.values()
    iterkeys = lambda o: o.keys()

    n = lambda s: s
