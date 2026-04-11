###################
 NEWS for aiosmtpd
###################

.. towncrier release notes start

1.4.6 (2024-05-18)
==================

* STARTTLS is now fully enforced if used.

1.4.5 (2024-03-02)
==================

* Fixed incorrect handling of newlines.


1.4.4.post2 (2023-01-19)
========================

Fixed/Improved
--------------
* Prevent unclean repo from being built (Closes #365)
* Reduce chance of not-ready-for-release packages from being uploaded


1.4.4 (2023-01-17)
==================

Fixed/Improved
--------------
* No longer expect an implicit creation of the event loop through ``get_event_loop()`` (Closes #353)


1.4.3 (2022-12-21)
=====================

Fixed/Improved
--------------
* Is now compatible with uvloop
* Add compatibility for Python 3.10 and 3.11 (Closes #322)
* Test matrix update (Closes #306)

  * Drop Python 3.6, PyPy 3.6 (some) and MacOS 10
  * Add Python 3.10 & 3.11, PyPy 3.7 & 3.8, Ubuntu 22.04, MacOS 11 & 12

* Expanded tox environments
* Longer AUTOSTOP_DELAY especially for Windows (Closes #313)
* Update signing keys
* Some documentation fixes


1.4.2 (2021-03-08)
=====================

Fixed/Improved
--------------
* Controller's ``ready_timeout`` parameter increased from ``1.0`` to ``5.0``.
  This won't slow down Controller startup because it's just a timeout limit
  (instead of a sleep delay),
  but this should help prevent Controller from giving up too soon,
  especially during situations where system/network is a bit busy causing slowdowns.
  (See #262)
* Timeout messages in ``Controller.start()`` gets more details and a mention about the
  ``ready_timeout`` parameter. (See #262)
* Prevent sensitive AUTH information leak by sanitizing the repr()
  of AuthResult and LoginPassword.


1.4.1 (2021-03-04)
==================

Fixed/Improved
--------------
* Maximum length of email address local part is customizable, defaults to no limit. (Closes #257)


1.4.0 (2021-02-26)
==================

Added
-----
* Support for |PROXY Protocol|_ (Closes #174)
* Example for authentication
* SSL Support for CLI. See :ref:`the man page <manpage>` for more info. (Closes #172)
* New :class:`UnixSocketController` class to implement Unix socket-based SMTP server
  (Closes #114)

.. _`PROXY Protocol`: https://www.haproxy.com/blog/using-haproxy-with-the-proxy-protocol-to-better-secure-your-database/
.. |PROXY Protocol| replace:: **PROXY Protocol**

Fixed/Improved
--------------
* ``pypy3`` testenv for tox can now run on Windows
* ``static`` testenv now auto-skipped on Windows
* Now uses Sphinx's Doctest facility, which is much more flexible than pytest's doctest


1.3.2 (2021-02-20)
==================

Added
-----
* GPG Signing Key info to ``README.rst`` and PyPI Long Desc
* Hidden ``static`` test env for static code checking

Fixed/Improved
--------------
* Fixed Documentation Issues that might cause automatic package builders to fail
* Also consider ``EAFNOSUPPORT`` in IPv6 detection (Closes #244, again)
* Update PyPI Long Description


1.3.1 (2021-02-18)
==================

Fixed/Improved
--------------
* ``ready_timeout`` now actually enforced, raising ``TimeoutError`` if breached
* Hides only expected exceptions raised by ``Controller._testconn()``
* No longer fail with opaque "Unknown Error" if ``hostname=""`` (Closes #244)
* No longer hardcode localhost as ``::1`` but perform IPv6 detection first (Closes #244)


1.3.0 (2021-02-09)
==================

Added
-----
* New :meth:`handle_EHLO` interaction where said method can now modify list of responses
  to the EHLO command (Closes #155)

Fixed/Improved
--------------
* No longer have to workaround ``bpo-27931`` which has been fixed in Python 3.6 anyways.
* New :meth:`handle_EHLO` interaction where said method can now modify list of responses
  to the EHLO command (Closes #155)
* ``authenticator`` system improves on ``auth_callback`` by enabling the called function
  to see the SMTP Session and other info.
  (``auth_callback`` will be deprecated in 2.0)
* ``__version__`` is now an attribute in ``__init__.py``,
  and can be imported from the 'plain' ``aiosmtpd`` module.
  (It gets reimported to ``aiosmtpd.smtp``,
  so programs relying on ``aiosmtpd.smtp.__version__`` should still work.)
  (Closes #241)
* Uses pure ``pytest`` for all test cases (Closes #198)


1.2.4 (2021-01-24)
==================

Added
-----
* Optional (default-disabled) logging of ``AUTH`` interaction -- with severe warnings

Fixed/Improved
--------------
* ``AUTH`` command line now sanitized before logging (Closes #233)
* Remove special handling for lone ``=`` during AUTH;
  it is now treated as simple Base64-encoded ``b""``.
  This is the correct, strict interpretation of :rfc:`4954` mentions about ``=``


1.2.3 (2021-01-14)
==================

Added
-----
* Test for ``SMTP.__init__`` behavior after taking out code that edits TLS Context
* Implement mechanism to limit the number of commands sent (Closes #145)

Fixed/Improved
--------------
* ``handle_exception()`` no longer gets called when the client disconnected (Closes #127, #162)
* Implement & enforce line-length-limit, thus becoming Compliant with RFC 5321 § 4.5.3.1.6
* Delay all SMTP Status Code replies during ``DATA`` phase until the phase termination (Closes #9)
* Now catches ``Controller.factory()`` failure during ``Controller.start()`` (Closes #212)
* :class:`SMTP` no longer edits user-supplied SSL Context (Closes #191)
* Implement waiting for SSL setup/handshake within ``STARTTLS`` handler to be able to catch and handle
  (log) errors and to avoid session hanging around until timeout in such cases
* Add session peer information to some logging output where it was missing
* Support AUTH mechanisms with dash(es) in their names (Closes #224)
* Remove some double-logging of commands sent by clients
* LMTP servers now correctly advertise extensions in reply to ``LHLO`` (Closes #123, #124)
* ``NOOP`` now accepted before ``STARTTLS`` even if ``require_starttls=True`` (Closes #124)


1.2.2 (2020-11-08)
==================

Added
-----
* **Apache License version 2.0**
* Support for SMTP ``AUTH``, with AUTH hooks feature
* Built-in implementation for ``AUTH PLAIN`` and ``AUTH LOGIN`` logic (Closes #102)
* Feature to inject keyword args during server class instantiation in ``Controller.factory``
  (potentially Closes #194, #179)
* Support for Python 3.8 and 3.9.0 (also Closes #188)

Fixed/Improved
--------------
* Don't strip last ``\r\n`` prior to terminating dot.
* Slight improvement to make Test Suite more maintainable
* No more failures/DeprecationWarnings for Python 3.8 (Closes #167)
* Faster ``_handle_client()`` processing
* Faster method access for ``smtp_*``, ``handle_*``, and ``auth_*`` hooks

Removed
-------
* Unit Tests that mocked too deep, possibly masking observable internal behaviors
* Drop support for Python 3.5


1.2 (2018-09-01)
================
* Improve the documentation on enabling ``STARTTLS``.  (Closes #125)
* Add customizable ident field to SMTP class constructor. (Closes #131)
* Remove asyncio.coroutine decorator as it was introduced in Python 3.5.
* Add Controller docstring, explain dual-stack binding. (Closes #140)
* Gracefully handle ASCII decoding exceptions. (Closes #142)
* Fix typo.
* Improve Controller ssl_context documentation.
* Add timeout feature. (Partial fix for #145)


1.1 (2017-07-06)
================
* Drop support for Python 3.4.
* As per RFC 5321, §4.1.4, multiple ``HELO`` / ``EHLO`` commands in the same
  session are semantically equivalent to ``RSET``.  (Closes #78)
* As per RFC 5321, $4.1.1.9, ``NOOP`` takes an optional argument, which is
  ignored.  **API BREAK** If you have a handler that implements
  ``handle_NOOP()``, it previously took zero arguments but now requires a
  single argument.  (Closes #107)
* The command line options ``--version`` / ``-v`` has been added to print the
  package's current version number.  (Closes #111)
* General improvements in the ``Controller`` class.  (Closes #104)
* When aiosmtpd handles a ``STARTTLS`` it must arrange for the original
  transport to be closed when the wrapped transport is closed.  This fixes a
  hidden exception which occurs when an EOF is received on the original
  tranport after the connection is lost.  (Closes #83)
* Widen the catch of ``ConnectionResetError`` and ``CancelledError`` to also
  catch such errors from handler methods.  (Closes #110)
* Added a manpage for the ``aiosmtpd`` command line script.  (Closes #116)
* Added much better support for the ``HELP``.  There's a new decorator called
  ``@syntax()`` which you can use in derived classes to decorate ``smtp_*()``
  methods.  These then show up in ``HELP`` responses.  This also fixes
  ``HELP`` responses for the ``LMTP`` subclass.  (Closes #113)
* The ``Controller`` class now takes an optional keyword argument
  ``ssl_context`` which is passed directly to the asyncio ``create_server()``
  call.

1.0 (2017-05-15)
================
* Release.

1.0rc1 (2017-05-12)
===================
* Improved documentation.

1.0b1 (2017-05-07)
==================
* The connection peer is displayed in all INFO level logging.
* When running the test suite, you can include a ``-E`` option after the
  ``--`` separator to boost the debugging output.
* The main SMTP readline loops are now more robust against connection resets
  and mid-read EOFs.  (Closes #62)
* ``Proxy`` handlers work with ``SMTP`` servers regardless of the value of the
  ``decode_data`` argument.
* The command line script is now installed as ``aiosmtpd`` instead of
  ``smtpd``.
* The ``SMTP`` class now does a better job of handling Unicode, when the
  client does not claim to support ``SMTPUTF8`` but sends non-ASCII anyway.
  The server forces ASCII-only handling when ``enable_SMTPUTF8=False`` (the
  default) is passed to the constructor.  The command line arguments
  ``decode_data=True`` and ``enable_SMTPUTF8=True`` are no longer mutually
  exclusive.
* Officially support Windows.  (Closes #76)

1.0a5 (2017-04-06)
==================
* A new handler hook API has been added which provides more flexibility but
  requires more responsibility (e.g. hooks must return a string status).
  Deprecate ``SMTP.ehlo_hook()`` and ``SMTP.rset_hook()``.
* Deprecate handler ``process_message()`` methods.  Use the new asynchronous
  ``handle_DATA()`` methods, which take a session and an envelope object.
* Added the ``STARTTLS`` extension.  Given by Konstantin Volkov.
* Minor changes to the way the ``Debugging`` handler prints ``mail_options``
  and ``rcpt_options`` (although the latter is still not support in ``SMTP``).
* ``DATA`` method now respects original line endings, and passing size limits
  is now handled better.  Given by Konstantin Volkov.
* The ``Controller`` class has two new optional keyword arguments.

  - ``ready_timeout`` specifies a timeout in seconds that can be used to limit
    the amount of time it waits for the server to become ready.  This can also
    be overridden with the environment variable
    ``AIOSMTPD_CONTROLLER_TIMEOUT``. (Closes #35)
  - ``enable_SMTPUTF8`` is passed through to the ``SMTP`` constructor in the
    default factory.  If you override ``Controller.factory()`` you can pass
    ``self.enable_SMTPUTF8`` yourself.
* Handlers can define a ``handle_tls_handshake()`` method, which takes a
  session object, and is called if SSL is enabled during the making of the
  connection.  (Closes #48)
* Better Windows compatibility.
* Better Python 3.4 compatibility.
* Use ``flufl.testing`` package for nose2 and flake8 plugins.
* The test suite has achieved 100% code coverage. (Closes #2)

1.0a4 (2016-11-29)
==================
* The SMTP server connection identifier can be changed by setting the
  ``__ident__`` attribute on the ``SMTP`` instance.  (Closes #20)
* Fixed a new incompatibility with the ``atpublic`` library.

1.0a3 (2016-11-24)
==================
* Fix typo in ``Message.prepare_message()`` handler.  The crafted
  ``X-RcptTos`` header is renamed to ``X-RcptTo`` for backward compatibility
  with older libraries.
* Add a few hooks to make subclassing easier:

  * ``SMTP.ehlo_hook()`` is called just before the final, non-continuing 250
    response to allow subclasses to add additional ``EHLO`` sub-responses.
  * ``SMTP.rset_hook()`` is called just before the final 250 command to allow
    subclasses to provide additional ``RSET`` functionality.
  * ``Controller.make_socket()`` allows subclasses to customize the creation
    of the socket before binding.

1.0a2 (2016-11-22)
==================
* Officially support Python 3.6.
* Fix support for both IPv4 and IPv6 based on the ``--listen`` option.  Given
  by Jason Coombs.  (Closes #3)
* Correctly handle client disconnects.  Given by Konstantin vz'One Enchant.
* The SMTP class now takes an optional ``hostname`` argument.  Use this if you
  want to avoid the use of ``socket.getfqdn()``.  Given by Konstantin vz'One
  Enchant.
* Close the transport and thus the connection on SMTP ``QUIT``.  (Closes #11)
* Added an ``AsyncMessage`` handler.  Given by Konstantin vz'One Enchant.
* Add an examples/ directory.
* Flake8 clean.

1.0a1 (2015-10-19)
==================
* Initial release.
