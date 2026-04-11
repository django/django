.. _handlers:

==========
 Handlers
==========

Handlers are classes which can implement :ref:`hook methods <hooks>` that get
called at various points in the SMTP dialog.

Handlers can also be named on the :ref:`command line <cli>`,
but if the class's constructor takes arguments,
you must define a ``@classmethod`` that converts the positional arguments and
returns a handler instance:

.. py:classmethod:: from_cli(cls, parser, *args)

    Convert the positional arguments, as strings passed in on the command
    line, into a handler instance.

    :boldital:`parser` is the
    :class:`~argparse.ArgumentParser` instance in use.

    If this method does not recognize the positional arguments passed in ``parser``,
    it can *optionally* call :meth:`parser.error <argparse.ArgumentParser.error>`
    with the error message.

If ``from_cli()`` is not defined, the handler can still be used on the command
line, but its constructor cannot accept arguments.


.. _hooks:

Handler Hooks
=============

Handlers can implement hooks that get called during the SMTP dialog, or in
exceptional cases.  These *handler hooks* are ALL called **asynchronously**
(i.e. they are coroutines).

All handler hooks are optional and default behaviors are
carried out by the :class:`SMTP` class when a hook is omitted,
so you only need to implement the ones you care about.

When a handler hook is defined,
it may have additional responsibilities as described below.


Common Arguments
----------------

All handler hooks will be called with at least three arguments:

.. py:attribute:: server
   :type: SMTP

   The ``SMTP`` server instance

.. py:attribute:: session
   :type: Session

   The :ref:`session instance <sessions_and_envelopes>` currently being handled, and

.. py:attribute:: envelope
   :type: Envelope

   The :ref:`envelope instance <sessions_and_envelopes>` of the current SMTP Transaction

Some handler hooks will receive additional arguments.


Supported Hooks
---------------

The following hooks are currently supported (in alphabetical order):

.. py:method:: handle_AUTH(server, session, envelope, args)
   :noindex:

   Called to handle ``AUTH`` command if you need custom AUTH behavior.

   For more information, please read the documentation for :ref:`auth`.

.. py:method:: handle_DATA(server, session, envelope) -> str
   :async:

   :return: Response message to be sent to the client

   Called during ``DATA`` after the entire message (`"SMTP content"
   <https://tools.ietf.org/html/rfc5321#section-2.3.9>`_ as described in
   RFC 5321) has been received.

   The content is available in ``envelope.original_content`` as type ``bytes``,
   normalized according to the transparency rules
   as defined in :rfc:`RFC 5321, §4.5.2 <5321#section-4.5.2>`.

   In addition, the ``envelope.content`` attribute will also contain the contents;
   the type depends on whether :class:`~aiosmtpd.smtp.SMTP` was instantiated with
   ``decode_data=False`` or ``decode_data=True``.
   See :attr:`Envelope.content` for more info.

.. py:method:: handle_EHLO(server, session, envelope, hostname, responses) -> List[str]
   :async:
   :noindex:

   :param hostname: The host name given by the client in the ``EHLO`` command
   :type hostname: str
   :return: Response message to be sent to the client

   This hook is called during ``EHLO``.

   This hook may push *additional* ``250-<command>`` responses to the client by doing
   ``await server.push(status)`` before returning ``"250 HELP"`` as the final response.

    .. important::

        If the handler sets the ``session.host_name`` attribute to a false-y value
        (or leave it as the default ``None`` value)
        it will signal later steps that ``HELO`` failed
        and need to be performed again.

        This also applies to the :meth:`handle_EHLO` hook below.

   .. deprecated:: 1.3

      Use the :meth:`5-argument form <handle_EHLO>` instead.
      Support for the 4-argument form **will be removed in version 2.0**

.. py:method:: handle_EHLO(server, session, envelope, hostname, responses) -> List[str]
   :async:

   :param hostname: The host name given by the client in the ``EHLO`` command
   :type hostname: str
   :param responses: The 'planned' responses to the ``EHLO`` command
      *including* the last ``250 HELP`` response.
   :type responses: List[str]
   :return: List of response messages to be sent to the client

   Called during ``EHLO``.

   The hook MUST return a list containing the desired responses.
   The returned list should end with ``250 HELP``

   This hook MUST also set the :attr:``session.host_name`` attribute.

   .. important::

      It is strongly recommended to not change element ``[0]`` of the list
      (containing the hostname of the SMTP server).

.. py:method:: handle_HELO(server, session, envelope, hostname) -> str
   :async:

   :param hostname: The host name given by client during ``HELO``
   :type hostname: str
   :return: Response message to be sent to the client

   This hook is called during ``HELO``.

   If implemented,
   this hook MUST also set the :attr:``session.host_name`` attribute
   before returning ``'250 {}'.format(server.hostname)`` as the status.

.. py:method:: handle_MAIL(server, session, envelope, address, mail_options) -> str
   :async:

   :param address: The parsed email address given by the client in the ``MAIL FROM`` command
   :type address: str
   :param mail_options: Additional ESMTP MAIL options provided by the client
   :type mail_options: List[str]
   :return: Response message to be sent to the client

   Called during ``MAIL FROM``.

   If implemented,
   this hook MUST also set the :attr:`envelope.mail_from` attribute
   and it MAY extend :attr:`envelope.mail_options` (which is always a Python list).

.. py:method:: handle_NOOP(server, session, envelope, arg) -> str
   :async:

   :param arg: All characters following the ``NOOP`` command
   :type arg: str
   :return: Response message to be sent to the client

   Called during ``NOOP``.

.. method:: handle_PROXY(server, session, envelope, proxy_data)
   :noindex:

   :param SMTP server: The :class:`SMTP` instance invoking the hook.
   :param Session session: The Session data *so far* (see Important note below)
   :param Envelope envelope: The Envelope data *so far* (see Important note below)
   :param ProxyData proxy_data: The result of parsing the PROXY Header
   :return: Truthy or Falsey, indicating if the connection may continue or not, respectively

   Called during PROXY Protocol Handshake.

   See :ref:`ProxyProtocol` for more information.

.. py:method:: handle_QUIT(server, session, envelope) -> str
   :async:

   :return: Response message to be sent to the client

   Called during ``QUIT``.

.. py:method:: handle_RCPT(server, session, envelope, address, rcpt_options) -> str
   :async:

   :param address: The parsed email address given by the client in the ``RCPT TO`` command
   :type address: str
   :param rcpt_options: Additional ESMTP RCPT options provided by the client
   :type rcpt_options: List[str]
   :return: Response message to be sent to the client

   Called during ``RCPT TO``.

   If implemented,
   this hook SHOULD append the address to ``envelope.rcpt_tos``
   and it MAY extend ``envelope.rcpt_options`` (both of which are always Python lists).

.. py:method:: handle_RSET(server, session, envelope) -> str
   :async:

   :return: Response message to be sent to the client

   Called during ``RSET``.

.. py:method:: handle_VRFY(server, session, envelope, address) -> str
   :async:

   :param address: The parsed email address given by the client in the ``VRFY`` command
   :type address: str
   :return: Response message to be sent to the client

   Called during ``VRFY``.

In addition to the SMTP command hooks, the following hooks can also be
implemented by handlers.  These have different APIs, and are called
**synchronously** (i.e. they are **not** coroutines).

.. py:method:: handle_STARTTLS(server, session, envelope)

    If implemented, and if SSL is supported, this method gets called
    during the TLS handshake phase of ``connection_made()``.  It should return
    True if the handshake succeeded, and False otherwise.

.. py:method:: handle_exception(error)

    If implemented, this method is called when any error occurs during the
    handling of a connection (e.g. if an ``smtp_<command>()`` method raises an
    exception).  The exception object is passed in.  This method *must* return
    a status string, such as ``'542 Internal server error'``.  If the method
    returns ``None`` or raises an exception, an exception will be logged, and a
    ``451`` code will be returned to the client.

    .. important::

        If client connection is lost, this handler will NOT be called.


Built-in handlers
=================

The following built-in handlers can be imported from :mod:`aiosmtpd.handlers`:

.. py:module:: aiosmtpd.handlers

.. py:class:: AsyncMessage

   A subclass of the :class:`~aiosmtpd.handlers.Message` handler,
   it is also an :term:`abstract base class` (it must be subclassed).

   The only difference with :class:`Message` is that
   :func:`handle_message()` is called *asynchronously*.

   This class **cannot** be used on the command line.

.. py:class:: Debugging

   This class prints the contents of the received messages to a given output stream.
   Programmatically, you can pass the stream to print to into the constructor.

   When specified on the command line,
   the (optional) positional argument
   must either be the string ``stdout`` or ``stderr``
   indicating which stream to use.
   Examples::

      aiosmtpd -c aiosmtpd.handlers.Debugging
      aiosmtpd -c aiosmtpd.handlers.Debugging stderr
      aiosmtpd -c aiosmtpd.handlers.Debugging stdout

.. py:class:: Mailbox

   A subclass of the :class:`~aiosmtpd.handlers.Message` handler
   which adds the messages to a :class:`~mailbox.Maildir`.
   See :ref:`mailboxhandler` for details.

   When specified on the command line,
   it accepts *exactly* one positional argument which is
   the ``maildir`` (i.e, directory where email messages will be stored.)
   Example::

      aiosmtpd -c aiosmtpd.handlers.Mailbox /home/myhome/Maildir

.. py:class:: Message

   This class is an :term:`abstract base class` (it must be subclassed)
   which converts the message content into a message instance.
   The class used to create these instances can be passed to the constructor,
   and defaults to :class:`email.message.Message`

   This message instance gains a few additional headers
   (e.g. :mailheader:`X-Peer`, :mailheader:`X-MailFrom`, and :mailheader:`X-RcptTo`).
   You can override this behavior by overriding the :func:`prepare_message` method,
   which takes a session and an envelope.
   The message instance is then passed to the handler's :func:`handle_message()` method.
   It is this method that must be implemented in the subclass.

   :func:`prepare_message()` and :func:`handle_message()`` are both called :boldital:`synchronously`.

   This class **cannot** be used on the command line.

.. py:class:: Proxy

   This class is a relatively simple SMTP proxy;
   it forwards messages to a remote host and port.
   The constructor takes the host name and port as positional arguments.

   This class **cannot** be used on the command line.

   .. important::

      Do not confuse this class with `the PROXY Protocol`_;
      they are two totally different things.

.. py:class:: Sink

   This class just consumes and discards messages.
   It's essentially the "no op" handler.

   It can be used on the command line, but accepts no positional arguments.
   Example::

      aiosmtpd -c aiosmtpd.handlers.Sink


.. _mailboxhandler:

The Mailbox Handler
===================

A convenient handler is the ``Mailbox`` handler, which stores incoming
messages into a maildir.

To try it, let's first prepare an :class:`~contextlib.ExitStack` to automatically
clean up after we finish:

    >>> from contextlib import ExitStack
    >>> from tempfile import TemporaryDirectory
    >>> # Clean up the temporary directory at the end
    >>> resources = ExitStack()
    >>> tempdir = resources.enter_context(TemporaryDirectory())

Then, prepare the controller:

    >>> import os
    >>> from aiosmtpd.controller import Controller
    >>> from aiosmtpd.handlers import Mailbox
    >>> #
    >>> maildir_path = os.path.join(tempdir, 'maildir')
    >>> controller = Controller(Mailbox(maildir_path))
    >>> controller.start()
    >>> # Arrange for the controller to be stopped at the end
    >>> ignore = resources.callback(controller.stop)

Now we can connect to the server and send it a message...

    >>> from smtplib import SMTP
    >>> client = SMTP(controller.hostname, controller.port)
    >>> client.sendmail('aperson@example.com', ['bperson@example.com'], """\
    ... From: Anne Person <anne@example.com>
    ... To: Bart Person <bart@example.com>
    ... Subject: A test
    ... Message-ID: <ant>
    ...
    ... Hi Bart, this is Anne.
    ... """)
    {}

...and a second message...

    >>> client.sendmail('cperson@example.com', ['dperson@example.com'], """\
    ... From: Cate Person <cate@example.com>
    ... To: Dave Person <dave@example.com>
    ... Subject: A test
    ... Message-ID: <bee>
    ...
    ... Hi Dave, this is Cate.
    ... """)
    {}

...and a third message.

    >>> client.sendmail('eperson@example.com', ['fperson@example.com'], """\
    ... From: Elle Person <elle@example.com>
    ... To: Fred Person <fred@example.com>
    ... Subject: A test
    ... Message-ID: <cat>
    ...
    ... Hi Fred, this is Elle.
    ... """)
    {}

We open up the mailbox again, and all three messages are waiting for us.

    >>> from mailbox import Maildir
    >>> from operator import itemgetter
    >>> mailbox = Maildir(maildir_path)
    >>> messages = sorted(mailbox, key=itemgetter('message-id'))
    >>> for message in messages:
    ...     print(message['Message-ID'], message['From'], message['To'])
    <ant> Anne Person <anne@example.com> Bart Person <bart@example.com>
    <bee> Cate Person <cate@example.com> Dave Person <dave@example.com>
    <cat> Elle Person <elle@example.com> Fred Person <fred@example.com>

Cleanup when we're done.

    >>> resources.close()


.. _`the PROXY Protocol`: https://www.haproxy.com/blog/haproxy/proxy-protocol/
