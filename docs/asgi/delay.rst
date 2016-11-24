===============================================
Delay Protocol ASGI Message Format (Draft Spec)
===============================================

Protocol that allows any ASGI message to be delayed for a given number of milliseconds.

This simple protocol enables developers to schedule ASGI messages to be sent at a time in the future.
It can be used in conjunction with any other channel. This allows you do simple tasks
like scheduling an email to be sent later, to more complex tasks like testing latency in protocols.


Delay
'''''

Send a message to this channel to delay a message.

Channel: ``asgi.delay``

Keys:

    * ``channel``: Unicode string specifying the final destination channel for the message after the delay.

    * ``delay``: Positive integer specifying the number of milliseconds to delay the message.

    * ``content``: Dictionary of unicode string keys for the message content. This should meet the
content specifications for the specified destination channel.
