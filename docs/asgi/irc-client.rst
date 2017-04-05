===========================================
IRC Client ASGI Message Format (Draft Spec)
===========================================

.. warning::
  This is an incomplete draft.

Represents communication with an external IRC server as a client. It is possible
to have multiple clients hooked into the same channel layer talking to different
servers, which is why the reply channel is not a fixed name;
a client will provide it with every incoming action and upon connection.

The reply channel must stay consistent throughout the client's lifetime, so it
can be used as a unique identifier for the client.


Connected
---------

Sent when the client has established a connection to an IRC server.

Channel: ``irc-client.connect``

Keys:

* ``reply_channel``: The channel to send messages or actions to the server over.

* ``server``: A two-item list of ``[hostname, port]``, where hostname is a
  unicode string of the server hostname or IP address, and port is the integer port.


Joined
------

Sent when the client has joined an IRC channel.

Channel: ``irc-client.join``

Keys:

* ``reply_channel``: The channel to send messages or actions to the server over.

* ``channel``: Unicode string name of the IRC channel joined


Receive
-------

Represents either a message, action or notice being received from the server.

Channel: ``irc-client.receive``

Keys:

* ``reply_channel``: The channel to send messages or actions to the server over.

* ``type``: Unicode string, one of ``message``, ``action`` or ``notice``.

* ``user``: IRC user as a unicode string (including host portion)

* ``channel``: IRC channel name as a unicode string

* ``body``: Message, action or notice content as a unicode string


Control
-------

Sent to control the IRC client.

Channel: Specified by the server as ``reply_channel`` in other types

Keys:

* ``channel``: IRC channel name to act on as a unicode string

* ``type``: Unicode string, one of ``join``, ``part``, ``message`` or
  ``action``.

* ``body``: If type is ``message`` or ``action``, the body of the message
  or the action as a unicode string.
