====================================
UDP ASGI Message Format (Draft Spec)
====================================

Raw UDP is specified here as it is a datagram-based, unordered and unreliable
protocol, which neatly maps to the underlying message abstraction. It is not
expected that many applications would use the low-level protocol, but it may
be useful for some.

While it might seem odd to have reply channels for UDP as it is a stateless
protocol, replies need to come from the same server as the messages were
sent to, so the reply channel here ensures that reply packets from an ASGI
stack do not come from a different protocol server to the one you sent the
initial packet to.


Receive
'''''''

Sent when a UDP datagram is received.

Channel: ``udp.receive``

Keys:

* ``reply_channel``: Channel name for sending data, starts with ``udp.send!``

* ``data``: Byte string of UDP datagram payload.

* ``client``: List of ``[host, port]`` where ``host`` is a unicode string of the
  remote host's IPv4 or IPv6 address, and ``port`` is the remote port as an
  integer.

* ``server``: List of ``[host, port]`` where ``host`` is the listening address
  for this server as a unicode string, and ``port`` is the integer listening port.
  Optional, defaults to ``None``.


Send
''''

Sent to send out a UDP datagram to a client.

Channel: ``udp.send!``

Keys:

* ``data``: Byte string of UDP datagram payload.
