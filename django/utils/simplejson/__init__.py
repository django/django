r"""
A simple, fast, extensible JSON encoder and decoder

JSON (JavaScript Object Notation) <http://json.org> is a subset of
JavaScript syntax (ECMA-262 3rd edition) used as a lightweight data
interchange format.

simplejson exposes an API familiar to uses of the standard library
marshal and pickle modules.

Encoding basic Python object hierarchies::
    
    >>> import simplejson
    >>> simplejson.dumps(['foo', {'bar': ('baz', None, 1.0, 2)}])
    '["foo", {"bar": ["baz", null, 1.0, 2]}]'
    >>> print simplejson.dumps("\"foo\bar")
    "\"foo\bar"
    >>> print simplejson.dumps(u'\u1234')
    "\u1234"
    >>> print simplejson.dumps('\\')
    "\\"
    >>> print simplejson.dumps({"c": 0, "b": 0, "a": 0}, sort_keys=True)
    {"a": 0, "b": 0, "c": 0}
    >>> from StringIO import StringIO
    >>> io = StringIO()
    >>> simplejson.dump(['streaming API'], io)
    >>> io.getvalue()
    '["streaming API"]'

Compact encoding::

    >>> import simplejson
    >>> simplejson.dumps([1,2,3,{'4': 5, '6': 7}], separators=(',',':'))
    '[1,2,3,{"4":5,"6":7}]'

Pretty printing::

    >>> import simplejson
    >>> print simplejson.dumps({'4': 5, '6': 7}, sort_keys=True, indent=4)
    {
        "4": 5, 
        "6": 7
    }

Decoding JSON::
    
    >>> import simplejson
    >>> simplejson.loads('["foo", {"bar":["baz", null, 1.0, 2]}]')
    [u'foo', {u'bar': [u'baz', None, 1.0, 2]}]
    >>> simplejson.loads('"\\"foo\\bar"')
    u'"foo\x08ar'
    >>> from StringIO import StringIO
    >>> io = StringIO('["streaming API"]')
    >>> simplejson.load(io)
    [u'streaming API']

Specializing JSON object decoding::

    >>> import simplejson
    >>> def as_complex(dct):
    ...     if '__complex__' in dct:
    ...         return complex(dct['real'], dct['imag'])
    ...     return dct
    ... 
    >>> simplejson.loads('{"__complex__": true, "real": 1, "imag": 2}',
    ...     object_hook=as_complex)
    (1+2j)
    >>> import decimal
    >>> simplejson.loads('1.1', parse_float=decimal.Decimal)
    Decimal("1.1")

Extending JSONEncoder::
    
    >>> import simplejson
    >>> class ComplexEncoder(simplejson.JSONEncoder):
    ...     def default(self, obj):
    ...         if isinstance(obj, complex):
    ...             return [obj.real, obj.imag]
    ...         return simplejson.JSONEncoder.default(self, obj)
    ... 
    >>> dumps(2 + 1j, cls=ComplexEncoder)
    '[2.0, 1.0]'
    >>> ComplexEncoder().encode(2 + 1j)
    '[2.0, 1.0]'
    >>> list(ComplexEncoder().iterencode(2 + 1j))
    ['[', '2.0', ', ', '1.0', ']']
    

Using simplejson from the shell to validate and
pretty-print::
    
    $ echo '{"json":"obj"}' | python -msimplejson.tool
    {
        "json": "obj"
    }
    $ echo '{ 1.2:3.4}' | python -msimplejson.tool
    Expecting property name: line 1 column 2 (char 2)

Note that the JSON produced by this module's default settings
is a subset of YAML, so it may be used as a serializer for that as well.
"""
__version__ = '1.9.2'
__all__ = [
    'dump', 'dumps', 'load', 'loads',
    'JSONDecoder', 'JSONEncoder',
]

if __name__ == '__main__':
    import warnings
    warnings.warn('python -msimplejson is deprecated, use python -msiplejson.tool', DeprecationWarning)
    from django.utils.simplejson.decoder import JSONDecoder
    from django.utils.simplejson.encoder import JSONEncoder
else:
    from decoder import JSONDecoder
    from encoder import JSONEncoder

_default_encoder = JSONEncoder(
    skipkeys=False,
    ensure_ascii=True,
    check_circular=True,
    allow_nan=True,
    indent=None,
    separators=None,
    encoding='utf-8',
    default=None,
)

def dump(obj, fp, skipkeys=False, ensure_ascii=True, check_circular=True,
        allow_nan=True, cls=None, indent=None, separators=None,
        encoding='utf-8', default=None, **kw):
    """
    Serialize ``obj`` as a JSON formatted stream to ``fp`` (a
    ``.write()``-supporting file-like object).

    If ``skipkeys`` is ``True`` then ``dict`` keys that are not basic types
    (``str``, ``unicode``, ``int``, ``long``, ``float``, ``bool``, ``None``) 
    will be skipped instead of raising a ``TypeError``.

    If ``ensure_ascii`` is ``False``, then the some chunks written to ``fp``
    may be ``unicode`` instances, subject to normal Python ``str`` to
    ``unicode`` coercion rules. Unless ``fp.write()`` explicitly
    understands ``unicode`` (as in ``codecs.getwriter()``) this is likely
    to cause an error.

    If ``check_circular`` is ``False``, then the circular reference check
    for container types will be skipped and a circular reference will
    result in an ``OverflowError`` (or worse).

    If ``allow_nan`` is ``False``, then it will be a ``ValueError`` to
    serialize out of range ``float`` values (``nan``, ``inf``, ``-inf``)
    in strict compliance of the JSON specification, instead of using the
    JavaScript equivalents (``NaN``, ``Infinity``, ``-Infinity``).

    If ``indent`` is a non-negative integer, then JSON array elements and object
    members will be pretty-printed with that indent level. An indent level
    of 0 will only insert newlines. ``None`` is the most compact representation.

    If ``separators`` is an ``(item_separator, dict_separator)`` tuple
    then it will be used instead of the default ``(', ', ': ')`` separators.
    ``(',', ':')`` is the most compact JSON representation.

    ``encoding`` is the character encoding for str instances, default is UTF-8.

    ``default(obj)`` is a function that should return a serializable version
    of obj or raise TypeError. The default simply raises TypeError.

    To use a custom ``JSONEncoder`` subclass (e.g. one that overrides the
    ``.default()`` method to serialize additional types), specify it with
    the ``cls`` kwarg.
    """
    # cached encoder
    if (skipkeys is False and ensure_ascii is True and
        check_circular is True and allow_nan is True and
        cls is None and indent is None and separators is None and
        encoding == 'utf-8' and default is None and not kw):
        iterable = _default_encoder.iterencode(obj)
    else:
        if cls is None:
            cls = JSONEncoder
        iterable = cls(skipkeys=skipkeys, ensure_ascii=ensure_ascii,
            check_circular=check_circular, allow_nan=allow_nan, indent=indent,
            separators=separators, encoding=encoding,
            default=default, **kw).iterencode(obj)
    # could accelerate with writelines in some versions of Python, at
    # a debuggability cost
    for chunk in iterable:
        fp.write(chunk)


def dumps(obj, skipkeys=False, ensure_ascii=True, check_circular=True,
        allow_nan=True, cls=None, indent=None, separators=None,
        encoding='utf-8', default=None, **kw):
    """
    Serialize ``obj`` to a JSON formatted ``str``.

    If ``skipkeys`` is ``True`` then ``dict`` keys that are not basic types
    (``str``, ``unicode``, ``int``, ``long``, ``float``, ``bool``, ``None``) 
    will be skipped instead of raising a ``TypeError``.

    If ``ensure_ascii`` is ``False``, then the return value will be a
    ``unicode`` instance subject to normal Python ``str`` to ``unicode``
    coercion rules instead of being escaped to an ASCII ``str``.

    If ``check_circular`` is ``False``, then the circular reference check
    for container types will be skipped and a circular reference will
    result in an ``OverflowError`` (or worse).

    If ``allow_nan`` is ``False``, then it will be a ``ValueError`` to
    serialize out of range ``float`` values (``nan``, ``inf``, ``-inf``) in
    strict compliance of the JSON specification, instead of using the
    JavaScript equivalents (``NaN``, ``Infinity``, ``-Infinity``).

    If ``indent`` is a non-negative integer, then JSON array elements and
    object members will be pretty-printed with that indent level. An indent
    level of 0 will only insert newlines. ``None`` is the most compact
    representation.

    If ``separators`` is an ``(item_separator, dict_separator)`` tuple
    then it will be used instead of the default ``(', ', ': ')`` separators.
    ``(',', ':')`` is the most compact JSON representation.

    ``encoding`` is the character encoding for str instances, default is UTF-8.

    ``default(obj)`` is a function that should return a serializable version
    of obj or raise TypeError. The default simply raises TypeError.

    To use a custom ``JSONEncoder`` subclass (e.g. one that overrides the
    ``.default()`` method to serialize additional types), specify it with
    the ``cls`` kwarg.
    """
    # cached encoder
    if (skipkeys is False and ensure_ascii is True and
        check_circular is True and allow_nan is True and
        cls is None and indent is None and separators is None and
        encoding == 'utf-8' and default is None and not kw):
        return _default_encoder.encode(obj)
    if cls is None:
        cls = JSONEncoder
    return cls(
        skipkeys=skipkeys, ensure_ascii=ensure_ascii,
        check_circular=check_circular, allow_nan=allow_nan, indent=indent,
        separators=separators, encoding=encoding, default=default,
        **kw).encode(obj)


_default_decoder = JSONDecoder(encoding=None, object_hook=None)


def load(fp, encoding=None, cls=None, object_hook=None, parse_float=None,
        parse_int=None, parse_constant=None, **kw):
    """
    Deserialize ``fp`` (a ``.read()``-supporting file-like object containing
    a JSON document) to a Python object.

    If the contents of ``fp`` is encoded with an ASCII based encoding other
    than utf-8 (e.g. latin-1), then an appropriate ``encoding`` name must
    be specified. Encodings that are not ASCII based (such as UCS-2) are
    not allowed, and should be wrapped with
    ``codecs.getreader(fp)(encoding)``, or simply decoded to a ``unicode``
    object and passed to ``loads()``

    ``object_hook`` is an optional function that will be called with the
    result of any object literal decode (a ``dict``). The return value of
    ``object_hook`` will be used instead of the ``dict``. This feature
    can be used to implement custom decoders (e.g. JSON-RPC class hinting).
    
    To use a custom ``JSONDecoder`` subclass, specify it with the ``cls``
    kwarg.
    """
    return loads(fp.read(),
        encoding=encoding, cls=cls, object_hook=object_hook,
        parse_float=parse_float, parse_int=parse_int,
        parse_constant=parse_constant, **kw)


def loads(s, encoding=None, cls=None, object_hook=None, parse_float=None,
        parse_int=None, parse_constant=None, **kw):
    """
    Deserialize ``s`` (a ``str`` or ``unicode`` instance containing a JSON
    document) to a Python object.

    If ``s`` is a ``str`` instance and is encoded with an ASCII based encoding
    other than utf-8 (e.g. latin-1) then an appropriate ``encoding`` name
    must be specified. Encodings that are not ASCII based (such as UCS-2)
    are not allowed and should be decoded to ``unicode`` first.

    ``object_hook`` is an optional function that will be called with the
    result of any object literal decode (a ``dict``). The return value of
    ``object_hook`` will be used instead of the ``dict``. This feature
    can be used to implement custom decoders (e.g. JSON-RPC class hinting).

    ``parse_float``, if specified, will be called with the string
    of every JSON float to be decoded. By default this is equivalent to
    float(num_str). This can be used to use another datatype or parser
    for JSON floats (e.g. decimal.Decimal).

    ``parse_int``, if specified, will be called with the string
    of every JSON int to be decoded. By default this is equivalent to
    int(num_str). This can be used to use another datatype or parser
    for JSON integers (e.g. float).

    ``parse_constant``, if specified, will be called with one of the
    following strings: -Infinity, Infinity, NaN, null, true, false.
    This can be used to raise an exception if invalid JSON numbers
    are encountered.

    To use a custom ``JSONDecoder`` subclass, specify it with the ``cls``
    kwarg.
    """
    if (cls is None and encoding is None and object_hook is None and
            parse_int is None and parse_float is None and
            parse_constant is None and not kw):
        return _default_decoder.decode(s)
    if cls is None:
        cls = JSONDecoder
    if object_hook is not None:
        kw['object_hook'] = object_hook
    if parse_float is not None:
        kw['parse_float'] = parse_float
    if parse_int is not None:
        kw['parse_int'] = parse_int
    if parse_constant is not None:
        kw['parse_constant'] = parse_constant
    return cls(encoding=encoding, **kw).decode(s)


#
# Compatibility cruft from other libraries
#


def decode(s):
    """
    demjson, python-cjson API compatibility hook. Use loads(s) instead.
    """
    import warnings
    warnings.warn("simplejson.loads(s) should be used instead of decode(s)",
        DeprecationWarning)
    return loads(s)


def encode(obj):
    """
    demjson, python-cjson compatibility hook. Use dumps(s) instead.
    """
    import warnings
    warnings.warn("simplejson.dumps(s) should be used instead of encode(s)",
        DeprecationWarning)
    return dumps(obj)


def read(s):
    """
    jsonlib, JsonUtils, python-json, json-py API compatibility hook.
    Use loads(s) instead.
    """
    import warnings
    warnings.warn("simplejson.loads(s) should be used instead of read(s)",
        DeprecationWarning)
    return loads(s)


def write(obj):
    """
    jsonlib, JsonUtils, python-json, json-py API compatibility hook.
    Use dumps(s) instead.
    """
    import warnings
    warnings.warn("simplejson.dumps(s) should be used instead of write(s)",
        DeprecationWarning)
    return dumps(obj)


if __name__ == '__main__':
    import simplejson.tool
    simplejson.tool.main()
