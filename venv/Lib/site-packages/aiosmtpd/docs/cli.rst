.. _cli:

====================
 Command line usage
====================

``aiosmtpd`` provides a main entry point which can be used to run the server
on the command line.  There are two ways to run the server, depending on how
the package has been installed.

You can run the server by passing it to Python directly::

    $ python3 -m aiosmtpd -n

This starts a server on localhost, port 8025 without setting the uid to
'nobody' (i.e. because you aren't running it as root).  Once you've done that,
you can connect directly to the server using your favorite command line
protocol tool.  Type the ``QUIT`` command at the server once you see the
greeting::

    % telnet localhost 8025
    Trying 127.0.0.1...
    Connected to localhost.
    Escape character is '^]'.
    220 subdivisions Python SMTP ...
    QUIT
    221 Bye
    Connection closed by foreign host.

Of course, you could use Python's :mod:`smtplib` module, or any other SMTP client to
talk to the server.

Hit control-C at the server to stop it.

The entry point may also be installed as the ``aiosmtpd`` command, so this is
equivalent to the above ``python3`` invocation::

    $ aiosmtpd -n


Options
=======

Optional arguments are described in the :ref:`man page <manpage>` document.
