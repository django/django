======================================
Email ASGI Message Format (Draft Spec)
======================================

.. warning::
  This is an incomplete draft.

Represents emails sent or received, likely over the SMTP protocol though that
is not directly specified here (a protocol server could in theory deliver
or receive email over HTTP to some external service, for example). Generally
adheres to RFC 5322 as much as possible.

As emails have no concept of a session and there's no trustable socket or
author model, the send and receive channels are both multi-listener, and
there is no ``reply_channel`` on any message type. If you want to persist
data across different email receive consumers, you should decide what part
of the message to use for an identifier (from address? to address? subject?
thread id?) and provide the persistence yourself.

The protocol server should handle encoding of headers by itself, understanding
RFC 1342 format headers and decoding them into unicode upon receive, and 
encoding outgoing emails similarly (preferably using UTF-8).


Receive
'''''''

Sent when an email is received.

Channel: ``email.receive``

Keys:

* ``from``: Unicode string specifying the return-path of the email as specified
  in the SMTP envelope. Will be ``None`` if no return path was provided.

* ``to``: List of unicode strings specifying the recipients requested in the
  SMTP envelope using ``RCPT TO`` commands. Will always contain at least one
  value.

* ``headers``: Dictionary of unicode string keys and unicode string values,
  containing all headers, including ``subject``. Header names are all forced
  to lower case. Header values are decoded from RFC 1342 if needed.

* ``content``: Contains a content object (see section below) representing the
  body of the message.

Note that ``from`` and ``to`` are extracted from the SMTP envelope, and not
from the headers inside the message; if you wish to get the header values,
you should use ``headers['from']`` and ``headers['to']``; they may be different.


Send
''''

Sends an email out via whatever transport 


Content objects
'''''''''''''''

Used in both send and receive to represent the tree structure of a MIME
multipart message tree.

A content object is always a dict, containing at least the key:

* ``content-type``: The unicode string of the content type for this section.

Multipart content objects also have:

* ``parts``: A list of content objects contained inside this multipart

Any other type of object has:

* ``body``: Byte string content of this part, decoded from any
  ``Content-Transfer-Encoding`` if one was specified as a MIME header.
