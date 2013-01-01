===================
Porting to Python 3
===================

Django 1.5 is the first version of Django to support Python 3. The same code
runs both on Python 2 (≥ 2.6.5) and Python 3 (≥ 3.2), thanks to the six_
compatibility layer.

.. _six: http://packages.python.org/six/

This document is primarily targeted at authors of pluggable application
who want to support both Python 2 and 3. It also describes guidelines that
apply to Django's code.

Philosophy
==========

This document assumes that you are familiar with the changes between Python 2
and Python 3. If you aren't, read `Python's official porting guide`_ first.
Refreshing your knowledge of unicode handling on Python 2 and 3 will help; the
`Pragmatic Unicode`_ presentation is a good resource.

Django uses the *Python 2/3 Compatible Source* strategy. Of course, you're
free to chose another strategy for your own code, especially if you don't need
to stay compatible with Python 2. But authors of pluggable applications are
encouraged to use the same porting strategy as Django itself.

Writing compatible code is much easier if you target Python ≥ 2.6. Django 1.5
introduces compatibility tools such as :mod:`django.utils.six`. For
convenience, forwards-compatible aliases were introduced in Django 1.4.2. If
your application takes advantage of these tools, it will require Django ≥
1.4.2.

Obviously, writing compatible source code adds some overhead, and that can
cause frustration. Django's developers have found that attempting to write
Python 3 code that's compatible with Python 2 is much more rewarding than the
opposite. Not only does that make your code more future-proof, but Python 3's
advantages (like the saner string handling) start shining quickly. Dealing
with Python 2 becomes a backwards compatibility requirement, and we as
developers are used to dealing with such constraints.

Porting tools provided by Django are inspired by this philosophy, and it's
reflected throughout this guide.

.. _Python's official porting guide: http://docs.python.org/py3k/howto/pyporting.html
.. _Pragmatic Unicode: http://nedbatchelder.com/text/unipain.html

Porting tips
============

Unicode literals
----------------

This step consists in:

- Adding ``from __future__ import unicode_literals`` at the top of your Python
  modules -- it's best to put it in each and every module, otherwise you'll
  keep checking the top of your files to see which mode is in effect;
- Removing the ``u`` prefix before unicode strings;
- Adding a ``b`` prefix before bytestrings.

Performing these changes systematically guarantees backwards compatibility.

However, Django applications generally don't need bytestrings, since Django
only exposes unicode interfaces to the programmer. Python 3 discourages using
bytestrings, except for binary data or byte-oriented interfaces. Python 2
makes bytestrings and unicode strings effectively interchangeable, as long as
they only contain ASCII data. Take advantage of this to use unicode strings
wherever possible and avoid the ``b`` prefixes.

.. note::

    Python 2's ``u`` prefix is a syntax error in Python 3.2 but it will be
    allowed again in Python 3.3 thanks to :pep:`414`. Thus, this
    transformation is optional if you target Python ≥ 3.3. It's still
    recommended, per the "write Python 3 code" philosophy.

String handling
---------------

Python 2's :func:`unicode` type was renamed :func:`str` in Python 3,
:func:`str` was renamed ``bytes()``, and :func:`basestring` disappeared.
six_ provides :ref:`tools <string-handling-with-six>` to deal with these
changes.

Django also contains several string related classes and functions in the
:mod:`django.utils.encoding` and :mod:`django.utils.safestring` modules. Their
names used the words ``str``, which doesn't mean the same thing in Python 2
and Python 3, and ``unicode``, which doesn't exist in Python 3. In order to
avoid ambiguity and confusion these concepts were renamed ``bytes`` and
``text``.

Here are the name changes in :mod:`django.utils.encoding`:

==================  ==================
Old name            New name
==================  ==================
``smart_str``       ``smart_bytes``
``smart_unicode``   ``smart_text``
``force_unicode``   ``force_text``
==================  ==================

For backwards compatibility, the old names still work on Python 2. Under
Python 3, ``smart_str`` is an alias for ``smart_text``.

For forwards compatibility, the new names work as of Django 1.4.2.

.. note::

    :mod:`django.utils.encoding` was deeply refactored in Django 1.5 to
    provide a more consistent API. Check its documentation for more
    information.

:mod:`django.utils.safestring` is mostly used via the
:func:`~django.utils.safestring.mark_safe` and
:func:`~django.utils.safestring.mark_for_escaping` functions, which didn't
change. In case you're using the internals, here are the name changes:

==================  ==================
Old name            New name
==================  ==================
``EscapeString``    ``EscapeBytes``
``EscapeUnicode``   ``EscapeText``
``SafeString``      ``SafeBytes``
``SafeUnicode``     ``SafeText``
==================  ==================

For backwards compatibility, the old names still work on Python 2. Under
Python 3, ``EscapeString`` and ``SafeString`` are aliases for ``EscapeText``
and ``SafeText`` respectively.

For forwards compatibility, the new names work as of Django 1.4.2.

:meth:`~object.__str__` and :meth:`~object.__unicode__` methods
---------------------------------------------------------------

In Python 2, the object model specifies :meth:`~object.__str__` and
:meth:`~object.__unicode__` methods. If these methods exist, they must return
``str`` (bytes) and ``unicode`` (text) respectively.

The ``print`` statement and the :func:`str` built-in call
:meth:`~object.__str__` to determine the human-readable representation of an
object. The :func:`unicode` built-in calls :meth:`~object.__unicode__` if it
exists, and otherwise falls back to :meth:`~object.__str__` and decodes the
result with the system encoding. Conversely, the
:class:`~django.db.models.Model` base class automatically derives
:meth:`~object.__str__` from :meth:`~object.__unicode__` by encoding to UTF-8.

In Python 3, there's simply :meth:`~object.__str__`, which must return ``str``
(text).

(It is also possible to define ``__bytes__()``, but Django application have
little use for that method, because they hardly ever deal with
``bytes``.)

Django provides a simple way to define :meth:`~object.__str__` and
:meth:`~object.__unicode__` methods that work on Python 2 and 3: you must
define a :meth:`~object.__str__` method returning text and to apply the
:func:`~django.utils.encoding.python_2_unicode_compatible` decorator.

On Python 3, the decorator is a no-op. On Python 2, it defines appropriate
:meth:`~object.__unicode__` and :meth:`~object.__str__` methods (replacing the
original :meth:`~object.__str__` method in the process). Here's an example::

    from __future__ import unicode_literals
    from django.utils.encoding import python_2_unicode_compatible

    @python_2_unicode_compatible
    class MyClass(object):
        def __str__(self):
            return "Instance of my class"

This technique is the best match for Django's porting philosophy.

For forwards compatibility, this decorator is available as of Django 1.4.2.

Finally, note that :meth:`~object.__repr__` must return a ``str`` on all
versions of Python.

:class:`dict` and :class:`dict`-like classes
--------------------------------------------

:meth:`dict.keys`, :meth:`dict.items` and :meth:`dict.values` return lists in
Python 2 and iterators in Python 3. :class:`~django.http.QueryDict` and the
:class:`dict`-like classes defined in :mod:`django.utils.datastructures`
behave likewise in Python 3.

six_ provides compatibility functions to work around this change:
:func:`~six.iterkeys`, :func:`~six.iteritems`, and :func:`~six.itervalues`.
Django's bundled version adds :func:`~django.utils.six.iterlists` for
``django.utils.datastructures.MultiValueDict`` and its subclasses.

:class:`~django.http.HttpRequest` and :class:`~django.http.HttpResponse` objects
--------------------------------------------------------------------------------

According to :pep:`3333`:

- headers are always ``str`` objects,
- input and output streams are always ``bytes`` objects.

Specifically, :attr:`HttpResponse.content <django.http.HttpResponse.content>`
contains ``bytes``, which may become an issue if you compare it with a
``str`` in your tests. The preferred solution is to rely on
:meth:`~django.test.TestCase.assertContains` and
:meth:`~django.test.TestCase.assertNotContains`. These methods accept a
response and a unicode string as arguments.

Coding guidelines
=================

The following guidelines are enforced in Django's source code. They're also
recommended for third-party application who follow the same porting strategy.

Syntax requirements
-------------------

Unicode
~~~~~~~

In Python 3, all strings are considered Unicode by default. The ``unicode``
type from Python 2 is called ``str`` in Python 3, and ``str`` becomes
``bytes``.

You mustn't use the ``u`` prefix before a unicode string literal because it's
a syntax error in Python 3.2. You must prefix byte strings with ``b``.

In order to enable the same behavior in Python 2, every module must import
``unicode_literals`` from ``__future__``::

    from __future__ import unicode_literals

    my_string = "This is an unicode literal"
    my_bytestring = b"This is a bytestring"

If you need a byte string literal under Python 2 and a unicode string literal
under Python 3, use the :func:`str` builtin::

    str('my string')

In Python 3, there aren't any automatic conversions between ``str`` and
``bytes``, and the :mod:`codecs` module became more strict. :meth:`str.decode`
always returns ``bytes``, and ``bytes.decode`` always returns ``str``. As a
consequence, the following pattern is sometimes necessary::

    value = value.encode('ascii', 'ignore').decode('ascii')

Be cautious if you have to `index bytestrings`_.

.. _index bytestrings: http://docs.python.org/py3k/howto/pyporting.html#bytes-literals

Exceptions
~~~~~~~~~~

When you capture exceptions, use the ``as`` keyword::

    try:
        ...
    except MyException as exc:
        ...

This older syntax was removed in Python 3::

    try:
        ...
    except MyException, exc:    # Don't do that!
        ...

The syntax to reraise an exception with a different traceback also changed.
Use :func:`six.reraise`.

Magic methods
-------------

Use the patterns below to handle magic methods renamed in Python 3.

Iterators
~~~~~~~~~

::

    class MyIterator(six.Iterator):
        def __iter__(self):
            return self             # implement some logic here

        def __next__(self):
            raise StopIteration     # implement some logic here

Boolean evaluation
~~~~~~~~~~~~~~~~~~

::

    class MyBoolean(object):

        def __bool__(self):
            return True             # implement some logic here

        def __nonzero__(self):      # Python 2 compatibility
            return type(self).__bool__(self)

Division
~~~~~~~~

::

    class MyDivisible(object):

        def __truediv__(self, other):
            return self / other     # implement some logic here

        def __div__(self, other):   # Python 2 compatibility
            return type(self).__truediv__(self, other)

        def __itruediv__(self, other):
            return self // other    # implement some logic here

        def __idiv__(self, other):  # Python 2 compatibility
            return type(self).__itruediv__(self, other)

.. module: django.utils.six

Writing compatible code with six
--------------------------------

six_ is the canonical compatibility library for supporting Python 2 and 3 in
a single codebase. Read its documentation!

:mod:`six` is bundled with Django as of version 1.4.2. You can import it as
:mod:`django.utils.six`.

Here are the most common changes required to write compatible code.

.. _string-handling-with-six:

String handling
~~~~~~~~~~~~~~~

The ``basestring`` and ``unicode`` types were removed in Python 3, and the
meaning of ``str`` changed. To test these types, use the following idioms::

    isinstance(myvalue, six.string_types)       # replacement for basestring
    isinstance(myvalue, six.text_type)          # replacement for unicode
    isinstance(myvalue, bytes)                  # replacement for str

Python ≥ 2.6 provides ``bytes`` as an alias for ``str``, so you don't need
:data:`six.binary_type`.

``long``
~~~~~~~~

The ``long`` type no longer exists in Python 3. ``1L`` is a syntax error. Use
:data:`six.integer_types` check if a value is an integer or a long::

    isinstance(myvalue, six.integer_types)      # replacement for (int, long)

``xrange``
~~~~~~~~~~

Import ``six.moves.xrange`` wherever you use ``xrange``.

Moved modules
~~~~~~~~~~~~~

Some modules were renamed in Python 3. The :mod:`django.utils.six.moves
<six.moves>` module provides a compatible location to import them.

The ``urllib``, ``urllib2`` and ``urlparse`` modules were reworked in depth
and :mod:`django.utils.six.moves <six.moves>` doesn't handle them. Django
explicitly tries both locations, as follows::

    try:
        from urllib.parse import urlparse, urlunparse
    except ImportError:     # Python 2
        from urlparse import urlparse, urlunparse

PY3
~~~

If you need different code in Python 2 and Python 3, check :data:`six.PY3`::

    if six.PY3:
        # do stuff Python 3-wise
    else:
        # do stuff Python 2-wise

This is a last resort solution when :mod:`six` doesn't provide an appropriate
function.

.. module:: django.utils.six

Customizations of six
---------------------

The version of six bundled with Django includes one extra function:

.. function:: iterlists(MultiValueDict)

    Returns an iterator over the lists of values of a ``MultiValueDict``. This
    replaces ``iterlists()`` on Python 2 and ``lists()`` on Python 3.

.. function:: assertRaisesRegex(testcase, *args, **kwargs)

    This replaces ``testcase.assertRaisesRegexp`` on Python 2, and
    ``testcase.assertRaisesRegex`` on Python 3. ``assertRaisesRegexp`` still
    exists in current Python3 versions, but issues a warning.


In addition to six' defaults moves, Django's version provides ``thread`` as
``_thread`` and ``dummy_thread`` as ``_dummy_thread``.
