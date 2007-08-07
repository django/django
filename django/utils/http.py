import urllib
from django.utils.encoding import smart_str, force_unicode
from django.utils.functional import allow_lazy

def urlquote(url, safe='/'):
    """
    A version of Python's urllib.quote() function that can operate on unicode
    strings. The url is first UTF-8 encoded before quoting. The returned string
    can safely be used as part of an argument to a subsequent iri_to_uri() call
    without double-quoting occurring.
    """
    return force_unicode(urllib.quote(smart_str(url)))
urlquote = allow_lazy(urlquote, unicode)

def urlquote_plus(url, safe=''):
    """
    A version of Python's urllib.quote_plus() function that can operate on
    unicode strings. The url is first UTF-8 encoded before quoting. The
    returned string can safely be used as part of an argument to a subsequent
    iri_to_uri() call without double-quoting occurring.
    """
    return force_unicode(urllib.quote_plus(smart_str(url), safe))
urlquote_plus = allow_lazy(urlquote_plus, unicode)

def urlencode(query, doseq=0):
    """
    A version of Python's urllib.urlencode() function that can operate on
    unicode strings. The parameters are first case to UTF-8 encoded strings and
    then encoded as per normal.
    """
    if hasattr(query, 'items'):
        query = query.items()
    return urllib.urlencode(
        [(smart_str(k),
         isinstance(v, (list,tuple)) and [smart_str(i) for i in v] or smart_str(v))
            for k, v in query],
        doseq)

