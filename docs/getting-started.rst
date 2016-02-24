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
tie in the URL router and view subsystem to the default ``http.request``
channel if you don't provide another consumer that listens to it - remember,
only one consumer can listen to any given channel.

As a very basic example, let's write a consumer that overrides the built-in
handling and handles every HTTP request directly. This isn't something you'd
usually do in a project, but it's a good illustration of how Channels
actually underlies even core Django.

Make a new project, a new app, and put this in a ``consumers.py`` file in the app::

    from django.http import HttpResponse
    from channels.handler import AsgiHandler

    def http_consumer(message):
        # Make standard HTTP response - access ASGI path attribute directly
        response = HttpResponse("Hello world! You asked for %s" % message.content['path'])
        # Encode that response into message format (ASGI)
        for chunk in AsgiHandler.encode_response(response):
            message.reply_channel.send(chunk)

The most important thing to note here is that, because things we send in
messages must be JSON serializable, the request and response messages
are in a key-value format. You can read more about that format in the
:doc:`ASGI specification <asgi>`, but you don't need to worry about it too much;
just know that there's an ``AsgiRequest`` class that translates from ASGI into
Django request objects, and the ``AsgiHandler`` class handles translation of
``HttpResponse`` into ASGI messages, which you see used above. Usually,
Django's built-in code will do all this for you when you're using normal views.

Now, go into your ``settings.py`` file, and set up a channel layer; by default,
Django will just use an in-memory layer and route HTTP requests to the normal
URL resolver (we'll come back to channel layers in a minute).

For now, we want to override the *channel routing* so that, rather than going
to the URL resolver and our normal view stack, all HTTP requests go to our
custom consumer we wrote above. Here's what that looks like::

    # In settings.py
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.database_layer.DatabaseChannelLayer",
            "ROUTING": "myproject.routing.channel_routing",
        },
    }

    # In routing.py
    channel_routing = {
        "http.request": "myproject.myapp.consumers.http_consumer",
    }

As you can see, this is a little like Django's ``DATABASES`` setting; there are
named channel layers, with a default one called ``default``. Each layer
needs a class specified which powers it - we'll come to the options there later -
and a routing scheme, which points to a dict containing the routing settings.
It's recommended you call this ``routing.py`` and put it alongside ``urls.py``
in your project, but you can put it wherever you like, as long as the path is
correct.

If you start up ``python manage.py runserver`` and go to
``http://localhost:8000``, you'll see that, rather than a default Django page,
you get the Hello World response, so things are working. If you don't see
a response, check you :doc:`installed Channels correctly <installation>`.

Now, that's not very exciting - raw HTTP responses are something Django has
been able to do for a long time. Let's try some WebSockets, and make a basic
chat server!

Delete that consumer and its routing - we'll want the normal Django view layer to
serve HTTP requests from now on, which happens if you don't specify a consumer
for ``http.request`` - and make this WebSocket consumer instead::

    # In consumers.py
    from channels import Group

    def ws_add(message):
        Group("chat").add(message.reply_channel)

Hook it up to the ``websocket.connect`` channel like this::

    # In routing.py
    from myproject.myapp.consumers import ws_add

    channel_routing = {
        "websocket.connect": ws_add,
    }

Now, let's look at what this is doing. It's tied to the
``websocket.connect`` channel, which means that it'll get a message
whenever a new WebSocket connection is opened by a client.

When it gets that message, it takes the ``reply_channel`` attribute from it, which
is the unique response channel for that client, and adds it to the ``chat``
group, which means we can send messages to all connected chat clients.

Of course, if you've read through :doc:`concepts`, you'll know that channels
added to groups expire out if their messages expire (every channel layer has
a message expiry time, usually between 30 seconds and a few minutes, and it's
often configurable).

However, we'll still get disconnection messages most of the time when a
WebSocket disconnects; the expiry/garbage collection of group membership is
mostly there for when a disconnect message gets lost (channels are not
guaranteed delivery, just mostly reliable). Let's add an explicit disconnect
handler::

    # Connected to websocket.disconnect
    def ws_disconnect(message):
        Group("chat").discard(message.reply_channel)

.. _websocket-example:

Now, that's taken care of adding and removing WebSocket send channels for the
``chat`` group; all we need to do now is take care of message sending. For now,
we're not going to store a history of messages or anything and just replay
any message sent in to all connected clients. Here's all the code::

    # In consumers.py
    from channels import Group

    # Connected to websocket.connect
    def ws_add(message):
        Group("chat").add(message.reply_channel)

    # Connected to websocket.receive
    def ws_message(message):
        # ASGI WebSocket packet-received and send-packet message types
        # both have a "text" key for their textual data. 
        Group("chat").send({
            "text": "[user] %s" % message.content['text'],
        })

    # Connected to websocket.disconnect
    def ws_disconnect(message):
        Group("chat").discard(message.reply_channel)

And what our routing should look like in ``routing.py``::

    from myproject.myapp.consumers import ws_add, ws_message, ws_disconnect

    channel_routing = {
        "websocket.connect": ws_add,
        "websocket.receive": ws_message,
        "websocket.disconnect": ws_disconnect,
    }

With all that code, you now have a working set of a logic for a chat server.
All you need to do now is get it deployed, and as we'll see, that's not too
hard.

Running with Channels
---------------------

Because Channels takes Django into a multi-process model, you no longer run
everything in one process along with a WSGI server (of course, you're still
free to do that if you don't want to use Channels). Instead, you run one or
more *interface servers*, and one or more *worker servers*, connected by
that *channel layer* you configured earlier.

There are multiple kinds of "interface servers", and each one will service a
different type of request - one might do both WebSocket and HTTP requests, while
another might act as an SMS message gateway, for example.

These are separate from the "worker servers" where Django will run actual logic,
though, and so the *channel layer* transports the content of channels across
the network. In a production scenario, you'd usually run *worker servers*
as a separate cluster from the *interface servers*, though of course you
can run both as separate processes on one machine too.

By default, Django doesn't have a channel layer configured - it doesn't need one to run
normal WSGI requests, after all. As soon as you try to add some consumers,
though, you'll need to configure one.

In the example above we used the database channel layer implementation
as our default channel layer. This uses two tables
in the ``default`` database to do message handling, and isn't particularly fast but
requires no extra dependencies, so it's handy for development.
When you deploy to production, though, you'll want to
use a backend like the Redis backend that has much better throughput and
lower latency.

The second thing, once we have a networked channel backend set up, is to make
sure we're running an interface server that's capable of serving WebSockets.
Luckily, installing Channels will also install ``daphne``, an interface server
that can handle both HTTP and WebSockets at the same time, and then ties this
in to run when you run ``runserver`` - you shouldn't notice any difference
from the normal Django ``runserver``, though some of the options may be a little
different.

*(Under the hood, runserver is now running Daphne in one thread and a worker
with autoreload in another - it's basically a miniature version of a deployment,
but all in one process)*

Now, let's test our code. Open a browser and put the following into the
JavaScript console to open a WebSocket and send some data down it::

    // Note that the path doesn't matter right now; any WebSocket
    // connection gets bumped over to WebSocket consumers
    socket = new WebSocket("ws://127.0.0.1:8000/chat/");
    socket.onmessage = function(e) {
        alert(e.data);
    }
    socket.onopen = function() {
        socket.send("hello world");
    }

You should see an alert come back immediately saying "hello world" - your
message has round-tripped through the server and come back to trigger the alert.
You can open another tab and do the same there if you like, and both tabs will
receive the message and show an alert, as any incoming message is sent to the
``chat`` group by the ``ws_message`` consumer, and both your tabs will have
been put into the ``chat`` group when they connected.

Feel free to put some calls to ``print`` in your handler functions too, if you
like, so you can understand when they're called. You can also run separate
worker processes with ``manage.py runworker`` as well - if you do this, you
should see some of the consumers being handled in the ``runserver`` thread and
some in the separate worker process.

Persisting Data
---------------

Echoing messages is a nice simple example, but it's ignoring the real
need for a system like this - persistent state for connections.
Let's consider a basic chat site where a user requests a chat room upon initial
connection, as part of the query string (e.g. ``wss://host/websocket?room=abc``).

The ``reply_channel`` attribute you've seen before is our unique pointer to the
open WebSocket - because it varies between different clients, it's how we can
keep track of "who" a message is from. Remember, Channels is network-transparent
and can run on multiple workers, so you can't just store things locally in
global variables or similar.

Instead, the solution is to persist information keyed by the ``reply_channel`` in
some other data store - sound familiar? This is what Django's session framework
does for HTTP requests, using a cookie as the key. Wouldn't it be useful if
we could get a session using the ``reply_channel`` as a key?

Channels provides a ``channel_session`` decorator for this purpose - it
provides you with an attribute called ``message.channel_session`` that acts
just like a normal Django session.

Let's use it now to build a chat server that expects you to pass a chatroom
name in the path of your WebSocket request (we'll ignore auth for now - that's next)::

    # In consumers.py
    from channels import Group
    from channels.sessions import channel_session

    # Connected to websocket.connect
    @channel_session
    def ws_connect(message):
        # Work out room name from path (ignore slashes)
        room = message.content['path'].strip("/")
        # Save room in session and add us to the group
        message.channel_session['room'] = room
        Group("chat-%s" % room).add(message.reply_channel)

    # Connected to websocket.receive
    @channel_session
    def ws_message(message):
        Group("chat-%s" % message.channel_session['room']).send(message.content)

    # Connected to websocket.disconnect
    @channel_session
    def ws_disconnect(message):
        Group("chat-%s" % message.channel_session['room']).discard(message.reply_channel)

If you play around with it from the console (or start building a simple
JavaScript chat client that appends received messages to a div), you'll see
that you can set a chat room with the initial request.

Authentication
--------------

Now, of course, a WebSocket solution is somewhat limited in scope without the
ability to live with the rest of your website - in particular, we want to make
sure we know what user we're talking to, in case we have things like private
chat channels (we don't want a solution where clients just ask for the right
channels, as anyone could change the code and just put in private channel names)

It can also save you having to manually make clients ask for what they want to
see; if I see you open a WebSocket to my "updates" endpoint, and I know which
user you are, I can just auto-add that channel to all the relevant groups (mentions
of that user, for example).

Handily, as WebSockets start off using the HTTP protocol, they have a lot of
familiar features, including a path, GET parameters, and cookies. We'd like to
use these to hook into the familiar Django session and authentication systems;
after all, WebSockets are no good unless we can identify who they belong to
and do things securely.

In addition, we don't want the interface servers storing data or trying to run
authentication; they're meant to be simple, lean, fast processes without much
state, and so we'll need to do our authentication inside our consumer functions.

Fortunately, because Channels has an underlying spec for WebSockets and other
messages (:doc:`ASGI <asgi>`), it ships with decorators that help you with
both authentication and getting the underlying Django session (which is what
Django authentication relies on).

Channels can use Django sessions either from cookies (if you're running your
websocket server on the same port as your main site, using something like Daphne),
or from a ``session_key`` GET parameter, which is works if you want to keep
running your HTTP requests through a WSGI server and offload WebSockets to a
second server process on another port.

You get access to a user's normal Django session using the ``http_session``
decorator - that gives you a ``message.http_session`` attribute that behaves
just like ``request.session``. You can go one further and use ``http_session_user``
which will provide a ``message.user`` attribute as well as the session attribute.

Now, one thing to note is that you only get the detailed HTTP information
during the ``connect`` message of a WebSocket connection (you can read more
about that in the :doc:`ASGI spec <asgi>`) - this means we're not
wasting bandwidth sending the same information over the wire needlessly.

This also means we'll have to grab the user in the connection handler and then
store it in the session; thankfully, Channels ships with both a ``channel_session_user``
decorator that works like the ``http_session_user`` decorator we mentioned above but
loads the user from the *channel* session rather than the *HTTP* session,
and a function called ``transfer_user`` which replicates a user from one session
to another. Even better, it combines all of these into a ``channel_session_user_from_http``
decorator.

Bringing that all together, let's make a chat server where users can only
chat to people with the same first letter of their username::

    # In consumers.py
    from channels import Channel, Group
    from channels.sessions import channel_session
    from channels.auth import http_session_user, channel_session_user, transfer_user

    # Connected to websocket.connect
    @channel_session_user_from_http
    def ws_add(message):
        # Copy user from HTTP to channel session
        transfer_user(message.http_session, message.channel_session)
        # Add them to the right group
        Group("chat-%s" % message.user.username[0]).add(message.reply_channel)

    # Connected to websocket.receive
    @channel_session_user
    def ws_message(message):
        Group("chat-%s" % message.user.username[0]).send(message.content)

    # Connected to websocket.disconnect
    @channel_session_user
    def ws_disconnect(message):
        Group("chat-%s" % message.user.username[0]).discard(message.reply_channel)

If you're just using ``runserver`` (and so Daphne), you can just connect
and your cookies should transfer your auth over. If you were running WebSockets
on a separate port, you'd have to remember to provide the
Django session ID as part of the URL, like this::

    socket = new WebSocket("ws://127.0.0.1:9000/?session_key=abcdefg");

You can get the current session key in a template with ``{{ request.session.session_key }}``.
Note that Channels can't work with signed cookie sessions - since only HTTP
responses can set cookies, it needs a backend it can write to to separately
store state.


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

We'll even take some performance considerations into account: We'll make our
own custom channel for new chat messages and move the model save and the chat
broadcast into that, meaning the sending process/consumer can move on
immediately and not spend time waiting for the database save and the
(slow on some backends) ``Group.send()`` call.

Let's see what that looks like, assuming we
have a ChatMessage model with ``message`` and ``room`` fields::

    # In consumers.py
    from channels import Channel
    from channels.sessions import channel_session
    from .models import ChatMessage

    # Connected to chat-messages
    def msg_consumer(message):
        # Save to model
        ChatMessage.objects.create(
            room=message.content['room'],
            message=message.content['message'],
        )
        # Broadcast to listening sockets
        Group("chat-%s" % room).send({
            "content": message.content['message'],
        })

    # Connected to websocket.connect
    @channel_session
    def ws_connect(message):
        # Work out room name from path (ignore slashes)
        room = message.content['path'].strip("/")
        # Save room in session and add us to the group
        message.channel_session['room'] = room
        Group("chat-%s" % room).add(message.reply_channel)

    # Connected to websocket.receive
    @channel_session
    def ws_message(message):
        # Stick the message onto the processing queue
        Channel("chat-messages").send({
            "room": channel_session['room'],
            "message": content,
        })

    # Connected to websocket.disconnect
    @channel_session
    def ws_disconnect(message):
        Group("chat-%s" % message.channel_session['room']).discard(message.reply_channel)

Note that we could add messages onto the ``chat-messages`` channel from anywhere;
inside a View, inside another model's ``post_save`` signal, inside a management
command run via ``cron``. If we wanted to write a bot, too, we could put its
listening logic inside the ``chat-messages`` consumer, as every message would
pass through it.


Enforcing Ordering
------------------

There's one final concept we want to introduce you to before you go on to build
sites with Channels - consmer ordering

Because Channels is a distributed system that can have many workers, by default
it just processes messages in the order the workers get them off the queue.
It's entirely feasible for a WebSocket interface server to send out a ``connect``
and a ``receive`` message close enough together that a second worker will pick
up and start processing the ``receive`` message before the first worker has
finished processing the ``connect`` worker.

This is particularly annoying if you're storing things in the session in the
``connect`` consumer and trying to get them in the ``receive`` consumer - because
the ``connect`` consumer hasn't exited, its session hasn't saved. You'd get the
same effect if someone tried to request a view before the login view had finished
processing, but there you're not expecting that page to run after the login,
whereas you'd naturally expect ``receive`` to run after ``connect``.

Channels has a solution - the ``enforce_ordering`` decorator. All WebSocket 
messages contain an ``order`` key, and this decorator uses that to make sure that
messages are consumed in the right order, in one of two modes:

* Slight ordering: Message 0 (``websocket.connect``) is done first, all others
  are unordered

* Strict ordering: All messages are consumed strictly in sequence

The decorator uses ``channel_session`` to keep track of what numbered messages
have been processed, and if a worker tries to run a consumer on an out-of-order
message, it raises the ``ConsumeLater`` exception, which puts the message
back on the channel it came from and tells the worker to work on another message.

There's a cost to using ``enforce_ordering``, which is why it's an optional
decorator, and the cost is much greater in *strict* mode than it is in
*slight* mode. Generally you'll want to use *slight* mode for most session-based WebSocket
and other "continuous protocol" things. Here's an example, improving our
first-letter-of-username chat from earlier::

    # In consumers.py
    from channels import Channel, Group
    from channels.sessions import channel_session, enforce_ordering
    from channels.auth import http_session_user, channel_session_user, channel_session_user_from_http

    # Connected to websocket.connect
    @enforce_ordering(slight=True)
    @channel_session_user_from_http
    def ws_add(message):
        # Add them to the right group
        Group("chat-%s" % message.user.username[0]).add(message.reply_channel)

    # Connected to websocket.receive
    @enforce_ordering(slight=True)
    @channel_session_user
    def ws_message(message):
        Group("chat-%s" % message.user.username[0]).send(message.content)

    # Connected to websocket.disconnect
    @enforce_ordering(slight=True)
    @channel_session_user
    def ws_disconnect(message):
        Group("chat-%s" % message.user.username[0]).discard(message.reply_channel)

Slight ordering does mean that it's possible for a ``disconnect`` message to
get processed before a ``receive`` message, but that's fine in this case;
the client is disconnecting anyway, they don't care about those pending messages.

Strict ordering is the default as it's the most safe; to use it, just call
the decorator without arguments::

    @enforce_ordering
    def ws_message(message):
        ...

Generally, the performance (and safety) of your ordering is tied to your
session backend's performance. Make sure you choose session backend wisely
if you're going to rely heavily on ``enforce_ordering``.


Next Steps
----------

That covers the basics of using Channels; you've seen not only how to use basic
channels, but also seen how they integrate with WebSockets, how to use groups
to manage logical sets of channels, and how Django's session and authentication
systems easily integrate with WebSockets.

We recommend you read through the rest of the reference documentation to see
all of what Channels has to offer; in particular, you may want to look at
our :doc:`deploying` and :doc:`scaling` resources to get an idea of how to
design and run apps in production environments.
