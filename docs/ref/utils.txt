============
Django Utils
============

.. module:: django.utils
   :synopsis: Django's built-in utilities.

This document covers all stable modules in ``django.utils``. Most of the
modules in ``django.utils`` are designed for internal use and only the
following parts can be considered stable and thus backwards compatible as per
the :ref:`internal release deprecation policy <internal-release-deprecation-policy>`.

``django.utils.cache``
======================

.. module:: django.utils.cache
   :synopsis: Helper functions for controlling caching.

This module contains helper functions for controlling caching. It does so by
managing the ``Vary`` header of responses. It includes functions to patch the
header of response objects directly and decorators that change functions to do
that header-patching themselves.

For information on the ``Vary`` header, see :rfc:`2616#section-14.44` section
14.44.

Essentially, the ``Vary`` HTTP header defines which headers a cache should take
into account when building its cache key. Requests with the same path but
different header content for headers named in ``Vary`` need to get different
cache keys to prevent delivery of wrong content.

For example, :doc:`internationalization </topics/i18n/index>` middleware would need
to distinguish caches by the ``Accept-language`` header.

.. function:: patch_cache_control(response, **kwargs)

    This function patches the ``Cache-Control`` header by adding all keyword
    arguments to it. The transformation is as follows:

    * All keyword parameter names are turned to lowercase, and underscores
      are converted to hyphens.
    * If the value of a parameter is ``True`` (exactly ``True``, not just a
      true value), only the parameter name is added to the header.
    * All other parameters are added with their value, after applying
      ``str()`` to it.

.. function:: get_max_age(response)

    Returns the max-age from the response Cache-Control header as an integer
    (or ``None`` if it wasn't found or wasn't an integer).

.. function:: patch_response_headers(response, cache_timeout=None)

    Adds some useful headers to the given ``HttpResponse`` object:

    * ``ETag``
    * ``Last-Modified``
    * ``Expires``
    * ``Cache-Control``

    Each header is only added if it isn't already set.

    ``cache_timeout`` is in seconds. The :setting:`CACHE_MIDDLEWARE_SECONDS`
    setting is used by default.

.. function:: add_never_cache_headers(response)

    Adds headers to a response to indicate that a page should never be cached.

.. function:: patch_vary_headers(response, newheaders)

    Adds (or updates) the ``Vary`` header in the given ``HttpResponse`` object.
    ``newheaders`` is a list of header names that should be in ``Vary``.
    Existing headers in ``Vary`` aren't removed.

.. function:: get_cache_key(request, key_prefix=None)

    Returns a cache key based on the request path. It can be used in the
    request phase because it pulls the list of headers to take into account
    from the global path registry and uses those to build a cache key to
    check against.

    If there is no headerlist stored, the page needs to be rebuilt, so this
    function returns ``None``.

.. function:: learn_cache_key(request, response, cache_timeout=None, key_prefix=None)

    Learns what headers to take into account for some request path from the
    response object. It stores those headers in a global path registry so that
    later access to that path will know what headers to take into account
    without building the response object itself. The headers are named in
    the ``Vary`` header of the response, but we want to prevent response
    generation.

    The list of headers to use for cache key generation is stored in the same
    cache as the pages themselves. If the cache ages some data out of the
    cache, this just means that we have to build the response once to get at
    the Vary header and so at the list of headers to use for the cache key.

``django.utils.datastructures``
===============================

.. module:: django.utils.datastructures
   :synopsis: Data structures that aren't in Python's standard library.

.. class:: SortedDict

    The :class:`django.utils.datastructures.SortedDict` class is a dictionary
    that keeps its keys in the order in which they're inserted.
    ``SortedDict`` adds two additional methods to the standard Python ``dict``
    class:

    .. method:: insert(index, key, value)

        .. deprecated:: 1.5

        Inserts the key, value pair before the item with the given index.

    .. method:: value_for_index(index)

        .. deprecated:: 1.5

        Returns the value of the item at the given zero-based index.

Creating a new SortedDict
-------------------------

Creating a new ``SortedDict`` must be done in a way where ordering is
guaranteed. For example::

    SortedDict({'b': 1, 'a': 2, 'c': 3})

will not work. Passing in a basic Python ``dict`` could produce unreliable
results. Instead do::

    SortedDict([('b', 1), ('a', 2), ('c', 3)])

``django.utils.dateparse``
==========================

.. versionadded:: 1.4

.. module:: django.utils.dateparse
   :synopsis: Functions to parse datetime objects.

The functions defined in this module share the following properties:

- They raise :exc:`~exceptions.ValueError` if their input is well formatted but
  isn't a valid date or time.
- They return ``None`` if it isn't well formatted at all.
- They accept up to picosecond resolution in input, but they truncate it to
  microseconds, since that's what Python supports.

.. function:: parse_date(value)

    Parses a string and returns a :class:`datetime.date`.

.. function:: parse_time(value)

    Parses a string and returns a :class:`datetime.time`.

    UTC offsets aren't supported; if ``value`` describes one, the result is
    ``None``.

.. function:: parse_datetime(value)

    Parses a string and returns a :class:`datetime.datetime`.

    UTC offsets are supported; if ``value`` describes one, the result's
    ``tzinfo`` attribute is a :class:`~django.utils.tzinfo.FixedOffset`
    instance.

``django.utils.decorators``
===========================

.. module:: django.utils.decorators
    :synopsis: Functions that help with creating decorators for views.

.. function:: method_decorator(decorator)

    Converts a function decorator into a method decorator. See :ref:`decorating
    class based views<decorating-class-based-views>` for example usage.

.. function:: decorator_from_middleware(middleware_class)

    Given a middleware class, returns a view decorator. This lets you use
    middleware functionality on a per-view basis. The middleware is created
    with no params passed.

.. function:: decorator_from_middleware_with_args(middleware_class)

    Like ``decorator_from_middleware``, but returns a function
    that accepts the arguments to be passed to the middleware_class.
    For example, the :func:`~django.views.decorators.cache.cache_page`
    decorator is created from the ``CacheMiddleware`` like this::

         cache_page = decorator_from_middleware_with_args(CacheMiddleware)

         @cache_page(3600)
         def my_view(request):
             pass

``django.utils.encoding``
=========================

.. module:: django.utils.encoding
   :synopsis: A series of helper classes and function to manage character encoding.

.. class:: StrAndUnicode

    A class that derives ``__str__`` from ``__unicode__``.

    On Python 2, ``__str__`` returns the output of ``__unicode__`` encoded as
    a UTF-8 bytestring. On Python 3, ``__str__`` returns the output of
    ``__unicode__``.

    Useful as a mix-in. If you support Python 2 and 3 with a single code base,
    you can inherit this mix-in and just define ``__unicode__``.

.. function:: python_2_unicode_compatible

    A decorator that defines ``__unicode__`` and ``__str__`` methods under
    Python 2. Under Python 3 it does nothing.

    To support Python 2 and 3 with a single code base, define a ``__str__``
    method returning text and apply this decorator to the class.

.. function:: smart_text(s, encoding='utf-8', strings_only=False, errors='strict')

    .. versionadded:: 1.5

    Returns a text object representing ``s`` -- ``unicode`` on Python 2 and
    ``str`` on Python 3. Treats bytestrings using the ``encoding`` codec.

    If ``strings_only`` is ``True``, don't convert (some) non-string-like
    objects.

.. function:: smart_unicode(s, encoding='utf-8', strings_only=False, errors='strict')

    Historical name of :func:`smart_text`. Only available under Python 2.

.. function:: is_protected_type(obj)

    Determine if the object instance is of a protected type.

    Objects of protected types are preserved as-is when passed to
    ``force_text(strings_only=True)``.

.. function:: force_text(s, encoding='utf-8', strings_only=False, errors='strict')

    .. versionadded:: 1.5

    Similar to ``smart_text``, except that lazy instances are resolved to
    strings, rather than kept as lazy objects.

    If ``strings_only`` is ``True``, don't convert (some) non-string-like
    objects.

.. function:: force_unicode(s, encoding='utf-8', strings_only=False, errors='strict')

    Historical name of :func:`force_text`. Only available under Python 2.

.. function:: smart_bytes(s, encoding='utf-8', strings_only=False, errors='strict')

    .. versionadded:: 1.5

    Returns a bytestring version of ``s``, encoded as specified in
    ``encoding``.

    If ``strings_only`` is ``True``, don't convert (some) non-string-like
    objects.

.. function:: force_bytes(s, encoding='utf-8', strings_only=False, errors='strict')

    .. versionadded:: 1.5

    Similar to ``smart_bytes``, except that lazy instances are resolved to
    bytestrings, rather than kept as lazy objects.

    If ``strings_only`` is ``True``, don't convert (some) non-string-like
    objects.

.. function:: smart_str(s, encoding='utf-8', strings_only=False, errors='strict')

    Alias of :func:`smart_bytes` on Python 2 and :func:`smart_text` on Python
    3. This function returns a ``str`` or a lazy string.

    For instance, this is  suitable for writing to :data:`sys.stdout` on
    Python 2 and 3.

.. function:: force_str(s, encoding='utf-8', strings_only=False, errors='strict')

    Alias of :func:`force_bytes` on Python 2 and :func:`force_text` on Python
    3. This function always returns a ``str``.

.. function:: iri_to_uri(iri)

    Convert an Internationalized Resource Identifier (IRI) portion to a URI
    portion that is suitable for inclusion in a URL.

    This is the algorithm from section 3.1 of :rfc:`3987#section-3.1`. However,
    since we are assuming input is either UTF-8 or unicode already, we can
    simplify things a little from the full method.

    Returns an ASCII string containing the encoded result.

.. function:: filepath_to_uri(path)

    Convert a file system path to a URI portion that is suitable for inclusion
    in a URL. The path is assumed to be either UTF-8 or unicode.

    This method will encode certain characters that would normally be
    recognized as special characters for URIs.  Note that this method does not
    encode the ' character, as it is a valid character within URIs. See
    ``encodeURIComponent()`` JavaScript function for more details.

    Returns an ASCII string containing the encoded result.

``django.utils.feedgenerator``
==============================

.. module:: django.utils.feedgenerator
   :synopsis: Syndication feed generation library -- used for generating RSS, etc.

Sample usage::

    >>> from django.utils import feedgenerator
    >>> feed = feedgenerator.Rss201rev2Feed(
    ...     title=u"Poynter E-Media Tidbits",
    ...     link=u"http://www.poynter.org/column.asp?id=31",
    ...     description=u"A group Weblog by the sharpest minds in online media/journalism/publishing.",
    ...     language=u"en",
    ... )
    >>> feed.add_item(
    ...     title="Hello",
    ...     link=u"http://www.holovaty.com/test/",
    ...     description="Testing."
    ... )
    >>> with open('test.rss', 'w') as fp:
    ...     feed.write(fp, 'utf-8')

For simplifying the selection of a generator use ``feedgenerator.DefaultFeed``
which is currently ``Rss201rev2Feed``

For definitions of the different versions of RSS, see:
http://web.archive.org/web/20110718035220/http://diveintomark.org/archives/2004/02/04/incompatible-rss

.. function:: get_tag_uri(url, date)

    Creates a TagURI.

    See http://web.archive.org/web/20110514113830/http://diveintomark.org/archives/2004/05/28/howto-atom-id

SyndicationFeed
---------------

.. class:: SyndicationFeed

    Base class for all syndication feeds. Subclasses should provide write().

    .. method:: __init__(title, link, description, [language=None, author_email=None, author_name=None, author_link=None, subtitle=None, categories=None, feed_url=None, feed_copyright=None, feed_guid=None, ttl=None, **kwargs])

        Initialize the feed with the given dictionary of metadata, which applies
        to the entire feed.

        Any extra keyword arguments you pass to ``__init__`` will be stored in
        ``self.feed``.

        All parameters should be Unicode objects, except ``categories``, which
        should be a sequence of Unicode objects.

    .. method:: add_item(title, link, description, [author_email=None, author_name=None, author_link=None, pubdate=None, comments=None, unique_id=None, enclosure=None, categories=(), item_copyright=None, ttl=None, **kwargs])

        Adds an item to the feed. All args are expected to be Python ``unicode``
        objects except ``pubdate``, which is a ``datetime.datetime`` object, and
        ``enclosure``, which is an instance of the ``Enclosure`` class.

    .. method:: num_items()

    .. method:: root_attributes()

        Return extra attributes to place on the root (i.e. feed/channel)
        element. Called from ``write()``.

    .. method:: add_root_elements(handler)

        Add elements in the root (i.e. feed/channel) element.
        Called from ``write()``.

    .. method:: item_attributes(item)

        Return extra attributes to place on each item (i.e. item/entry)
        element.

    .. method:: add_item_elements(handler, item)

        Add elements on each item (i.e. item/entry) element.

    .. method:: write(outfile, encoding)

        Outputs the feed in the given encoding to ``outfile``, which is a
        file-like object. Subclasses should override this.

    .. method:: writeString(encoding)

        Returns the feed in the given encoding as a string.

    .. method:: latest_post_date()

        Returns the latest item's ``pubdate``. If none of them have a
        ``pubdate``, this returns the current date/time.

Enclosure
---------

.. class:: Enclosure

    Represents an RSS enclosure

RssFeed
-------

.. class:: RssFeed(SyndicationFeed)

Rss201rev2Feed
--------------

.. class:: Rss201rev2Feed(RssFeed)

    Spec: http://cyber.law.harvard.edu/rss/rss.html

RssUserland091Feed
------------------

.. class:: RssUserland091Feed(RssFeed)

    Spec: http://backend.userland.com/rss091

Atom1Feed
---------

.. class:: Atom1Feed(SyndicationFeed)

    Spec: http://www.atomenabled.org/developers/syndication/atom-format-spec.php

``django.utils.functional``
===========================

.. module:: django.utils.functional
    :synopsis: Functional programming tools.

.. function:: allow_lazy(func, *resultclasses)

    Django offers many utility functions (particularly in ``django.utils``) that
    take a string as their first argument and do something to that string. These
    functions are used by template filters as well as directly in other code.

    If you write your own similar functions and deal with translations, you'll
    face the problem of what to do when the first argument is a lazy translation
    object. You don't want to convert it to a string immediately, because you might
    be using this function outside of a view (and hence the current thread's locale
    setting will not be correct).

    For cases like this, use the ``django.utils.functional.allow_lazy()``
    decorator. It modifies the function so that *if* it's called with a lazy
    translation as the first argument, the function evaluation is delayed until it
    needs to be converted to a string.

    For example::

        from django.utils.functional import allow_lazy

        def fancy_utility_function(s, ...):
            # Do some conversion on string 's'
            ...
        fancy_utility_function = allow_lazy(fancy_utility_function, unicode)

    The ``allow_lazy()`` decorator takes, in addition to the function to decorate,
    a number of extra arguments (``*args``) specifying the type(s) that the
    original function can return. Usually, it's enough to include ``unicode`` here
    and ensure that your function returns only Unicode strings.

    Using this decorator means you can write your function and assume that the
    input is a proper string, then add support for lazy translation objects at the
    end.

``django.utils.html``
=====================

.. module:: django.utils.html
   :synopsis: HTML helper functions

Usually you should build up HTML using Django's templates to make use of its
autoescape mechanism, using the utilities in :mod:`django.utils.safestring`
where appropriate. This module provides some additional low level utilitiesfor
escaping HTML.

.. function:: escape(text)

    Returns the given text with ampersands, quotes and angle brackets encoded
    for use in HTML. The input is first passed through
    :func:`~django.utils.encoding.force_text` and the output has
    :func:`~django.utils.safestring.mark_safe` applied.

.. function:: conditional_escape(text)

    Similar to ``escape()``, except that it doesn't operate on pre-escaped strings,
    so it will not double escape.

.. function:: format_html(format_string, *args, **kwargs)

    This is similar to `str.format`_, except that it is appropriate for
    building up HTML fragments. All args and kwargs are passed through
    :func:`conditional_escape` before being passed to ``str.format``.

    For the case of building up small HTML fragments, this function is to be
    preferred over string interpolation using ``%`` or ``str.format`` directly,
    because it applies escaping to all arguments - just like the Template system
    applies escaping by default.

    So, instead of writing:

    .. code-block:: python

        mark_safe(u"%s <b>%s</b> %s" % (some_html,
                                        escape(some_text),
                                        escape(some_other_text),
                                        ))

    you should instead use:

    .. code-block:: python

        format_html(u"%{0} <b>{1}</b> {2}",
                    mark_safe(some_html), some_text, some_other_text)

    This has the advantage that you don't need to apply :func:`escape` to each
    argument and risk a bug and an XSS vulnerability if you forget one.

    Note that although this function uses ``str.format`` to do the
    interpolation, some of the formatting options provided by `str.format`_
    (e.g. number formatting) will not work, since all arguments are passed
    through :func:`conditional_escape` which (ultimately) calls
    :func:`~django.utils.encoding.force_text` on the values.

.. function:: format_html_join(sep, format_string, args_generator)

    A wrapper of :func:`format_html`, for the common case of a group of
    arguments that need to be formatted using the same format string, and then
    joined using ``sep``. ``sep`` is also passed through
    :func:`conditional_escape`.

    ``args_generator`` should be an iterator that returns the sequence of
    ``args`` that will be passed to :func:`format_html`. For example::

        format_html_join('\n', "<li>{0} {1}</li>", ((u.first_name, u.last_name)
                                                    for u in users))

.. function:: strip_tags(value)

    Removes anything that looks like an html tag from the string, that is
    anything contained within ``<>``.

    For example::

        strip_tags(value)

    If ``value`` is ``"<b>Joel</b> <button>is</button> a <span>slug</span>"`` the
    return value will be ``"Joel is a slug"``.

.. function:: remove_tags(value, tags)

    Removes a list of [X]HTML tag names from the output.

    For example::

        remove_tags(value, ["b", "span"])

    If ``value`` is ``"<b>Joel</b> <button>is</button> a <span>slug</span>"`` the
    return value will be ``"Joel <button>is</button> a slug"``.

    Note that this filter is case-sensitive.

    If ``value`` is ``"<B>Joel</B> <button>is</button> a <span>slug</span>"`` the
    return value will be ``"<B>Joel</B> <button>is</button> a slug"``.

.. _str.format: http://docs.python.org/library/stdtypes.html#str.format

``django.utils.http``
=====================

.. module:: django.utils.http
   :synopsis: HTTP helper functions. (URL encoding, cookie handling, ...)

.. function:: urlquote(url, safe='/')

    A version of Python's ``urllib.quote()`` function that can operate on
    unicode strings. The url is first UTF-8 encoded before quoting. The
    returned string can safely be used as part of an argument to a subsequent
    ``iri_to_uri()`` call without double-quoting occurring. Employs lazy
    execution.

.. function:: urlquote_plus(url, safe='')

    A version of Python's urllib.quote_plus() function that can operate on
    unicode strings. The url is first UTF-8 encoded before quoting. The
    returned string can safely be used as part of an argument to a subsequent
    ``iri_to_uri()`` call without double-quoting occurring. Employs lazy
    execution.

.. function:: urlencode(query, doseq=0)

    A version of Python's urllib.urlencode() function that can operate on
    unicode strings. The parameters are first case to UTF-8 encoded strings
    and then encoded as per normal.

.. function:: cookie_date(epoch_seconds=None)

    Formats the time to ensure compatibility with Netscape's cookie standard.

    Accepts a floating point number expressed in seconds since the epoch in
    UTC--such as that outputted by ``time.time()``. If set to ``None``,
    defaults to the current time.

    Outputs a string in the format ``Wdy, DD-Mon-YYYY HH:MM:SS GMT``.

.. function:: http_date(epoch_seconds=None)

    Formats the time to match the :rfc:`1123` date format as specified by HTTP
    :rfc:`2616#section-3.3.1` section 3.3.1.

    Accepts a floating point number expressed in seconds since the epoch in
    UTC--such as that outputted by ``time.time()``. If set to ``None``,
    defaults to the current time.

    Outputs a string in the format ``Wdy, DD Mon YYYY HH:MM:SS GMT``.

.. function:: base36_to_int(s)

    Converts a base 36 string to an integer. On Python 2 the output is
    guaranteed to be an ``int`` and not a ``long``.

.. function:: int_to_base36(i)

    Converts a positive integer to a base 36 string. On Python 2 ``i`` must be
    smaller than :data:`sys.maxint`.

``django.utils.safestring``
===========================

.. module:: django.utils.safestring
   :synopsis: Functions and classes for working with strings that can be displayed safely without further escaping in HTML.

Functions and classes for working with "safe strings": strings that can be
displayed safely without further escaping in HTML. Marking something as a "safe
string" means that the producer of the string has already turned characters
that should not be interpreted by the HTML engine (e.g. '<') into the
appropriate entities.

.. class:: SafeBytes

    .. versionadded:: 1.5

    A ``bytes`` subclass that has been specifically marked as "safe"
    (requires no further escaping) for HTML output purposes.

.. class:: SafeString

    A ``str`` subclass that has been specifically marked as "safe"
    (requires no further escaping) for HTML output purposes. This is
    :class:`SafeBytes` on Python 2 and :class:`SafeText` on Python 3.

.. class:: SafeText

    .. versionadded:: 1.5

    A ``str`` (in Python 3) or ``unicode`` (in Python 2) subclass
    that has been specifically marked as "safe" for HTML output purposes.

.. class:: SafeUnicode

    Historical name of :class:`SafeText`. Only available under Python 2.

.. function:: mark_safe(s)

    Explicitly mark a string as safe for (HTML) output purposes. The returned
    object can be used everywhere a string or unicode object is appropriate.

    Can be called multiple times on a single string.

.. function:: mark_for_escaping(s)

    Explicitly mark a string as requiring HTML escaping upon output. Has no
    effect on ``SafeData`` subclasses.

    Can be called multiple times on a single string (the resulting escaping is
    only applied once).

``django.utils.text``
=====================

.. module:: django.utils.text
    :synopsis: Text manipulation.

.. function:: slugify

    Converts to lowercase, removes non-word characters (alphanumerics and
    underscores) and converts spaces to hyphens. Also strips leading and trailing
    whitespace.

    For example::

        slugify(value)

    If ``value`` is ``"Joel is a slug"``, the output will be ``"joel-is-a-slug"``.

``django.utils.translation``
============================

.. module:: django.utils.translation
   :synopsis: Internationalization support.

For a complete discussion on the usage of the following see the
:doc:`translation documentation </topics/i18n/translation>`.

.. function:: gettext(message)

    Translates ``message`` and returns it in a UTF-8 bytestring

.. function:: ugettext(message)

    Translates ``message`` and returns it in a unicode string

.. function:: pgettext(context, message)

    Translates ``message`` given the ``context`` and returns
    it in a unicode string.

    For more information, see :ref:`contextual-markers`.

.. function:: gettext_lazy(message)
.. function:: ugettext_lazy(message)
.. function:: pgettext_lazy(context, message)

    Same as the non-lazy versions above, but using lazy execution.

    See :ref:`lazy translations documentation <lazy-translations>`.

.. function:: gettext_noop(message)
.. function:: ugettext_noop(message)

    Marks strings for translation but doesn't translate them now. This can be
    used to store strings in global variables that should stay in the base
    language (because they might be used externally) and will be translated
    later.

.. function:: ngettext(singular, plural, number)

    Translates ``singular`` and ``plural`` and returns the appropriate string
    based on ``number`` in a UTF-8 bytestring.

.. function:: ungettext(singular, plural, number)

    Translates ``singular`` and ``plural`` and returns the appropriate string
    based on ``number`` in a unicode string.

.. function:: npgettext(context, singular, plural, number)

    Translates ``singular`` and ``plural`` and returns the appropriate string
    based on ``number`` and the ``context`` in a unicode string.

.. function:: ngettext_lazy(singular, plural, number)
.. function:: ungettext_lazy(singular, plural, number)
.. function:: npgettext_lazy(singular, plural, number)

    Same as the non-lazy versions above, but using lazy execution.

    See :ref:`lazy translations documentation <lazy-translations>`.

.. function:: string_concat(*strings)

    Lazy variant of string concatenation, needed for translations that are
    constructed from multiple parts.

.. function:: activate(language)

    Fetches the translation object for a given language and installs it as
    the current translation object for the current thread.

.. function:: deactivate()

    De-installs the currently active translation object so that further _ calls
    will resolve against the default translation object, again.

.. function:: deactivate_all()

    Makes the active translation object a NullTranslations() instance. This is
    useful when we want delayed translations to appear as the original string
    for some reason.

.. function:: override(language, deactivate=False)

    .. versionadded:: 1.4

    A Python context manager that uses
    :func:`django.utils.translation.activate` to fetch the translation object
    for a given language, installing it as the translation object for the
    current thread and reinstall the previous active language on exit.
    Optionally it can simply deinstall the temporary translation on exit with
    :func:`django.utils.translation.deactivate` if the deactivate argument is
    True. If you pass None as the language argument, a NullTranslations()
    instance is installed while the context is active.

.. function:: get_language()

    Returns the currently selected language code.

.. function:: get_language_bidi()

    Returns selected language's BiDi layout:

    * ``False`` = left-to-right layout
    * ``True`` = right-to-left layout

.. function:: get_language_from_request(request, check_path=False)

    .. versionchanged:: 1.4

    Analyzes the request to find what language the user wants the system to show.
    Only languages listed in settings.LANGUAGES are taken into account. If the user
    requests a sublanguage where we have a main language, we send out the main
    language.

    If ``check_path`` is ``True``, the function first checks the requested URL
    for whether its path begins with a language code listed in the
    :setting:`LANGUAGES` setting.

.. function:: to_locale(language)

    Turns a language name (en-us) into a locale name (en_US).

.. function:: templatize(src)

    Turns a Django template into something that is understood by xgettext. It does
    so by translating the Django translation tags into standard gettext function
    invocations.

.. _time-zone-selection-functions:

``django.utils.timezone``
=========================

.. versionadded:: 1.4

.. module:: django.utils.timezone
    :synopsis: Timezone support.

.. data:: utc

    :class:`~datetime.tzinfo` instance that represents UTC.

.. function:: get_default_timezone()

    Returns a :class:`~datetime.tzinfo` instance that represents the
    :ref:`default time zone <default-current-time-zone>`.

.. function:: get_default_timezone_name()

    Returns the name of the :ref:`default time zone
    <default-current-time-zone>`.

.. function:: get_current_timezone()

    Returns a :class:`~datetime.tzinfo` instance that represents the
    :ref:`current time zone <default-current-time-zone>`.

.. function:: get_current_timezone_name()

    Returns the name of the :ref:`current time zone
    <default-current-time-zone>`.

.. function:: activate(timezone)

    Sets the :ref:`current time zone <default-current-time-zone>`. The
    ``timezone`` argument must be an instance of a :class:`~datetime.tzinfo`
    subclass or, if pytz_ is available, a time zone name.

.. function:: deactivate()

    Unsets the :ref:`current time zone <default-current-time-zone>`.

.. function:: override(timezone)

    This is a Python context manager that sets the :ref:`current time zone
    <default-current-time-zone>` on entry with :func:`activate()`, and restores
    the previously active time zone on exit. If the ``timezone`` argument is
    ``None``, the :ref:`current time zone <default-current-time-zone>` is unset
    on entry with :func:`deactivate()` instead.

.. versionadded:: 1.5

.. function:: localtime(value, timezone=None)

    Converts an aware :class:`~datetime.datetime` to a different time zone,
    by default the :ref:`current time zone <default-current-time-zone>`.

    This function doesn't work on naive datetimes; use :func:`make_aware`
    instead.

.. function:: now()

    Returns an aware or naive :class:`~datetime.datetime` that represents the
    current point in time when :setting:`USE_TZ` is ``True`` or ``False``
    respectively.

.. function:: is_aware(value)

    Returns ``True`` if ``value`` is aware, ``False`` if it is naive. This
    function assumes that ``value`` is a :class:`~datetime.datetime`.

.. function:: is_naive(value)

    Returns ``True`` if ``value`` is naive, ``False`` if it is aware. This
    function assumes that ``value`` is a :class:`~datetime.datetime`.

.. function:: make_aware(value, timezone)

    Returns an aware :class:`~datetime.datetime` that represents the same
    point in time as ``value`` in ``timezone``, ``value`` being a naive
    :class:`~datetime.datetime`.

    This function can raise an exception if ``value`` doesn't exist or is
    ambiguous because of DST transitions.

.. function:: make_naive(value, timezone)

    Returns an naive :class:`~datetime.datetime` that represents in
    ``timezone``  the same point in time as ``value``, ``value`` being an
    aware :class:`~datetime.datetime`

.. _pytz: http://pytz.sourceforge.net/

``django.utils.tzinfo``
=======================

.. module:: django.utils.tzinfo
   :synopsis: Implementation of ``tzinfo`` classes for use with ``datetime.datetime``.

.. class:: FixedOffset

    Fixed offset in minutes east from UTC.

.. class:: LocalTimezone

    Proxy timezone information from time module.
