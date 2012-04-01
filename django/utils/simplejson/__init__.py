r"""JSON (JavaScript Object Notation) <http://json.org> is a subset of
JavaScript syntax (ECMA-262 3rd edition) used as a lightweight data
interchange format.

:mod:`simplejson` exposes an API familiar to users of the standard library
:mod:`marshal` and :mod:`pickle` modules. It is the externally maintained
version of the :mod:`json` library contained in Python 2.6, but maintains
compatibility with Python 2.4 and Python 2.5 and (currently) has
significant performance advantages, even without using the optional C
extension for speedups.

Encoding basic Python object hierarchies::

    >>> import simplejson as json
    >>> json.dumps(['foo', {'bar': ('baz', None, 1.0, 2)}])
    '["foo", {"bar": ["baz", null, 1.0, 2]}]'
    >>> print json.dumps("\"foo\bar")
    "\"foo\bar"
    >>> print json.dumps(u'\u1234')
    "\u1234"
    >>> print json.dumps('\\')
    "\\"
    >>> print json.dumps({"c": 0, "b": 0, "a": 0}, sort_keys=True)
    {"a": 0, "b": 0, "c": 0}
    >>> from StringIO import StringIO
    >>> io = StringIO()
    >>> json.dump(['streaming API'], io)
    >>> io.getvalue()
    '["streaming API"]'

Compact encoding::

    >>> import simplejson as json
    >>> json.dumps([1,2,3,{'4': 5, '6': 7}], separators=(',',':'))
    '[1,2,3,{"4":5,"6":7}]'

Pretty printing::

    >>> import simplejson as json
    >>> s = json.dumps({'4': 5, '6': 7}, sort_keys=True, indent=4)
    >>> print '\n'.join([l.rstrip() for l in  s.splitlines()])
    {
        "4": 5,
        "6": 7
    }

Decoding JSON::

    >>> import simplejson as json
    >>> obj = [u'foo', {u'bar': [u'baz', None, 1.0, 2]}]
    >>> json.loads('["foo", {"bar":["baz", null, 1.0, 2]}]') == obj
    True
    >>> json.loads('"\\"foo\\bar"') == u'"foo\x08ar'
    True
    >>> from StringIO import StringIO
    >>> io = StringIO('["streaming API"]')
    >>> json.load(io)[0] == 'streaming API'
    True

Specializing JSON object decoding::

    >>> import simplejson as json
    >>> def as_complex(dct):
    ...     if '__complex__' in dct:
    ...         return complex(dct['real'], dct['imag'])
    ...     return dct
    ...
    >>> json.loads('{"__complex__": true, "real": 1, "imag": 2}',
    ...     object_hook=as_complex)
    (1+2j)
    >>> import decimal
    >>> json.loads('1.1', parse_float=decimal.Decimal) == decimal.Decimal('1.1')
    True

Specializing JSON object encoding::

    >>> import simplejson as json
    >>> def encode_complex(obj):
    ...     if isinstance(obj, complex):
    ...         return [obj.real, obj.imag]
    ...     raise TypeError("%r is not JSON serializable" % (o,))
    ...
    >>> json.dumps(2 + 1j, default=encode_complex)
    '[2.0, 1.0]'
    >>> json.JSONEncoder(default=encode_complex).encode(2 + 1j)
    '[2.0, 1.0]'
    >>> ''.join(json.JSONEncoder(default=encode_complex).iterencode(2 + 1j))
    '[2.0, 1.0]'


Using simplejson.tool from the shell to validate and pretty-print::

    $ echo '{"json":"obj"}' | python -msimplejson.tool
    {
        "json": "obj"
    }
    $ echo '{ 1.2:3.4}' | python -msimplejson.tool
    Expecting property name: line 1 column 2 (char 2)
"""

# Django modification: try to use the system version first, providing it's
# either of a later version of has the C speedups in place. Otherwise, fall
# back to our local copy.

__version__ = '2.0.7'

use_system_version = False
try:
    # The system-installed version has priority providing it is either not an
    # earlier version or it contains the C speedups.
    import simplejson
    if (simplejson.__version__.split('.') >= __version__.split('.') or
            hasattr(simplejson, '_speedups')):
        from simplejson import *
        use_system_version = True
        # Make sure we copy over the version. See #17071
        __version__ = simplejson.__version__
except ImportError:
    pass

if not use_system_version:
    try:
        from json import *      # Python 2.6 preferred over local copy.

        # There is a "json" package around that is not Python's "json", so we
        # check for something that is only in the namespace of the version we
        # want.
        JSONDecoder

        use_system_version = True
        # Make sure we copy over the version. See #17071
        from json import __version__ as json_version
        __version__ = json_version
    except (ImportError, NameError):
        pass

# If all else fails, we have a bundled version that can be used.
if not use_system_version:
    __all__ = [
        'dump', 'dumps', 'load', 'loads',
        'JSONDecoder', 'JSONEncoder',
    ]

    from django.utils.simplejson.decoder import JSONDecoder
    from django.utils.simplejson.encoder import JSONEncoder

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
        """Serialize ``obj`` as a JSON formatted stream to ``fp`` (a
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
        """Serialize ``obj`` to a JSON formatted ``str``.

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
        """Deserialize ``fp`` (a ``.read()``-supporting file-like object containing
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
        """Deserialize ``s`` (a ``str`` or ``unicode`` instance containing a JSON
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
