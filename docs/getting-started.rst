Getting Started
===============

(If you haven't yet, make sure you :doc:`install Channels <installation>`)

Now, let's get to writing some consumers. If you've not read it already,
you should read :doc:`concepts`, as it covers the basic description of what
channels and groups are, and lays out some of the important implementation
patterns and caveats.

First Consumers
---------------

Now, by default, Django will run things through Channels but it will also
tie in the URL router and view subsystem to the default ``django.wsgi.request``
channel if you don't provide another consumer that listens to it - remember,
only one consumer can listen to any given channel.

As a very basic example, let's write a consumer that overrides the built-in
handling and handles every HTTP request directly. Make a new project, a new
app, and put this in a ``consumers.py`` file in the app::

    from channels import Channel
    from django.http import HttpResponse

    @Channel.consumer("django.wsgi.request")
    def http_consumer(response_channel, path, **kwargs):
        response = HttpResponse("Hello world! You asked for %s" % path)
        Channel(response_channel).send(response.channel_encode())

The most important thing to note here is that, because things we send in
messages must be JSON-serialisable, the request and response messages
are in a key-value format. There are ``channel_decode()`` and
``channel_encode()`` methods on both Django's request and response classes,
but here we just take two of the request variables directly as keyword
arguments for simplicity.

If you start up ``python manage.py runserver`` and go to
``http://localhost:8000``, you'll see that, rather than a default Django page,
you get the Hello World response, so things are working. If you don't see
a response, check you :doc:`installed Channels correctly <installation>`.

Now, that's not very exciting - raw HTTP responses are something Django can
do any time. Let's try some WebSockets!

Delete that consumer from above - we'll need the normal Django view layer to
serve templates later - and make this WebSocket consumer instead::

    # todo
