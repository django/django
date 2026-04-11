.. _smtp:

=================
 The SMTP Module
=================

At the heart of this module is the ``SMTP`` class in the ``aiosmtpd.smtp`` module.
This class implements the :rfc:`5321` Simple Mail Transport Protocol.
Often you won't run an ``SMTP`` instance directly,
but instead will use a :ref:`Controller <controller>` instance to run the server in a subthread.

.. doctest::

    >>> from aiosmtpd.controller import Controller

The ``SMTP`` class is itself a subclass of |StreamReaderProtocol|_


.. _subclass:

Subclassing
===========

While behavior for common SMTP commands can be specified using :ref:`handlers
<handlers>`, more complex specializations such as adding custom SMTP commands
require subclassing the ``SMTP`` class.

For example, let's say you wanted to add a new SMTP command called ``PING``.
All methods implementing ``SMTP`` commands are prefixed with ``smtp_``; they
must also be coroutines.  Here's how you could implement this use case:

.. doctest::

    >>> import asyncio
    >>> from aiosmtpd.smtp import SMTP as Server, syntax
    >>> class MyServer(Server):
    ...     @syntax('PING [ignored]')
    ...     async def smtp_PING(self, arg):
    ...         await self.push('259 Pong')

Now let's run this server in a controller:

.. doctest::

    >>> from aiosmtpd.handlers import Sink
    >>> class MyController(Controller):
    ...     def factory(self):
    ...         return MyServer(self.handler)

    >>> controller = MyController(Sink())
    >>> controller.start()

We can now connect to this server with an ``SMTP`` client.

.. doctest::

    >>> from smtplib import SMTP as Client
    >>> client = Client(controller.hostname, controller.port)

Let's ping the server.  Since the ``PING`` command isn't an official ``SMTP``
command, we have to use the lower level interface to talk to it.

.. doctest::

    >>> code, message = client.docmd('PING')
    >>> code
    259
    >>> message
    b'Pong'

Because we prefixed the ``smtp_PING()`` method with the ``@syntax()``
decorator, the command shows up in the ``HELP`` output.

.. doctest::

    >>> print(client.help().decode('utf-8'))
    Supported commands: AUTH DATA EHLO HELO HELP MAIL NOOP PING QUIT RCPT RSET VRFY

And we can get more detailed help on the new command.

.. doctest::

    >>> print(client.help('PING').decode('utf-8'))
    Syntax: PING [ignored]

Don't forget to ``stop()`` the controller when you're done.

.. doctest::

    >>> controller.stop()


Server hooks
============

.. warning:: These methods are deprecated.  See :ref:`handler hooks <hooks>`
             instead.

The ``SMTP`` server class also implements some hooks which your subclass can
override to provide additional responses.

.. py:function:: ehlo_hook()

    This hook makes it possible for subclasses to return additional ``EHLO``
    responses.  This method, called *asynchronously* and taking no arguments,
    can do whatever it wants, including (most commonly) pushing new
    ``250-<command>`` responses to the client.  This hook is called just
    before the standard ``250 HELP`` which ends the ``EHLO`` response from the
    server.

    .. deprecated:: 1.2

.. py:function:: rset_hook()

    This hook makes it possible to return additional ``RSET`` responses.  This
    method, called *asynchronously* and taking no arguments, is called just
    before the standard ``250 OK`` which ends the ``RSET`` response from the
    server.

    .. deprecated:: 1.2


.. _smtp_api:

aiosmtpd.smtp
=============

.. py:module:: aiosmtpd.smtp

.. py:data:: AuthenticatorType
   :value: Callable[[SMTP, Session, Envelope, str, Any], AuthResult]

.. decorator:: auth_mechanism(actual_name)

   :param actual_name: Name of the AUTH Mechanism implemented by the method.
      See :ref:`authmech` for more info.
   :type actual_name: str

   This decorator specifies the actual name of the AUTH Mechanism implemented
   by the method being decorated, regardless of the method's name.

   .. important::

      The decorated method's name MUST still start with ``auth_``

.. class:: AuthResult

   Contains the result of the Authentication Procedure.

   For more info, please see :class:`AuthResult`

.. class:: LoginPassword(login: bytes, password: bytes)

   A subclass of :class:`typing.NamedTuple` that holds the Authentication Data for the
   built-in ``LOGIN`` and ``PLAIN`` AUTH Mechanisms.

   It is to be used for Authentication purposes by :func:`Authenticator`

   For more information, please refer to the :ref:`auth` page.

.. class:: SMTP(handler, *, data_size_limit=33554432, enable_SMTPUTF8=False, \
   decode_data=False, hostname=None, ident=None, tls_context=None, \
   require_starttls=False, timeout=300, auth_required=False, \
   auth_require_tls=True, auth_exclude_mechanism=None, auth_callback=None, \
   authenticator=None, command_call_limit=None, \
   proxy_protocol_timeout=None, \
   loop=None)

   |
   | :part:`Parameters`

   .. py:attribute:: handler

      An instance of a :ref:`handler <handlers>` class that optionally can implement
      :ref:`hooks`.

   .. py:attribute:: data_size_limit
      :type: int
      :value: 33554432
      :noindex:

      The limit in number of bytes that is accepted for client SMTP commands.
      It is returned to ESMTP clients in the ``250-SIZE`` response.

   .. py:attribute:: enable_SMTPUTF8
      :type: bool
      :value: False
      :noindex:

      When ``True``, causes the ESMTP ``SMTPUTF8`` option to be returned to the client,
      and allows for UTF-8 content to be accepted, as defined in :rfc:`6531`.

   .. py:attribute:: decode_data
      :type: bool
      :value: False

      When ``True``, attempts to decode byte content in the ``DATA`` command,
      assigning the string value to the :ref:`envelope's <sessions_and_envelopes>`
      ``content`` attribute.

   .. py:attribute:: hostname
      :type: Optional[str]
      :value: None
      :noindex:

      The first part of the string returned in the ``220`` greeting response
      given to clients when they first connect to the server.
      If not given, the system's fully-qualified domain name is used.

   .. py:attribute:: ident
      :type: Optional[str]
      :value: None

      The second part of the string returned in the ``220`` greeting response
      that identifies the software name and version of the SMTP server
      to the client.
      If not given, a default Python SMTP ident is used.

   .. py:attribute:: tls_context
      :type: Optional[ssl.SSLContext]
      :value: None
      :noindex:

      An instance of :class:`ssl.SSLContext`.
      Providing this will enable support for ``STARTTLS`` ESMTP/LMTP option
      as defined in :rfc:`3207`.

      See :ref:`tls` for a more in-depth discussion on enabling ``STARTTLS``.

   .. py:attribute:: require_starttls
      :type: bool
      :value: False
      :noindex:

      If set to ``True``,
      then client must send ``STARTTLS`` before "restricted" ESMTP commands can be issued.

      "Restricted" ESMTP commands are all commands not in the set
      ``{"NOOP", "EHLO", "STARTTLS", "QUIT"}``

   .. py:attribute:: timeout
      :type: Union[int, float]
      :value: 300

      The number of seconds to wait between valid SMTP commands.
      After this time the connection will be closed by the server.

      The default is 300 seconds, as per :rfc:`2821`.

   .. py:attribute:: auth_required
      :type: bool
      :value: False

      Specifies whether SMTP Authentication is mandatory or not for the session.
      This impacts some SMTP commands such as ``HELP``, ``MAIL FROM``, ``RCPT TO``, and others.

   .. py:attribute:: auth_require_tls
      :type: bool
      :value: True

      Specifies whether ``STARTTLS`` must be used before AUTH exchange or not.

      If you set this to ``False`` then AUTH exchange can be done outside a TLS context,
      but the class will warn you of security considerations.

      Has no effect if :attr:`require_starttls` is ``True``.

   .. py:attribute:: auth_exclude_mechanism
      :type: Optional[Iterable[str]]
      :value: None

      Specifies which AUTH mechanisms to NOT use.

      This is the only way to completely disable the built-in AUTH mechanisms.

      See :ref:`auth` for a more in-depth discussion on AUTH mechanisms.

      .. versionadded:: 1.2.2

   .. py:attribute:: auth_callback
      :type: Callable[[str, bytes, bytes], bool]
      :value: login_always_fail

      A function that accepts three arguments:
      ``mechanism: str``, ``login: bytes``, and ``password: bytes``.
      Based on these args, the function must return a ``bool``
      that indicates whether the client's authentication attempt
      is accepted/successful or not.

      .. deprecated:: 1.3

         Use :attr:`authenticator` instead. This parameter **will be removed in version 2.0**.

   .. py:attribute:: authenticator
      :type: aiosmtpd.smtp.AuthenticatorType
      :value: None

      A function whose signature is identical to ``aiosmtpd.smtp.AuthenticatorType``.

      See :func:`Authenticator` for more information.

      .. versionadded:: 1.3

   .. py:attribute:: command_call_limit
      :type: Optional[Union[int, Dict[str, int]]]
      :value: None

      If not ``None`` sets the maximum time a certain SMTP command can be invoked.
      This is to prevent DoS due to malicious client connecting and never disconnecting,
      due to continual sending of SMTP commands to prevent timeout.

      The handling differs based on the type:

      .. highlights::

         If :attr:`command_call_limit` is of type ``int``,
         then the value is the call limit for ALL SMTP commands.

         If :attr:`command_call_limit` is of type ``dict``,
         it must be a ``Dict[str, int]``
         (the type of the values will be enforced).
         The keys will be the SMTP Command to set the limit for,
         the values will be the call limit per SMTP Command.

         .. highlights::

            A special key of ``"*"`` is used to set the 'default' call limit for commands not
            explicitly declared in :attr:`command_call_limit`.
            If ``"*"`` is not given,
            then the 'default' call limit will be set to ``aiosmtpd.smtp.CALL_LIMIT_DEFAULT``

      Other types -- or a ``Dict`` whose any value is not an ``int`` -- will raise a
      ``TypeError`` exception.

      Examples::

          # All commands have a limit of 10 calls
          SMTP(..., command_call_limit=10)

          # Commands RCPT and NOOP have their own limits; others have an implicit limit
          # of 20 (CALL_LIMIT_DEFAULT)
          SMTP(..., command_call_limit={"RCPT": 30, "NOOP": 5})

          # Commands RCPT and NOOP have their own limits; others set to 3
          SMTP(..., command_call_limit={"RCPT": 20, "NOOP": 10, "*": 3})

      If not given (or set to ``None``), then command call limit will not be enforced.
      **This will change in version 2.0**.

      .. versionadded:: 1.2.3

   .. py:attribute:: proxy_protocol_timeout
      :type: Optional[Union[int, float]]
      :value: None

      If given (not ``None``), activates support for **PROXY Protocol**.

      Please read the `PROXY Protocol Support documentation <ProxyProtocol>`_
      for a more in-depth explanation.

      If not given (or ``None``), disables support for PROXY Protocol.

      .. warning::

         When PROXY protocol support is activated,
         :class:`SMTP`'s behavior changes:
         It no longer immediately sends ``220`` greeting upon client connection,
         but instead it will wait for client to first send the PROXY protocol header.

         This is in accordance to the PROXY Protocol standard.

      .. versionadded:: 1.4

   .. py:attribute:: loop
      :noindex:

      The asyncio event loop to use.
      If not given, :meth:`asyncio.new_event_loop` will be called to create the event loop.

   |
   | :part:`Attributes & Methods`

   .. py:attribute:: line_length_limit

      The maximum line length, in octets (not characters; one UTF-8 character
      may result in more than one octet).
      Defaults to ``1001`` in compliance with
      :rfc:`RFC 5321 § 4.5.3.1.6 <5321#section-4.5.3.1.6>`

      .. attention::

         This sets the *stream limit* of :meth:`asyncio.StreamReader.readuntil`,
         thus impacting how the method works.
         In previous versions of aiosmtpd, the limit is not set.
         To return to the behavior of the previous versions, set
         :attr:`line_length_limit` to ``2**16`` *before* instantiating the
         :class:`SMTP` class.

   .. py:attribute:: local_part_limit

      The maximum lengh (in octets) of the local part of email addresses.

      :rfc:`RFC 5321 § 4.5.3.1.1 <5321#section-4.5.3.1.1>` specifies a maximum length of 64 octets,
      but this requirement is flexible and can be relaxed at the server's discretion
      (see :rfc:`§ 4.5.3.1 <5321#section-4.5.3.1>`).

      Setting this to `0` (the default) disables this limit completely.

   .. py:attribute:: AuthLoginUsernameChallenge

      A ``str`` containing the base64-encoded challenge to be sent as the first challenge
      in the ``AUTH LOGIN`` mechanism.

   .. py:attribute:: AuthLoginPasswordChallenge

      A ``str`` containing the base64-encoded challenge to be sent as the second challenge
      in the ``AUTH LOGIN`` mechanism.

   .. attribute:: event_handler

      The *handler* instance passed into the constructor.

   .. attribute:: data_size_limit

      The value of the *data_size_limit* argument passed into the constructor.

   .. attribute:: enable_SMTPUTF8

      The value of the *enable_SMTPUTF8* argument passed into the constructor.

   .. attribute:: hostname

      The ``220`` greeting hostname.  This will either be the value of the
      *hostname* argument passed into the constructor, or the system's fully
      qualified host name.

   .. attribute:: tls_context

      The value of the *tls_context* argument passed into the constructor.

   .. attribute:: require_starttls

      True if both the *tls_context* argument to the constructor was given
      **and** the *require_starttls* flag was True.

   .. attribute:: session

      The active :ref:`session <sessions_and_envelopes>` object, if there is
      one, otherwise None.

   .. attribute:: envelope

      The active :ref:`envelope <sessions_and_envelopes>` object, if there is
      one, otherwise None.

   .. attribute:: transport

      The active `asyncio transport`_ if there is one, otherwise None.

   .. attribute:: loop

      The event loop being used.  This will either be the given *loop*
      argument, or the new event loop that was created.

   .. attribute:: authenticated

      A flag that indicates whether authentication had succeeded.

   .. method:: _create_session()

      A method subclasses can override to return custom ``Session`` instances.

   .. method:: _create_envelope()

      A method subclasses can override to return custom ``Envelope`` instances.

   .. method:: push(status)
      :async:

      The method that subclasses and handlers should use to return statuses to
      SMTP clients.  This is a coroutine.  *status* can be a bytes object, but
      for convenience it is more likely to be a string.  If it's a string, it
      must be ASCII, unless *enable_SMTPUTF8* is True in which case it will be
      encoded as UTF-8.

   .. method:: smtp_<COMMAND>(arg)
      :async:

      Coroutine methods implementing the SMTP protocol commands.  For example,
      ``smtp_HELO()`` implements the SMTP ``HELO`` command.  Subclasses can
      override these, or add new command methods to implement custom
      extensions to the SMTP protocol.  *arg* is the rest of the SMTP command
      given by the client, or None if nothing but the command was given.

   .. py:method:: challenge_auth(\
      challenge, encode_to_b64=True, log_client_response=False\
      ) -> Union[_Missing, bytes]
      :async:

      :param challenge: The SMTP AUTH challenge to send to the client.
         May be in plaintext, may be in base64. Do NOT prefix with "334 "!
      :type challenge: AnyStr
      :param encode_to_b64: If true, will perform base64-encoding before sending
         the challenge to the client.
      :type encode_to_b64: bool
      :param log_client_response: If true, will perform logging of client response
      :type log_client_response: bool
      :return: Response from client (already base64-decoded) or ``MISSING`` (see description)

      This method will return ``MISSING`` if either of these scenarios happen:

         * client aborted the ``AUTH`` procedure by sending ``b"*"``, or
         * client response to the challenge cannot be base64-decoded.

      .. warning::

         Setting ``log_client_response=True`` might cause leakage of sensitive information!

         :boldital:`DO NOT TURN ON` UNLESS ABSOLUTELY NECESSARY!

.. _tls:

Enabling STARTTLS
=================

To enable :rfc:`3207` ``STARTTLS``,
you must supply the *tls_context* argument to the :class:`SMTP` class.
*tls_context* is created with the :func:`ssl.create_default_context` call
from the :mod:`ssl` module, as follows::

    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)

The context must be initialized with a server certificate, private key, and/or
intermediate CA certificate chain with the
:meth:`ssl.SSLContext.load_cert_chain` method.  This can be done with
separate files, or an all in one file.  Files must be in PEM format.

For example, if you wanted to use a self-signed certification for localhost,
which is easy to create but doesn't provide much security, you could use the
:manpage:`openssl(1)` command like so::

    $ openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem \
      -days 365 -nodes -subj '/CN=localhost'

and then in Python::

    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.load_cert_chain('cert.pem', 'key.pem')

Now pass the ``context`` object to the *tls_context* argument in the ``SMTP``
constructor.

Note that a number of exceptions can be generated by these methods, and by SSL
connections, which you must be prepared to handle.  Additional documentation
is available in Python's :mod:`ssl` module, and should be reviewed before use; in
particular if client authentication and/or advanced error handling is desired.

If *require_starttls* is ``True``, a TLS session must be initiated for the
server to respond to any commands other than ``EHLO``/``LHLO``, ``NOOP``,
``QUIT``, and ``STARTTLS``.

If *require_starttls* is ``False`` (the default), use of TLS is not required;
the client *may* upgrade the connection to TLS, or may use any supported
command over an insecure connection.

If *tls_context* is not supplied, the ``STARTTLS`` option will not be
advertised, and the ``STARTTLS`` command will not be accepted.
*require_starttls* is meaningless in this case, and should be set to
``False``.

.. _`asyncio transport`: https://docs.python.org/3/library/asyncio-protocol.html#asyncio-transport
.. _StreamReaderProtocol: https://docs.python.org/3/library/asyncio-stream.html#streamreaderprotocol
.. |StreamReaderProtocol| replace:: ``StreamReaderProtocol``
