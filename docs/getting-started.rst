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
    from channels.decorators import consumer
    from django.http import HttpResponse

    @consumer("django.wsgi.request")
    def http_consumer(response_channel, path, **kwargs):
        response = HttpResponse("Hello world! You asked for %s" % path)
        Channel(response_channel).send(**response.channel_encode())

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

    @consumer("django.websocket.connect")
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

    @consumer("django.websocket.keepalive")
    def ws_keepalive(channel, send_channel, **kwargs):
        Group("chat").add(send_channel)

Of course, this is exactly the same code as the ``connect`` handler, so let's
just combine them::

    @consumer("django.websocket.connect", "django.websocket.keepalive")
    def ws_add(channel, send_channel, **kwargs):
        Group("chat").add(send_channel)

And, even though channels will expire out, let's add an explicit ``disconnect``
handler to clean up as people disconnect (most channels will cleanly disconnect
and get this called)::

    @consumer("django.websocket.disconnect")
    def ws_disconnect(channel, send_channel, **kwargs):
        Group("chat").discard(send_channel)

Now, that's taken care of adding and removing WebSocket send channels for the
``chat`` group; all we need to do now is take care of message sending. For now,
we're not going to store a history of messages or anything and just replay
any message sent in to all connected clients. Here's all the code::

    from channels import Channel
    from channels.decorators import consumer

    @consumer("django.websocket.connect", "django.websocket.keepalive")
    def ws_add(channel, send_channel, **kwargs):
        Group("chat").add(send_channel)

    @consumer("django.websocket.receive")
    def ws_message(channel, send_channel, content, **kwargs):
        Group("chat").send(content=content)

    @consumer("django.websocket.disconnect")
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
just running a WSGI interface and a worker in two separate threads), but now we want
WebSocket support we'll need a separate process to keep things clean.

For simplicity, we'll use the database channel backend - this uses two tables
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
a worker for us, but WebSockets isn't compatible with WSGI and needs to run
separately.

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
copies of ``runworker`` you'll probably be able to see the tasks running
on different workers.

Authentication
--------------

Now, of course, a WebSocket solution is somewhat limited in scope without the
ability to live with the rest of your website - in particular, we want to make
sure we know what user we're talking to, in case we have things like private
chat channels (we don't want a solution where clients just ask for the right
channels, as anyone could change the code and just put in private channel names)

It can also save you having to manually make clients ask for what they want to
see; if I see you open a WebSocket to my "updates" endpoint, and I know which
user ID, I can just auto-add that channel to all the relevant groups (mentions
of that user, for example).

Handily, as WebSockets start off using the HTTP protocol, they have a lot of
familiar features, including a path, GET parameters, and cookies. Notably,
the cookies allow us to perform authentication using the same methods the
normal Django middleware does. Middleware only runs on requests to views,
however, and not on raw consumer calls; it's tailored to work with single
HTTP requests, and so we need a different solution to authenticate WebSockets.

In addition, we don't want the interface servers storing data or trying to run
authentication; they're meant to be simple, lean, fast processes without much
state, and so we'll need to do our authentication inside our consumer functions.

Fortunately, because Channels has standardised WebSocket event
:doc:`message-standards`, it ships with decorators that help you with
authentication, as well as using Django's session framework (which authentication
relies on).

All we need to do is add the ``websocket_auth`` decorator to our views,
and we'll get extra ``session`` and ``user`` keyword arguments we can use;
let's make one where users can only chat to people with the same first letter
of their username::

    from channels import Channel
    from channels.decorators import consumer, websocket_auth

    @consumer("django.websocket.connect", "django.websocket.keepalive")
    @websocket_auth
    def ws_add(channel, send_channel, user, **kwargs):
        Group("chat-%s" % user.username[0]).add(send_channel)

    @consumer("django.websocket.receive")
    @websocket_auth
    def ws_message(channel, send_channel, content, user, **kwargs):
        Group("chat-%s" % user.username[0]).send(content=content)

    @consumer("django.websocket.disconnect")
    @websocket_auth
    def ws_disconnect(channel, send_channel, user, **kwargs):
        Group("chat-%s" % user.username[0]).discard(send_channel)

(Note that we always end consumers with ``**kwargs``; this is to save us
from writing out all variables we might get sent and to allow forwards-compatibility
with any additions to the message formats in the future)

Persisting Data
---------------

Doing chatrooms by username first letter is a nice simple example, but it's
skirting around the real design pattern - persistent state for connections.
A user may open our chat site and select the chatroom to join themselves, so we
should let them send this request in the initial WebSocket connection,
check they're allowed to access it, and then remember which room a socket is
connected to when they send a message in so we know which group to send it to.

The ``send_channel`` is our unique pointer to the open WebSocket - as you've
seen, we do all our operations on it - but it's not something we can annotate
with data; it's just a simple string, and even if we hack around and set
attributes on it that's not going to carry over to other workers.

Instead, the solution is to persist information keyed by the send channel in
some other data store - sound familiar? This is what Django's session framework
does for HTTP requests, only there it uses cookies as the lookup key rather
than the ``send_channel``.

Now, as you saw above, you can use the ``websocket_auth`` decorator to get
both a ``user`` and a ``session`` variable in your message arguments - and,
indeed, there is a ``websocket_session`` decorator that will just give you
the ``session`` attribute.

However, that session is based on cookies, and so follows the user round the
site - it's great for information that should persist across all WebSocket and
HTTP connections, but not great for information that is specific to a single
WebSocket (such as "which chatroom should this socket be connected to"). For
this reason, Channels also provides a ``websocker_channel_session`` decorator,
which adds a ``channel_session`` attribute to the message; this works just like
the normal ``session`` attribute, and persists to the same storage, but varies
per-channel rather than per-cookie.

Let's use it now to build a chat server that expects you to pass a chatroom
name in the path of your WebSocket request (we'll ignore auth for now)::

    from channels import Channel
    from channels.decorators import consumer, websocket_channel_session

    @consumer("django.websocket.connect")
    @websocket_channel_session
    def ws_connect(channel, send_channel, path, channel_session, **kwargs):
        # Work out room name from path (ignore slashes)
        room = path.strip("/")
        # Save room in session and add us to the group
        channel_session['room'] = room
        Group("chat-%s" % room).add(send_channel)

    @consumer("django.websocket.keepalive")
    @websocket_channel_session
    def ws_add(channel, send_channel, channel_session, **kwargs):
        Group("chat-%s" % channel_session['room']).add(send_channel)

    @consumer("django.websocket.receive")
    @websocket_channel_session
    def ws_message(channel, send_channel, content, channel_session, **kwargs):
        Group("chat-%s" % channel_session['room']).send(content=content)

    @consumer("django.websocket.disconnect")
    @websocket_channel_session
    def ws_disconnect(channel, send_channel, channel_session, **kwargs):
        Group("chat-%s" % channel_session['room']).discard(send_channel)

If you play around with it from the console (or start building a simple
JavaScript chat client that appends received messages to a div), you'll see
that you can now request which chat room you want in the initial request. We
could easily add in the auth decorator here too and do an initial check in
``connect`` that the user had permission to join that chatroom.

Models
------

So far, we've just been taking incoming messages and rebroadcasting them to
other clients connected to the same group, but this isn't that great; really,
we want to persist messages to a datastore, and we'd probably like to be
able to inject messages into chatrooms from things other than WebSocket client
connections (perhaps a built-in bot, or server status messages).

Thankfully, we can just use Django's ORM to handle persistence of messages and
easily integrate the send into the save flow of the model, rather than the
message receive - that way, any new message saved will be broadcast to all
the appropriate clients, no matter where it's saved from.

We'll even take some performance considerations into account - We'll make our
own custom channel for new chat messages and move the model save and the chat
broadcast into that, meaning the sending process/consumer can move on
immediately and not spend time waiting for the database save and the
(slow on some backends) ``Group.send()`` call.

Let's see what that looks like, assuming we
have a ChatMessage model with ``message`` and ``room`` fields::

    from channels import Channel
    from channels.decorators import consumer, websocket_channel_session
    from .models import ChatMessage

    @consumer("chat-messages")
    def msg_consumer(room, message):
        # Save to model
        ChatMessage.objects.create(room=room, message=message)
        # Broadcast to listening sockets
        Group("chat-%s" % room).send(message)

    @consumer("django.websocket.connect")
    @websocket_channel_session
    def ws_connect(channel, send_channel, path, channel_session, **kwargs):
        # Work out room name from path (ignore slashes)
        room = path.strip("/")
        # Save room in session and add us to the group
        channel_session['room'] = room
        Group("chat-%s" % room).add(send_channel)

    @consumer("django.websocket.keepalive")
    @websocket_channel_session
    def ws_add(channel, send_channel, channel_session, **kwargs):
        Group("chat-%s" % channel_session['room']).add(send_channel)

    @consumer("django.websocket.receive")
    @websocket_channel_session
    def ws_message(channel, send_channel, content, channel_session, **kwargs):
        # Stick the message onto the processing queue
        Channel("chat-messages").send(room=channel_session['room'], message=content)

    @consumer("django.websocket.disconnect")
    @websocket_channel_session
    def ws_disconnect(channel, send_channel, channel_session, **kwargs):
        Group("chat-%s" % channel_session['room']).discard(send_channel)

Note that we could add messages onto the ``chat-messages`` channel from anywhere;
inside a View, inside another model's ``post_save`` signal, inside a management
command run via ``cron``. If we wanted to write a bot, too, we could put its
listening logic inside the ``chat-messages`` consumer, as every message would
pass through it.

Next Steps
----------

That covers the basics of using Channels; you've seen not only how to use basic
channels, but also seen how they integrate with WebSockets, how to use groups
to manage logical sets of channels, and how Django's session and authentication
systems easily integrate with WebSockets.

We recommend you read through the rest of the reference documentation to see
all of what Channels has to offer; in particular, you may want to look at
our :doc:`deployment` and :doc:`scaling` resources to get an idea of how to
design and run apps in production environments.
