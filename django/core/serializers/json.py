"""
Serialize data to/from JSON
"""

import datetime
from django.utils import simplejson
from django.utils.simplejson import decoder
from django.core.serializers.python import Serializer as PythonSerializer
from django.core.serializers.python import Deserializer as PythonDeserializer
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
try:
    import decimal
except ImportError:
    from django.utils import _decimal as decimal    # Python 2.3 fallback

class Serializer(PythonSerializer):
    """
    Convert a queryset to JSON.
    """
    def end_serialization(self):
        simplejson.dump(self.objects, self.stream, cls=DjangoJSONEncoder, **self.options)

    def getvalue(self):
        if callable(getattr(self.stream, 'getvalue', None)):
            return self.stream.getvalue()

def Deserializer(stream_or_string, **options):
    """
    Deserialize a stream or string of JSON data.
    """
    if isinstance(stream_or_string, basestring):
        stream = StringIO(stream_or_string)
    else:
        stream = stream_or_string
    #for obj in PythonDeserializer(simplejson.load(stream, cls=DjangoJSONDecoder)):
    for obj in PythonDeserializer(simplejson.load(stream)):
        yield obj

class DjangoJSONEncoder(simplejson.JSONEncoder):
    """
    JSONEncoder subclass that knows how to encode date/time and decimal types.
    """

    DATE_FORMAT = "%Y-%m-%d"
    TIME_FORMAT = "%H:%M:%S"

    def default(self, o):
        if isinstance(o, datetime.datetime):
            return o.strftime("%s %s" % (self.DATE_FORMAT, self.TIME_FORMAT))
        elif isinstance(o, datetime.date):
            return o.strftime(self.DATE_FORMAT)
        elif isinstance(o, datetime.time):
            return o.strftime(self.TIME_FORMAT)
        elif isinstance(o, decimal.Decimal):
            return str(o)
        else:
            return super(DjangoJSONEncoder, self).default(o)

# Older, deprecated class name (for backwards compatibility purposes).
DateTimeAwareJSONEncoder = DjangoJSONEncoder

## Our override for simplejson.JSONNumber, because we want to use decimals in
## preference to floats (we can convert decimal -> float when they stored, if
## needed, but cannot go the other way).
#def DjangoNumber(match, context):
#    match = DjangoNumber.regex.match(match.string, *match.span())
#    integer, frac, exp = match.groups()
#    if exp:
#        res = float(integer + (frac or '') + (exp or ''))
#    elif frac:
#        res = decimal.Decimal(integer + frac)
#    else:
#        res = int(integer)
#    return res, None
#decoder.pattern(r'(-?(?:0|[1-9]\d*))(\.\d+)?([eE][-+]?\d+)?')(DjangoNumber)
#
#converters = decoder.ANYTHING[:]
#converters[-1] = DjangoNumber
#decoder.JSONScanner = decoder.Scanner(converters)
#
#class DjangoJSONDecoder(simplejson.JSONDecoder):
#    _scanner = decoder.Scanner(converters)
#
