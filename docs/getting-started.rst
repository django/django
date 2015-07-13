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
do any time. Let's try some WebSockets, and make a basic chat server!

Delete that consumer from above - we'll need the normal Django view layer to
serve templates later - and make this WebSocket consumer instead::

    @Channel.consumer("django.websocket.connect")
    def ws_connect(channel, send_channel, **kwargs):
        Group("chat").add(send_channel)

Now, let's look at what this is doing. It's tied to the
``django.websocket.connect`` channel, which means that it'll get a message
whenever a new WebSocket connection is opened by a client.

When it gets that message, it takes the ``send_channel`` key from it, which
is the unique response channel for that client, and adds it to the ``chat``
group, which means we can send messages to all connected chat clients.

Of course, if you've read through :doc:`concepts`, you'll know that channels
added to groups expire out after a while unless you keep renewing their
membership. This is because Channels is stateless; the worker processes
don't keep track of the open/close states of the potentially thousands of
connections you have open at any one time.

The solution to this is that the WebSocket interface servers will send
periodic "keepalive" messages on the ``django.websocket.keepalive`` channel,
so we can hook that up to re-add the channel (it's safe to add the channel to
a group it's already in - similarly, it's safe to discard a channel from a
group it's not in)::

    @Channel.consumer("django.websocket.keepalive")
    def ws_keepalive(channel, send_channel, **kwargs):
        Group("chat").add(send_channel)

Of course, this is exactly the same code as the ``connect`` handler, so let's
just combine them::

    @Channel.consumer("django.websocket.connect", "django.websocket.keepalive")
    def ws_add(channel, send_channel, **kwargs):
        Group("chat").add(send_channel)

And, even though channels will expire out, let's add an explicit ``disconnect``
handler to clean up as people disconnect (most channels will cleanly disconnect
and get this called)::

    @Channel.consumer("django.websocket.disconnect")
    def ws_disconnect(channel, send_channel, **kwargs):
        Group("chat").discard(send_channel)

Now, that's taken care of adding and removing WebSocket send channels for the
``chat`` group; all we need to do now is take care of message sending. For now,
we're not going to store a history of messages or anything and just replay
any message sent in to all connected clients. Here's all the code::

    @Channel.consumer("django.websocket.connect", "django.websocket.keepalive")
    def ws_add(channel, send_channel, **kwargs):
        Group("chat").add(send_channel)

    @Channel.consumer("django.websocket.receive")
    def ws_message(channel, send_channel, content, **kwargs):
        Group("chat").send(content=content)

    @Channel.consumer("django.websocket.disconnect")
    def ws_disconnect(channel, send_channel, **kwargs):
        Group("chat").discard(send_channel)

With all that code in your ``consumers.py`` file, you now have a working
set of a logic for a chat server. All you need to do now is get it deployed,
and as we'll see, that's not too hard.

Running with Channels
---------------------

Because Channels takes Django into a multi-process model, you can no longer
just run one process if you want to serve more than one protocol type.

There are multiple kinds of "interface server", and each one will service a
different type of request - one might do WSGI requests, one might handle
WebSockets, or you might have one that handles both.

These are separate from the "worker servers" where Django will run actual logic,
though, and so you'll need to configure a channel backend to allow the
channels to run over the network. By default, when you're using Django out of
the box, the channel backend is set to an in-memory one that only works in
process; this is enough to serve normal WSGI style requests (``runserver`` is
just running a WSGI interface and a worker in two threads), but now we want
WebSocket support we'll need a separate process to keep things clean.

For simplicity, we'll configure the database backend - this uses two tables
in the database to do message handling, and isn't particularly fast but
requires no extra dependencies. Put this in your ``settings.py`` file::

    CHANNEL_BACKENDS = {
        "default": {
            "BACKEND": "channels.backends.database.DatabaseChannelBackend",
        },
    }

As you can see, the format is quite similar to the ``DATABASES`` setting in
Django, but for this case much simpler, as it just uses the default database
(you can set which alias it uses with the ``DB_ALIAS`` key).

In production, we'd recommend you use something like the Redis channel backend;
you can :doc:`read about the backends <backends>` and see how to set them up
and their performance considerations if you wish.

The second thing, once we have a networked channel backend set up, is to make
sure we're running the WebSocket interface server. Even in development, we need
to do this; ``runserver`` will take care of normal Web requests and running
a worker for us, but WebSockets require an in-process async solution.

The easiest way to do this is to use the ``runwsserver`` management command
that ships with Django; just make sure you've installed the latest release
of ``autobahn`` first::

    pip install -U autobahn
    python manage.py runwsserver

Run that alongside ``runserver`` and you'll have two interface servers, a
worker thread, and the channel backend all connected and running. You can
even launch separate worker processes with ``runworker`` if you like (you'll
need at least one of those if you're not also running ``runserver``).

Now, just open a browser and put the following into the JavaScript console
to test your new code::

    socket = new WebSocket("ws://127.0.0.1:9000");
    socket.onmessage = function(e) {
        alert(e.data);
    }
    socket.send("hello world");

You should see an alert come back immediately saying "hello world" - your
message has round-tripped through the server and come back to trigger the alert.
You can open another tab and do the same there if you like, and both tabs will
receive the message and show an alert.

Feel free to put some calls to ``print`` in your handler functions too, if you
like, so you can understand when they're called. If you run three or four
copies of ``runworker``, too, you will probably be able to see the tasks running
on different workers.
