.. _controller:

====================
 Programmatic usage
====================

If you already have an `asyncio event loop`_, you can `create a server`_ using
the :class:`~aiosmtpd.smtp.SMTP` class as the *protocol factory*, and then run the loop forever.
If you need to pass arguments to the ``SMTP`` constructor, use
:func:`functools.partial` or write your own wrapper function.  You might also
want to add a signal handler so that the loop can be stopped, say when you hit
control-C.

It's probably easier to use a *threaded controller* which runs the SMTP server in a
separate thread with a dedicated event loop.  The controller provides useful
and reliable ``start`` and ``stop`` semantics so that the foreground thread
doesn't block.  Among other use cases, this makes it convenient to spin up an
SMTP server for unit tests.

In both cases, you need to pass a :ref:`handler <handlers>` to the ``SMTP``
constructor.  Handlers respond to events that you care about during the SMTP
dialog.

.. important::

  Consider running the controller in a separate Python process (e.g., using the
  :mod:`multiprocessing` module) if you don't want your main Python process to be
  blocked when aiosmtpd is handling extra-large emails.


Using the controller
====================

.. _tcpserver:

TCP-based Server
----------------

The :class:`~aiosmtpd.controller.Controller` class creates a TCP-based server,
listening on an Internet endpoint (i.e., ``ip_address:port`` pair).

Say you want to receive email for ``example.com`` and print incoming mail data
to the console.  Start by implementing a handler as follows:

.. doctest::

    >>> import asyncio
    >>> class ExampleHandler:
    ...     async def handle_RCPT(self, server, session, envelope, address, rcpt_options):
    ...         if not address.endswith('@example.com'):
    ...             return '550 not relaying to that domain'
    ...         envelope.rcpt_tos.append(address)
    ...         return '250 OK'
    ...
    ...     async def handle_DATA(self, server, session, envelope):
    ...         print('Message from %s' % envelope.mail_from)
    ...         print('Message for %s' % envelope.rcpt_tos)
    ...         print('Message data:\n')
    ...         for ln in envelope.content.decode('utf8', errors='replace').splitlines():
    ...             print(f'> {ln}'.strip())
    ...         print()
    ...         print('End of message')
    ...         return '250 Message accepted for delivery'

Pass an instance of your ``ExampleHandler`` class to the ``Controller``, and
then start it:

.. doctest::

    >>> from aiosmtpd.controller import Controller
    >>> controller = Controller(ExampleHandler())
    >>> controller.start()

The SMTP thread might run into errors during its setup phase; to catch this
the main thread will timeout when waiting for the SMTP server to become ready.
By default the timeout is set to 1 second but can be changed either by using
the :envvar:`AIOSMTPD_CONTROLLER_TIMEOUT` environment variable or by passing a
different ``ready_timeout`` duration to the Controller's constructor.

Connect to the server and send a message, which then gets printed by
``ExampleHandler``:

.. doctest::

    >>> from smtplib import SMTP as Client
    >>> client = Client(controller.hostname, controller.port)
    >>> r = client.sendmail('a@example.com', ['b@example.com'], """\
    ... From: Anne Person <anne@example.com>
    ... To: Bart Person <bart@example.com>
    ... Subject: A test
    ... Message-ID: <ant>
    ...
    ... Hi Bart, this is Anne.
    ... """)
    Message from a@example.com
    Message for ['b@example.com']
    Message data:
    <BLANKLINE>
    > From: Anne Person <anne@example.com>
    > To: Bart Person <bart@example.com>
    > Subject: A test
    > Message-ID: <ant>
    >
    > Hi Bart, this is Anne.
    <BLANKLINE>
    End of message

You'll notice that at the end of the ``DATA`` command, your handler's
:meth:`handle_DATA` method was called.  The sender, recipients, and message
contents were taken from the envelope, and printed at the console.  The
handler methods also returns a successful status message.

The ``ExampleHandler`` class also implements a :meth:`handle_RCPT` method.  This
gets called after the ``RCPT TO`` command is sanity checked.  The method
ensures that all recipients are local to the ``@example.com`` domain,
returning an error status if not.  It is the handler's responsibility to add
valid recipients to the ``rcpt_tos`` attribute of the envelope and to return a
successful status.

Thus, if we try to send a message to a recipient not inside ``example.com``,
it is rejected:

.. doctest::

    >>> client.sendmail('aperson@example.com', ['cperson@example.net'], """\
    ... From: Anne Person <anne@example.com>
    ... To: Chris Person <chris@example.net>
    ... Subject: Another test
    ... Message-ID: <another>
    ...
    ... Hi Chris, this is Anne.
    ... """)
    Traceback (most recent call last):
    ...
    smtplib.SMTPRecipientsRefused: {'cperson@example.net': (550, b'not relaying to that domain')}

When you're done with the SMTP server, stop it via the controller.

.. doctest::

    >>> controller.stop()

The server is guaranteed to be stopped.

.. doctest::

    >>> client.connect(controller.hostname, controller.port)
    Traceback (most recent call last):
    ...
    ConnectionRefusedError: ...

There are a number of built-in :ref:`handler classes <handlers>` that you can
use to do some common tasks, and it's easy to write your own handler.  For a
full overview of the methods that handler classes may implement, see the
section on :ref:`handler hooks <hooks>`.


Unix Socket-based Server
------------------------

The :class:`~aiosmtpd.controller.UnixSocketController` class creates a server listening to
a Unix Socket (i.e., a special file that can act as a 'pipe' for interprocess
communication).

Usage is identical with the example described in the :ref:`tcpserver` section above,
with some differences:

**Rather than specifying a hostname:port to listen on, you specify the Socket's filepath:**

.. doctest:: unix_socket
    :skipif: in_win32 or in_cygwin

    >>> from aiosmtpd.controller import UnixSocketController
    >>> from aiosmtpd.handlers import Sink
    >>> controller = UnixSocketController(Sink(), unix_socket="smtp_socket~")
    >>> controller.start()

.. warning::

    Do not exceed the Operating System limit for the length of the socket file path.
    On Linux, the limit is 108 characters. On BSD OSes, it's 104 characters.

**Rather than connecting to IP:port, you connect to the Socket file.**
Python's :class:`smtplib.SMTP` class sadly cannot connect to a Unix Socket,
so we need to handle it on our own here:

.. doctest:: unix_socket
    :skipif: in_win32 or in_cygwin

    >>> import socket
    >>> sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    >>> sock.connect("smtp_socket~")
    >>> sock.recv(1024)
    b'220 ...'

Try sending something, don't forget to end with ``"\r\n"``:

.. doctest:: unix_socket
    :skipif: in_win32 or in_cygwin

    >>> sock.send(b"HELO example.org\r\n")
    18
    >>> sock.recv(1024)
    b'250 ...'

And close everything when done:

.. doctest:: unix_socket
    :skipif: in_win32 or in_cygwin

    >>> sock.send(b"QUIT\r\n")
    6
    >>> sock.recv(1024)
    b'221 Bye...'
    >>> sock.close()
    >>> controller.stop()


.. _unthreaded:

Unthreaded Controllers
----------------------

In addition to the **threaded** controllers described above,
``aiosmtpd`` also provides the following **UNthreaded** controllers:

* :class:`UnthreadedController` -- the unthreaded version of :class:`Controller`
* :class:`UnixSocketUnthreadedController` -- the unthreaded version of :class:`UnixSocketController`

These classes are considered *advanced* classes,
because you'll have to manage the event loop yourself.

For example, to start an unthreaded controller,
you'll have to do something similar to this:

.. doctest:: unthreaded

    >>> import asyncio
    >>> loop = asyncio.new_event_loop()
    >>> asyncio.set_event_loop(loop)
    >>> from aiosmtpd.controller import UnthreadedController
    >>> from aiosmtpd.handlers import Sink
    >>> controller = UnthreadedController(Sink(), loop=loop)
    >>> controller.begin()

Note that unlike the threaded counterparts,
the method used to start the controller is named ``begin()``.
And unlike the method in the threaded version,
``begin()`` does NOT start the asyncio event loop;
you'll have to start it yourself.

For the purposes of trying this,
let's create a thread and have it run the asyncio event loop;
we'll also schedule an autostop so it won't hang:

.. doctest:: unthreaded

    >>> def runner():
    ...     # Set the delay to something long enough so you have time
    ...     # to do some testing
    ...     loop.call_later(3.0, loop.stop)
    ...     loop.run_forever()
    >>> import threading
    >>> thread = threading.Thread(target=runner)
    >>> thread.daemon = True
    >>> thread.start()
    >>> import time
    >>> time.sleep(0.1)  # Allow the loop to begin

At this point in time, the server would be listening:

.. doctest:: unthreaded

    >>> from smtplib import SMTP as Client
    >>> client = Client(controller.hostname, controller.port)
    >>> client.helo("example.com")
    (250, ...)
    >>> client.quit()
    (221, b'Bye')

The complex thing will be to end it;
that is why we're marking these classes as "advanced".

For our example here,
since we have created an "autostop loop",
all we have to do is wait for the runner thread to end:

.. doctest:: unthreaded

    >>> thread.join()
    >>> loop.is_running()
    False

We still need to do some cleanup to fully release the bound port.
Since the loop has ended, we can simply call the :meth:`end` method:

.. doctest:: unthreaded

    >>> controller.end()

If you want to end the controller *but* keep the loop running,
you'll have to do it like this::

    loop.call_soon_threadsafe(controller.end)
    # If you want to ensure that controller has stopped, you can wait() here:
    controller.ended.wait(10.0)  # Optional

You must remember to cleanup the canceled tasks yourself.
We have provided a convenience method,
:meth:`~aiosmtpd.controller.BaseController.cancel_tasks`::

    # Will also stop the loop!
    loop.call_soon_threadsafe(controller.cancel_tasks)

(If you invoke ``cancel_tasks`` with the parameter ``stop_loop=False``,
then loop will NOT be stopped.
That is a much too-advanced topic and we will not discuss it further in this documentation.)

The Unix Socket variant, ``UnixSocketUnthreadedController``, works in the same way.
The difference is only in how to access the server, i.e., through a Unix Socket instead of TCP/IP.
We'll leave out the details for you to figure it out yourself.


.. _enablesmtputf8:

Enabling SMTPUTF8
=================

It's very common to want to enable the ``SMTPUTF8`` ESMTP option, therefore
this is the default for the ``Controller`` constructor.  For backward
compatibility reasons, this is *not* the default for the ``SMTP`` class
though.  If you want to disable this in the ``Controller``, you can pass this
argument into the constructor:

.. doctest::

    >>> from aiosmtpd.handlers import Sink
    >>> controller = Controller(Sink(), enable_SMTPUTF8=False)
    >>> controller.start()
    >>>
    >>> client = Client(controller.hostname, controller.port)
    >>> code, message = client.ehlo('me')
    >>> code
    250

The EHLO response does not include the ``SMTPUTF8`` ESMTP option.

.. doctest::

    >>> lines = message.decode('utf-8').splitlines()
    >>> # Don't print the server host name line, since that's variable.
    >>> for line in lines[1:]:
    ...     print(line)
    SIZE 33554432
    8BITMIME
    HELP

Stop the controller if we're done experimenting:

.. doctest::

    >>> controller.stop()


Controller API
==============

.. py:module:: aiosmtpd.controller


.. py:data:: DEFAULT_READY_TIMEOUT
    :type: float
    :value: 5.0


.. py:function:: get_localhost()

   :return: The numeric address of the loopback interface; ``"::1"`` if IPv6 is supported,
      ``"127.0.0.1"`` if IPv6 is not supported.
   :rtype: Literal["::1", "127.0.0.1"]


.. class:: IP6_IS

   .. py:attribute:: NO
      :type: set[int]

      Contains constants from :mod:`errno` that will be raised by :meth:`socket.socket.bind`
      if IPv6 is NOT available on the system.

   .. py:attribute:: YES
      :type: set[int]

      Contains constants from :mod:`errno` that will be raised by :meth:`socket.socket.bind`
      if IPv6 IS available on the system.

   .. note::

        You can customize the contents of these attributes by adding/removing from them,
        in case the behavior does not align with your expectations *and*
        you cannot wait for a patch to be merged.


.. class:: BaseController(\
    handler, \
    loop=None, \
    *, \
    ssl_context=None, \
    server_hostname=None, \
    server_kwargs=None, \
    **SMTP_parameters, \
    )

    This **Abstract Base Class** defines parameters, attributes, and methods common between
    all concrete controller classes.

    :param handler: Handler object
    :param loop: The asyncio event loop in which the server will run.
        If not given, :func:`asyncio.new_event_loop` will be called to create the event loop.
    :type loop: asyncio.AbstractEventLoop
    :param ssl_context: SSL Context to wrap the socket in.
        Will be passed-through to  :meth:`~asyncio.loop.create_server` method
    :type ssl_context: ssl.SSLContext
    :param server_hostname: Server's hostname,
        will be passed-through as ``hostname`` parameter of :class:`~aiosmtpd.smtp.SMTP`
    :type server_hostname: Optional[str]
    :param server_kwargs: *(DEPRECATED)* A dict that will be passed-through as keyword
        arguments of :class:`~aiosmtpd.smtp.SMTP`.
        This is DEPRECATED; please use ``**SMTP_parameters`` instead.
    :type server_kwargs: dict
    :param SMTP_parameters: Optional keyword arguments that
        will be passed-through as keyword arguments of :class:`~aiosmtpd.smtp.SMTP`

    |
    | :part:`Attributes`

    .. attribute:: handler
        :noindex:

        The instance of the event *handler* passed to the constructor.

    .. attribute:: loop
        :noindex:

        The event loop being used.

    .. attribute:: server

        This is the server instance returned by
        :meth:`_create_server` after the server has started.

        You can retrieve the :class:`~socket.socket` objects the server is listening on
        from the ``server.sockets`` attribute.

    .. py:attribute:: smtpd
        :type: aiosmtpd.smtp.SMTP

        The server instance (of class SMTP) created by :meth:`factory` after
        the controller is started.

    |
    | :part:`Methods`

    .. method:: factory() -> aiosmtpd.smtp.SMTP

        You can override this method to create custom instances of
        the :class:`~aiosmtpd.smtp.SMTP` class being controlled.

        By default, this creates an ``SMTP`` instance,
        passing in your handler and setting flags from the :attr:`**SMTP_Parameters` parameter.

        Examples of why you would want to override this method include
        creating an :ref:`LMTP <LMTP>` server instance instead of the standard ``SMTP`` server.

    .. py:method:: cancel_tasks(stop_loop=True)

        :param stop_loop: If ``True``, stops the loop before canceling tasks.
        :type stop_loop: bool

        This is a convenience class that will stop the loop &
        cancel all asyncio tasks for you.


.. class:: Controller(\
    handler, \
    hostname=None, \
    port=8025, \
    loop=None, \
    *, \
    ready_timeout=DEFAULT_READY_TIMEOUT, \
    ssl_context=None, \
    server_hostname=None, \
    server_kwargs=None, \
    **SMTP_parameters)

    A concrete subclass of :class:`BaseController` that provides
    a threaded, INET listener.

    :param hostname: Will be given to the event loop's :meth:`~asyncio.loop.create_server` method
       as the ``host`` parameter, with a slight processing (see below)
    :type hostname: Optional[str]
    :param port: Will be passed-through to :meth:`~asyncio.loop.create_server` method
    :type port: int
    :param ready_timeout: How long to wait until server starts.
        The :envvar:`AIOSMTPD_CONTROLLER_TIMEOUT` takes precedence over this parameter.
        See :attr:`ready_timeout` for more information.
    :type ready_timeout: float

    Other parameters are defined in the :class:`BaseController` class.

    The ``hostname`` parameter will be passed to the event loop's
    :meth:`~asyncio.loop.create_server` method as the ``host`` parameter,
    :boldital:`except` ``None`` (default) will be translated to ``::1``.

      * To bind `dual-stack`_ locally, use ``localhost``.
      * To bind `dual-stack`_ on all interfaces, use ``""`` (empty string).

    .. important::

       The ``hostname`` parameter does NOT get passed through to the SMTP instance;
       if you want to give the SMTP instance a custom hostname
       (e.g., for use in HELO/EHLO greeting),
       you must pass it through the :attr:`server_hostname` parameter.

    Explicitly defined SMTP keyword arguments will override keyword arguments of the
    same names defined in the (deprecated) ``server_kwargs`` argument.

    .. doctest:: controller_kwargs

         >>> from aiosmtpd.controller import Controller
         >>> from aiosmtpd.handlers import Sink
         >>> controller = Controller(
         ...     Sink(), timeout=200, server_kwargs=dict(timeout=400)
         ... )
         >>> controller.SMTP_kwargs["timeout"]
         200

    Finally, setting the ``ssl_context`` parameter will switch the protocol to ``SMTPS`` mode,
    implying unconditional encryption of the connection,
    and preventing the use of the ``STARTTLS`` mechanism.

    Actual behavior depends on the subclass's implementation.

    |
    | :part:`Attributes`

    In addition to those provided by :class:`BaseController`,
    this class provides the following:

    .. attribute:: hostname: str
                   port: int

        The values of the *hostname* and *port* arguments.

    .. attribute:: ready_timeout
        :type: float

        The timeout value used to wait for the server to start.

        This will either be the value of
        the :envvar:`AIOSMTPD_CONTROLLER_TIMEOUT` environment variable (converted to float),
        or the :attr:`ready_timeout` parameter.

        Setting this to a high value will NOT slow down controller startup,
        because it's a timeout limit rather than a sleep delay.
        However, you may want to reduce the default value to something 'just enough'
        so you don't have to wait too long for an exception, if problem arises.

        If this timeout is breached, a :class:`TimeoutError` exception will be raised.

    |
    | :part:`Methods`

    In addition to those provided by :class:`BaseController`,
    this class provides the following:

    .. method:: start() -> None

        :raises TimeoutError: if the server takes too long to get ready,
            exceeding the ``ready_timeout`` parameter.
        :raises RuntimeError: if an unrecognized & unhandled error happened,
            resulting in non-creation of a server object
            (:attr:`smtpd` remains ``None``)

        Start the server in the subthread.
        The subthread is always a :class:`daemon thread <threading.Thread>`
        (i.e., we always set ``thread.daemon=True``).

        Exceptions can be raised
        if the server does not start within :attr:`ready_timeout` seconds,
        or if any other exception occurs in :meth:`~BaseController.factory`
        while creating the server.

        .. important::

           If :meth:`start` raises an Exception,
           cleanup is not performed automatically,
           to support deep inspection post-exception (if you wish to do so.)
           Cleanup must still be performed manually by calling :meth:`stop`

           For example::

               # Assume SomeController is a concrete subclass of BaseThreadedController
               controller = SomeController(handler)
               try:
                   controller.start()
               except ...:
                   ... exception handling and/or inspection ...
               finally:
                   controller.stop()

    .. method:: stop(no_assert=False) -> None

        :param no_assert: If ``True``, skip the assertion step so an ``AssertionError`` will
            not be raised if thread had not been started successfully.
        :type no_assert: bool

        :raises AssertionError: if this method is called before
            :meth:`start` is called successfully *AND* ``no_assert=False``

        Stop the server and the event loop, and cancel all tasks
        via :meth:`~BaseController.cancel_tasks`.


.. class:: UnixSocketController(\
    handler, \
    unix_socket, \
    loop=None, \
    *, \
    ready_timeout=DEFAULT_READY_TIMEOUT, \
    ssl_context=None, \
    server_hostname=None, \
    **SMTP_parameters)

    A concrete subclass of :class:`BaseController` that provides
    a threaded, Unix Socket listener.

    :param unix_socket: Socket file,
        will be passed-through to :meth:`asyncio.loop.create_unix_server`
    :type unix_socket: Union[str, pathlib.Path]

    For the other parameters, see the description under :class:`Controller`

    |
    | :part:`Attributes`

    .. py:attribute:: unix_socket
        :type: str

        The stringified version of the ``unix_socket`` parameter

    Other attributes (except ``hostname`` and ``port``) are identical to :class:`Controller`
    and thus are not repeated nor explained here.

    |
    | :part:`Methods`

    All methods are identical to :class:`Controller`
    and thus are not repeated nor explained here.


.. class:: UnthreadedController(\
    handler, \
    hostname=None, \
    port=8025, \
    loop=None, \
    *, \
    ssl_context=None, \
    server_hostname=None, \
    server_kwargs=None, \
    **SMTP_parameters)

    .. versionadded:: 1.5.0

    A concrete subclass of :class:`BaseController` that provides
    an UNthreaded, INET listener.

    Parameters are identical to the :class:`Controller` class.

    |
    | :part:`Attributes`

    Attributes are identical to the :class:`Controller` class with one addition:

    .. py:attribute:: ended
        :type: threading.Event

        An ``Event`` that can be ``.wait()``-ed when ending the controller.
        Please see the :ref:`Unthreaded Controllers <unthreaded>` section for more info.

    |
    | :part:`Methods`

    In addition to those provided by :class:`BaseController`,
    this class provides the following:

    .. py:method:: begin

        Initializes the server task and insert it into the asyncio event loop.

        .. note::

            The SMTP class itself will only be initialized upon first connection
            to the server task.

    .. py:method:: finalize
        :async:

        Perform orderly closing of the server listener.
        If you need to close the server from a non-async function,
        you can use the :meth:`~UnthreadedController.end` method instead.

        Upon completion of this method, the :attr:`ended` attribute will be ``set()``.

    .. py:method:: end

        This is a convenience method that will asynchronously invoke the
        :meth:`finalize` method.
        This method non-async, and thus is callable from non-async functions.

        .. note::

            If the asyncio event loop has been stopped,
            then it is safe to invoke this method directly.
            Otherwise, it is recommended to invoke this method
            using the :meth:`~asyncio.loop.call_soon_threadsafe` method.


.. class:: UnixSocketUnthreadedController(\
    handler, \
    unix_socket, \
    loop=None, \
    *, \
    ssl_context=None, \
    server_hostname=None,\
    server_kwargs=None, \
    **SMTP_parameters)

    .. versionadded:: 1.5.0

    A concrete subclass of :class:`BaseController` that provides
    an UNthreaded, Unix Socket listener.

    Parameters are identical to the :class:`UnixSocketController` class.

    |
    | :part:`Attributes`

    Attributes are identical to the :class:`UnixSocketController` class,
    with the following addition:

    .. py:attribute:: ended
        :type: threading.Event

        An ``Event`` that can be ``.wait()``-ed when ending the controller.
        Please see the :ref:`Unthreaded Controllers <unthreaded>` section for more info.

    |
    | :part:`Methods`

    Methods are identical to the :class:`UnthreadedController` class.


.. _`asyncio event loop`: https://docs.python.org/3/library/asyncio-eventloop.html
.. _`create a server`: https://docs.python.org/3/library/asyncio-eventloop.html#asyncio.AbstractEventLoop.create_server
.. _dual-stack: https://en.wikipedia.org/wiki/IPv6#Dual-stack_IP_implementation
