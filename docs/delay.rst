Delay Server
============

Channels has an optional app ``channels.delay`` that implements the :doc:`ASGI Delay Protocol <asgi/delay>`.

The server is exposed through a custom management command ``rundelay`` which listens to
the `asgi.delay` channel for messages to delay.


Getting Started with Delay
--------------------------

To Install the app add `channels.delay` to `INSTALLED_APPS`::

    INSTALLED_APPS = (
        ...
        'channels',
        'channels.delay'
    )

Run `migrate` to create the tables

`python manage.py migrate`

Run the delay process to start processing messages

`python manage.py rundelay`

Now you're ready to start delaying messages.

Delaying Messages
-----------------

To delay a message by a fixed number of milliseconds use the `delay` parameter.

Here's an example::

    from channels import Channel

    delayed_message = {
        'channel': 'example_channel',
        'content': {'x': 1},
        'delay': 10 * 1000
    }
    # The message will be delayed 10 seconds by the server and then sent
    Channel('asgi.delay').send(delayed_message, immediately=True)
