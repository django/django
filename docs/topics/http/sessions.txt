===================
How to use sessions
===================

.. module:: django.contrib.sessions
   :synopsis: Provides session management for Django projects.

Django provides full support for anonymous sessions. The session framework
lets you store and retrieve arbitrary data on a per-site-visitor basis. It
stores data on the server side and abstracts the sending and receiving of
cookies. Cookies contain a session ID -- not the data itself (unless you're
using the :ref:`cookie based backend<cookie-session-backend>`).

Enabling sessions
=================

Sessions are implemented via a piece of :doc:`middleware </ref/middleware>`.

To enable session functionality, do the following:

* Edit the :setting:`MIDDLEWARE_CLASSES` setting and make sure
  it contains ``'django.contrib.sessions.middleware.SessionMiddleware'``.
  The default ``settings.py`` created by ``django-admin.py startproject``
  has ``SessionMiddleware`` activated.

If you don't want to use sessions, you might as well remove the
``SessionMiddleware`` line from :setting:`MIDDLEWARE_CLASSES` and
``'django.contrib.sessions'`` from your :setting:`INSTALLED_APPS`.
It'll save you a small bit of overhead.

Configuring the session engine
==============================

By default, Django stores sessions in your database (using the model
``django.contrib.sessions.models.Session``). Though this is convenient, in
some setups it's faster to store session data elsewhere, so Django can be
configured to store session data on your filesystem or in your cache.

Using database-backed sessions
------------------------------

If you want to use a database-backed session, you need to add
``'django.contrib.sessions'`` to your :setting:`INSTALLED_APPS` setting.

Once you have configured your installation, run ``manage.py syncdb``
to install the single database table that stores session data.

.. _cached-sessions-backend:

Using cached sessions
---------------------

For better performance, you may want to use a cache-based session backend.

To store session data using Django's cache system, you'll first need to make
sure you've configured your cache; see the :doc:`cache documentation
</topics/cache>` for details.

.. warning::

    You should only use cache-based sessions if you're using the Memcached
    cache backend. The local-memory cache backend doesn't retain data long
    enough to be a good choice, and it'll be faster to use file or database
    sessions directly instead of sending everything through the file or
    database cache backends.

If you have multiple caches defined in :setting:`CACHES`, Django will use the
default cache. To use another cache, set :setting:`SESSION_CACHE_ALIAS` to the
name of that cache.

.. versionchanged:: 1.5
    The :setting:`SESSION_CACHE_ALIAS` setting was added.

Once your cache is configured, you've got two choices for how to store data in
the cache:

* Set :setting:`SESSION_ENGINE` to
  ``"django.contrib.sessions.backends.cache"`` for a simple caching session
  store. Session data will be stored directly your cache. However, session
  data may not be persistent: cached data can be evicted if the cache fills
  up or if the cache server is restarted.

* For persistent, cached data, set :setting:`SESSION_ENGINE` to
  ``"django.contrib.sessions.backends.cached_db"``. This uses a
  write-through cache -- every write to the cache will also be written to
  the database. Session reads only use the database if the data is not
  already in the cache.

Both session stores are quite fast, but the simple cache is faster because it
disregards persistence. In most cases, the ``cached_db`` backend will be fast
enough, but if you need that last bit of performance, and are willing to let
session data be expunged from time to time, the ``cache`` backend is for you.

If you use the ``cached_db`` session backend, you also need to follow the
configuration instructions for the `using database-backed sessions`_.

Using file-based sessions
-------------------------

To use file-based sessions, set the :setting:`SESSION_ENGINE` setting to
``"django.contrib.sessions.backends.file"``.

You might also want to set the :setting:`SESSION_FILE_PATH` setting (which
defaults to output from ``tempfile.gettempdir()``, most likely ``/tmp``) to
control where Django stores session files. Be sure to check that your Web
server has permissions to read and write to this location.

.. _cookie-session-backend:

Using cookie-based sessions
---------------------------

.. versionadded:: 1.4

To use cookies-based sessions, set the :setting:`SESSION_ENGINE` setting to
``"django.contrib.sessions.backends.signed_cookies"``. The session data will be
stored using Django's tools for :doc:`cryptographic signing </topics/signing>`
and the :setting:`SECRET_KEY` setting.

.. note::

    It's recommended to leave the :setting:`SESSION_COOKIE_HTTPONLY` setting
    ``True`` to prevent tampering of the stored data from JavaScript.

.. warning::

    **The session data is signed but not encrypted**

    When using the cookies backend the session data can be read by the client.

    A MAC (Message Authentication Code) is used to protect the data against
    changes by the client, so that the session data will be invalidated when being
    tampered with. The same invalidation happens if the client storing the
    cookie (e.g. your user's browser) can't store all of the session cookie and
    drops data. Even though Django compresses the data, it's still entirely
    possible to exceed the `common limit of 4096 bytes`_ per cookie.

    **No freshness guarantee**

    Note also that while the MAC can guarantee the authenticity of the data
    (that it was generated by your site, and not someone else), and the
    integrity of the data (that it is all there and correct), it cannot
    guarantee freshness i.e. that you are being sent back the last thing you
    sent to the client. This means that for some uses of session data, the
    cookie backend might open you up to `replay attacks`_. Cookies will only be
    detected as 'stale' if they are older than your
    :setting:`SESSION_COOKIE_AGE`.

    **Performance**

    Finally, the size of a cookie can have an impact on the `speed of your site`_.

.. _`common limit of 4096 bytes`: http://tools.ietf.org/html/rfc2965#section-5.3
.. _`replay attacks`: http://en.wikipedia.org/wiki/Replay_attack
.. _`speed of your site`: http://yuiblog.com/blog/2007/03/01/performance-research-part-3/

Using sessions in views
=======================

When ``SessionMiddleware`` is activated, each :class:`~django.http.HttpRequest`
object -- the first argument to any Django view function -- will have a
``session`` attribute, which is a dictionary-like object.

You can read it and write to ``request.session`` at any point in your view.
You can edit it multiple times.

.. class:: backends.base.SessionBase

    This is the base class for all session objects. It has the following
    standard dictionary methods:

    .. method:: __getitem__(key)

      Example: ``fav_color = request.session['fav_color']``

    .. method:: __setitem__(key, value)

      Example: ``request.session['fav_color'] = 'blue'``

    .. method:: __delitem__(key)

      Example: ``del request.session['fav_color']``. This raises ``KeyError``
      if the given ``key`` isn't already in the session.

    .. method:: __contains__(key)

      Example: ``'fav_color' in request.session``

    .. method:: get(key, default=None)

      Example: ``fav_color = request.session.get('fav_color', 'red')``

    .. method:: pop(key)

      Example: ``fav_color = request.session.pop('fav_color')``

    .. method:: keys

    .. method:: items

    .. method:: setdefault

    .. method:: clear

    It also has these methods:

    .. method:: flush

      Delete the current session data from the session and regenerate the
      session key value that is sent back to the user in the cookie. This is
      used if you want to ensure that the previous session data can't be
      accessed again from the user's browser (for example, the
      :func:`django.contrib.auth.logout()` function calls it).

    .. method:: set_test_cookie

      Sets a test cookie to determine whether the user's browser supports
      cookies. Due to the way cookies work, you won't be able to test this
      until the user's next page request. See `Setting test cookies`_ below for
      more information.

    .. method:: test_cookie_worked

      Returns either ``True`` or ``False``, depending on whether the user's
      browser accepted the test cookie. Due to the way cookies work, you'll
      have to call ``set_test_cookie()`` on a previous, separate page request.
      See `Setting test cookies`_ below for more information.

    .. method:: delete_test_cookie

      Deletes the test cookie. Use this to clean up after yourself.

    .. method:: set_expiry(value)

      Sets the expiration time for the session. You can pass a number of
      different values:

      * If ``value`` is an integer, the session will expire after that
        many seconds of inactivity. For example, calling
        ``request.session.set_expiry(300)`` would make the session expire
        in 5 minutes.

      * If ``value`` is a ``datetime`` or ``timedelta`` object, the
        session will expire at that specific date/time.

      * If ``value`` is ``0``, the user's session cookie will expire
        when the user's Web browser is closed.

      * If ``value`` is ``None``, the session reverts to using the global
        session expiry policy.

      Reading a session is not considered activity for expiration
      purposes. Session expiration is computed from the last time the
      session was *modified*.

    .. method:: get_expiry_age

      Returns the number of seconds until this session expires. For sessions
      with no custom expiration (or those set to expire at browser close), this
      will equal :setting:`SESSION_COOKIE_AGE`.

      This function accepts two optional keyword arguments:

      - ``modification``: last modification of the session, as a
        :class:`~datetime.datetime` object. Defaults to the current time.
      - ``expiry``: expiry information for the session, as a
        :class:`~datetime.datetime` object, an :func:`int` (in seconds), or
        ``None``. Defaults to the value stored in the session by
        :meth:`set_expiry`, if there is one, or ``None``.

    .. method:: get_expiry_date

      Returns the date this session will expire. For sessions with no custom
      expiration (or those set to expire at browser close), this will equal the
      date :setting:`SESSION_COOKIE_AGE` seconds from now.

      This function accepts the same keyword argumets as :meth:`get_expiry_age`.

    .. method:: get_expire_at_browser_close

      Returns either ``True`` or ``False``, depending on whether the user's
      session cookie will expire when the user's Web browser is closed.

    .. method:: SessionBase.clear_expired

      .. versionadded:: 1.5

      Removes expired sessions from the session store. This class method is
      called by :djadmin:`clearsessions`.

Session object guidelines
-------------------------

* Use normal Python strings as dictionary keys on ``request.session``. This
  is more of a convention than a hard-and-fast rule.

* Session dictionary keys that begin with an underscore are reserved for
  internal use by Django.

* Don't override ``request.session`` with a new object, and don't access or
  set its attributes. Use it like a Python dictionary.

Examples
--------

This simplistic view sets a ``has_commented`` variable to ``True`` after a user
posts a comment. It doesn't let a user post a comment more than once::

    def post_comment(request, new_comment):
        if request.session.get('has_commented', False):
            return HttpResponse("You've already commented.")
        c = comments.Comment(comment=new_comment)
        c.save()
        request.session['has_commented'] = True
        return HttpResponse('Thanks for your comment!')

This simplistic view logs in a "member" of the site::

    def login(request):
        m = Member.objects.get(username=request.POST['username'])
        if m.password == request.POST['password']:
            request.session['member_id'] = m.id
            return HttpResponse("You're logged in.")
        else:
            return HttpResponse("Your username and password didn't match.")

...And this one logs a member out, according to ``login()`` above::

    def logout(request):
        try:
            del request.session['member_id']
        except KeyError:
            pass
        return HttpResponse("You're logged out.")

The standard :meth:`django.contrib.auth.logout` function actually does a bit
more than this to prevent inadvertent data leakage. It calls the
:meth:`~backends.base.SessionBase.flush` method of ``request.session``.
We are using this example as a demonstration of how to work with session
objects, not as a full ``logout()`` implementation.

Setting test cookies
====================

As a convenience, Django provides an easy way to test whether the user's
browser accepts cookies. Just call the
:meth:`~backends.base.SessionBase.set_test_cookie` method of
``request.session`` in a view, and call
:meth:`~backends.base.SessionBase.test_cookie_worked` in a subsequent view --
not in the same view call.

This awkward split between ``set_test_cookie()`` and ``test_cookie_worked()``
is necessary due to the way cookies work. When you set a cookie, you can't
actually tell whether a browser accepted it until the browser's next request.

It's good practice to use
:meth:`~backends.base.SessionBase.delete_test_cookie()` to clean up after
yourself. Do this after you've verified that the test cookie worked.

Here's a typical usage example::

    def login(request):
        if request.method == 'POST':
            if request.session.test_cookie_worked():
                request.session.delete_test_cookie()
                return HttpResponse("You're logged in.")
            else:
                return HttpResponse("Please enable cookies and try again.")
        request.session.set_test_cookie()
        return render_to_response('foo/login_form.html')

Using sessions out of views
===========================

An API is available to manipulate session data outside of a view::

    >>> from django.contrib.sessions.backends.db import SessionStore
    >>> import datetime
    >>> s = SessionStore()
    >>> s['last_login'] = datetime.datetime(2005, 8, 20, 13, 35, 10)
    >>> s.save()
    >>> s.session_key
    '2b1189a188b44ad18c35e113ac6ceead'

    >>> s = SessionStore(session_key='2b1189a188b44ad18c35e113ac6ceead')
    >>> s['last_login']
    datetime.datetime(2005, 8, 20, 13, 35, 0)

In order to prevent session fixation attacks, sessions keys that don't exist
are regenerated::

    >>> from django.contrib.sessions.backends.db import SessionStore
    >>> s = SessionStore(session_key='no-such-session-here')
    >>> s.save()
    >>> s.session_key
    'ff882814010ccbc3c870523934fee5a2'

If you're using the ``django.contrib.sessions.backends.db`` backend, each
session is just a normal Django model. The ``Session`` model is defined in
``django/contrib/sessions/models.py``. Because it's a normal model, you can
access sessions using the normal Django database API::

    >>> from django.contrib.sessions.models import Session
    >>> s = Session.objects.get(pk='2b1189a188b44ad18c35e113ac6ceead')
    >>> s.expire_date
    datetime.datetime(2005, 8, 20, 13, 35, 12)

Note that you'll need to call ``get_decoded()`` to get the session dictionary.
This is necessary because the dictionary is stored in an encoded format::

    >>> s.session_data
    'KGRwMQpTJ19hdXRoX3VzZXJfaWQnCnAyCkkxCnMuMTExY2ZjODI2Yj...'
    >>> s.get_decoded()
    {'user_id': 42}

When sessions are saved
=======================

By default, Django only saves to the session database when the session has been
modified -- that is if any of its dictionary values have been assigned or
deleted::

    # Session is modified.
    request.session['foo'] = 'bar'

    # Session is modified.
    del request.session['foo']

    # Session is modified.
    request.session['foo'] = {}

    # Gotcha: Session is NOT modified, because this alters
    # request.session['foo'] instead of request.session.
    request.session['foo']['bar'] = 'baz'

In the last case of the above example, we can tell the session object
explicitly that it has been modified by setting the ``modified`` attribute on
the session object::

    request.session.modified = True

To change this default behavior, set the :setting:`SESSION_SAVE_EVERY_REQUEST`
setting to ``True``. When set to ``True``, Django will save the session to the
database on every single request.

Note that the session cookie is only sent when a session has been created or
modified. If :setting:`SESSION_SAVE_EVERY_REQUEST` is ``True``, the session
cookie will be sent on every request.

Similarly, the ``expires`` part of a session cookie is updated each time the
session cookie is sent.

.. versionchanged:: 1.5
  The session is not saved if the response's status code is 500.

Browser-length sessions vs. persistent sessions
===============================================

You can control whether the session framework uses browser-length sessions vs.
persistent sessions with the :setting:`SESSION_EXPIRE_AT_BROWSER_CLOSE`
setting.

By default, :setting:`SESSION_EXPIRE_AT_BROWSER_CLOSE` is set to ``False``,
which means session cookies will be stored in users' browsers for as long as
:setting:`SESSION_COOKIE_AGE`. Use this if you don't want people to have to
log in every time they open a browser.

If :setting:`SESSION_EXPIRE_AT_BROWSER_CLOSE` is set to ``True``, Django will
use browser-length cookies -- cookies that expire as soon as the user closes
his or her browser. Use this if you want people to have to log in every time
they open a browser.

This setting is a global default and can be overwritten at a per-session level
by explicitly calling the :meth:`~backends.base.SessionBase.set_expiry` method
of ``request.session`` as described above in `using sessions in views`_.

Clearing the session store
==========================

As users create new sessions on your website, session data can accumulate in
your session store. If you're using the database backend, the
``django_session`` database table will grow. If you're using the file backend,
your temporary directory will contain an increasing number of files.

To understand this problem, consider what happens with the database backend.
When a user logs in, Django adds a row to the ``django_session`` database
table. Django updates this row each time the session data changes. If the user
logs out manually, Django deletes the row. But if the user does *not* log out,
the row never gets deleted. A similar process happens with the file backend.

Django does *not* provide automatic purging of expired sessions. Therefore,
it's your job to purge expired sessions on a regular basis. Django provides a
clean-up management command for this purpose: :djadmin:`clearsessions`. It's
recommended to call this command on a regular basis, for example as a daily
cron job.

Note that the cache backend isn't vulnerable to this problem, because caches
automatically delete stale data. Neither is the cookie backend, because the
session data is stored by the users' browsers.

Settings
========

A few :doc:`Django settings </ref/settings>` give you control over session
behavior:

SESSION_ENGINE
--------------

Default: ``django.contrib.sessions.backends.db``

Controls where Django stores session data. Valid values are:

* ``'django.contrib.sessions.backends.db'``
* ``'django.contrib.sessions.backends.file'``
* ``'django.contrib.sessions.backends.cache'``
* ``'django.contrib.sessions.backends.cached_db'``
* ``'django.contrib.sessions.backends.signed_cookies'``

See `configuring the session engine`_ for more details.

SESSION_FILE_PATH
-----------------

Default: ``/tmp/``

If you're using file-based session storage, this sets the directory in
which Django will store session data.

SESSION_COOKIE_AGE
------------------

Default: ``1209600`` (2 weeks, in seconds)

The age of session cookies, in seconds.

SESSION_COOKIE_DOMAIN
---------------------

Default: ``None``

The domain to use for session cookies. Set this to a string such as
``".example.com"`` (note the leading dot!) for cross-domain cookies, or use
``None`` for a standard domain cookie.

SESSION_COOKIE_HTTPONLY
-----------------------

Default: ``True``

Whether to use HTTPOnly flag on the session cookie. If this is set to
``True``, client-side JavaScript will not to be able to access the
session cookie.

HTTPOnly_ is a flag included in a Set-Cookie HTTP response header. It
is not part of the :rfc:`2109` standard for cookies, and it isn't honored
consistently by all browsers. However, when it is honored, it can be a
useful way to mitigate the risk of client side script accessing the
protected cookie data.

.. versionchanged:: 1.4
    The default value of the setting was changed from ``False`` to ``True``.

.. _HTTPOnly: https://www.owasp.org/index.php/HTTPOnly

SESSION_COOKIE_NAME
-------------------

Default: ``'sessionid'``

The name of the cookie to use for sessions. This can be whatever you want.

SESSION_COOKIE_PATH
-------------------

Default: ``'/'``

The path set on the session cookie. This should either match the URL path of
your Django installation or be parent of that path.

This is useful if you have multiple Django instances running under the same
hostname. They can use different cookie paths, and each instance will only see
its own session cookie.

SESSION_COOKIE_SECURE
---------------------

Default: ``False``

Whether to use a secure cookie for the session cookie. If this is set to
``True``, the cookie will be marked as "secure," which means browsers may
ensure that the cookie is only sent under an HTTPS connection.

SESSION_EXPIRE_AT_BROWSER_CLOSE
-------------------------------

Default: ``False``

Whether to expire the session when the user closes his or her browser. See
"Browser-length sessions vs. persistent sessions" above.

SESSION_SAVE_EVERY_REQUEST
--------------------------

Default: ``False``

Whether to save the session data on every request. If this is ``False``
(default), then the session data will only be saved if it has been modified --
that is, if any of its dictionary values have been assigned or deleted.

.. _Django settings: ../settings/

Technical details
=================

* The session dictionary should accept any pickleable Python object. See
  the :mod:`pickle` module for more information.

* Session data is stored in a database table named ``django_session`` .

* Django only sends a cookie if it needs to. If you don't set any session
  data, it won't send a session cookie.

Session IDs in URLs
===================

The Django sessions framework is entirely, and solely, cookie-based. It does
not fall back to putting session IDs in URLs as a last resort, as PHP does.
This is an intentional design decision. Not only does that behavior make URLs
ugly, it makes your site vulnerable to session-ID theft via the "Referer"
header.
