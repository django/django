"""
Implementation of JSONEncoder
"""
import re

ESCAPE = re.compile(r'[\x00-\x19\\"\b\f\n\r\t]')
ESCAPE_ASCII = re.compile(r'([\\"/]|[^\ -~])')
ESCAPE_DCT = {
    # escape all forward slashes to prevent </script> attack
    '/': '\\/',
    '\\': '\\\\',
    '"': '\\"',
    '\b': '\\b',
    '\f': '\\f',
    '\n': '\\n',
    '\r': '\\r',
    '\t': '\\t',
}
for i in range(0x20):
    ESCAPE_DCT.setdefault(chr(i), '\\u%04x' % (i,))

# assume this produces an infinity on all machines (probably not guaranteed)
INFINITY = float('1e66666')

def floatstr(o, allow_nan=True):
    # Check for specials.  Note that this type of test is processor- and/or
    # platform-specific, so do tests which don't depend on the internals.

    if o != o:
        text = 'NaN'
    elif o == INFINITY:
        text = 'Infinity'
    elif o == -INFINITY:
        text = '-Infinity'
    else:
        return str(o)

    if not allow_nan:
        raise ValueError("Out of range float values are not JSON compliant: %r"
            % (o,))

    return text


def encode_basestring(s):
    """
    Return a JSON representation of a Python string
    """
    def replace(match):
        return ESCAPE_DCT[match.group(0)]
    return '"' + ESCAPE.sub(replace, s) + '"'

def encode_basestring_ascii(s):
    def replace(match):
        s = match.group(0)
        try:
            return ESCAPE_DCT[s]
        except KeyError:
            return '\\u%04x' % (ord(s),)
    return '"' + str(ESCAPE_ASCII.sub(replace, s)) + '"'
        

class JSONEncoder(object):
    """
    Extensible JSON <http://json.org> encoder for Python data structures.

    Supports the following objects and types by default:
    
    +-------------------+---------------+
    | Python            | JSON          |
    +===================+===============+
    | dict              | object        |
    +-------------------+---------------+
    | list, tuple       | array         |
    +-------------------+---------------+
    | str, unicode      | string        |
    +-------------------+---------------+
    | int, long, float  | number        |
    +-------------------+---------------+
    | True              | true          |
    +-------------------+---------------+
    | False             | false         |
    +-------------------+---------------+
    | None              | null          |
    +-------------------+---------------+

    To extend this to recognize other objects, subclass and implement a
    ``.default()`` method with another method that returns a serializable
    object for ``o`` if possible, otherwise it should call the superclass
    implementation (to raise ``TypeError``).
    """
    __all__ = ['__init__', 'default', 'encode', 'iterencode']
    item_separator = ', '
    key_separator = ': '
    def __init__(self, skipkeys=False, ensure_ascii=True,
            check_circular=True, allow_nan=True, sort_keys=False,
            indent=None, separators=None):
        """
        Constructor for JSONEncoder, with sensible defaults.

        If skipkeys is False, then it is a TypeError to attempt
        encoding of keys that are not str, int, long, float or None.  If
        skipkeys is True, such items are simply skipped.

        If ensure_ascii is True, the output is guaranteed to be str
        objects with all incoming unicode characters escaped.  If
        ensure_ascii is false, the output will be unicode object.

        If check_circular is True, then lists, dicts, and custom encoded
        objects will be checked for circular references during encoding to
        prevent an infinite recursion (which would cause an OverflowError).
        Otherwise, no such check takes place.

        If allow_nan is True, then NaN, Infinity, and -Infinity will be
        encoded as such.  This behavior is not JSON specification compliant,
        but is consistent with most JavaScript based encoders and decoders.
        Otherwise, it will be a ValueError to encode such floats.

        If sort_keys is True, then the output of dictionaries will be
        sorted by key; this is useful for regression tests to ensure
        that JSON serializations can be compared on a day-to-day basis.

        If indent is a non-negative integer, then JSON array
        elements and object members will be pretty-printed with that
        indent level.  An indent level of 0 will only insert newlines.
        None is the most compact representation.

        If specified, separators should be a (item_separator, key_separator)
        tuple. The default is (', ', ': '). To get the most compact JSON
        representation you should specify (',', ':') to eliminate whitespace.
        """

        self.skipkeys = skipkeys
        self.ensure_ascii = ensure_ascii
        self.check_circular = check_circular
        self.allow_nan = allow_nan
        self.sort_keys = sort_keys
        self.indent = indent
        self.current_indent_level = 0
        if separators is not None:
            self.item_separator, self.key_separator = separators

    def _newline_indent(self):
        return '\n' + (' ' * (self.indent * self.current_indent_level))

    def _iterencode_list(self, lst, markers=None):
        if not lst:
            yield '[]'
            return
        if markers is not None:
            markerid = id(lst)
            if markerid in markers:
                raise ValueError("Circular reference detected")
            markers[markerid] = lst
        yield '['
        if self.indent is not None:
            self.current_indent_level += 1
            newline_indent = self._newline_indent()
            separator = self.item_separator + newline_indent
            yield newline_indent
        else:
            newline_indent = None
            separator = self.item_separator
        first = True
        for value in lst:
            if first:
                first = False
            else:
                yield separator
            for chunk in self._iterencode(value, markers):
                yield chunk
        if newline_indent is not None:
            self.current_indent_level -= 1
            yield self._newline_indent()
        yield ']'
        if markers is not None:
            del markers[markerid]

    def _iterencode_dict(self, dct, markers=None):
        if not dct:
            yield '{}'
            return
        if markers is not None:
            markerid = id(dct)
            if markerid in markers:
                raise ValueError("Circular reference detected")
            markers[markerid] = dct
        yield '{'
        key_separator = self.key_separator
        if self.indent is not None:
            self.current_indent_level += 1
            newline_indent = self._newline_indent()
            item_separator = self.item_separator + newline_indent
            yield newline_indent
        else:
            newline_indent = None
            item_separator = self.item_separator
        first = True
        if self.ensure_ascii:
            encoder = encode_basestring_ascii
        else:
            encoder = encode_basestring
        allow_nan = self.allow_nan
        if self.sort_keys:
            keys = dct.keys()
            keys.sort()
            items = [(k, dct[k]) for k in keys]
        else:
            items = dct.iteritems()
        for key, value in items:
            if isinstance(key, basestring):
                pass
            # JavaScript is weakly typed for these, so it makes sense to
            # also allow them.  Many encoders seem to do something like this.
            elif isinstance(key, float):
                key = floatstr(key, allow_nan)
            elif isinstance(key, (int, long)):
                key = str(key)
            elif key is True:
                key = 'true'
            elif key is False:
                key = 'false'
            elif key is None:
                key = 'null'
            elif self.skipkeys:
                continue
            else:
                raise TypeError("key %r is not a string" % (key,))
            if first:
                first = False
            else:
                yield item_separator
            yield encoder(key)
            yield key_separator
            for chunk in self._iterencode(value, markers):
                yield chunk
        if newline_indent is not None:
            self.current_indent_level -= 1
            yield self._newline_indent()
        yield '}'
        if markers is not None:
            del markers[markerid]

    def _iterencode(self, o, markers=None):
        if isinstance(o, basestring):
            if self.ensure_ascii:
                encoder = encode_basestring_ascii
            else:
                encoder = encode_basestring
            yield encoder(o)
        elif o is None:
            yield 'null'
        elif o is True:
            yield 'true'
        elif o is False:
            yield 'false'
        elif isinstance(o, (int, long)):
            yield str(o)
        elif isinstance(o, float):
            yield floatstr(o, self.allow_nan)
        elif isinstance(o, (list, tuple)):
            for chunk in self._iterencode_list(o, markers):
                yield chunk
        elif isinstance(o, dict):
            for chunk in self._iterencode_dict(o, markers):
                yield chunk
        else:
            if markers is not None:
                markerid = id(o)
                if markerid in markers:
                    raise ValueError("Circular reference detected")
                markers[markerid] = o
            for chunk in self._iterencode_default(o, markers):
                yield chunk
            if markers is not None:
                del markers[markerid]

    def _iterencode_default(self, o, markers=None):
        newobj = self.default(o)
        return self._iterencode(newobj, markers)

    def default(self, o):
        """
        Implement this method in a subclass such that it returns
        a serializable object for ``o``, or calls the base implementation
        (to raise a ``TypeError``).

        For example, to support arbitrary iterators, you could
        implement default like this::
            
            def default(self, o):
                try:
                    iterable = iter(o)
                except TypeError:
                    pass
                else:
                    return list(iterable)
                return JSONEncoder.default(self, o)
        """
        raise TypeError("%r is not JSON serializable" % (o,))

    def encode(self, o):
        """
        Return a JSON string representation of a Python data structure.

        >>> JSONEncoder().encode({"foo": ["bar", "baz"]})
        '{"foo":["bar", "baz"]}'
        """
        # This doesn't pass the iterator directly to ''.join() because it
        # sucks at reporting exceptions.  It's going to do this internally
        # anyway because it uses PySequence_Fast or similar.
        chunks = list(self.iterencode(o))
        return ''.join(chunks)

    def iterencode(self, o):
        """
        Encode the given object and yield each string
        representation as available.
        
        For example::
            
            for chunk in JSONEncoder().iterencode(bigobject):
                mysocket.write(chunk)
        """
        if self.check_circular:
            markers = {}
        else:
            markers = None
        return self._iterencode(o, markers)

__all__ = ['JSONEncoder']
