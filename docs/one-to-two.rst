What's new in Channels 2?
=========================

Channels 1 and Channels 2 are substantially different codebases, and the upgrade
is a major one. While we have attempted to keep things as familiar and
backwards-compatible as possible, major architectural shifts mean you will
likely need at least some code changes to upgrade.


Requirements
------------

First of all, Channels 2 is *Python 3.5 and up only*.

If you are using Python 2, or a previous version of Python 3, you cannot use
Channels 2 as it relies on the ``asyncio`` library and native Python async
support. This decision was a tough one, but ultimately Channels is a library
built around async functionality and so to not use these features would be
foolish in the long run.

Apart from that, there are no major changed requirements, and in fact Channels 2
deploys do not need separate worker and server processes and so should be easier
to manage.


Conceptual Changes
------------------

The fundamental layout and concepts of how Channels work have been significantly
changed; you'll need to understand how and why to help in upgrading.


Channel Layers and Processes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Channels 1 terminated HTTP and WebSocket connections in a separate process
to the one that ran Django code, and shuffled requests and events between them
over a cross-process *channel layer*, based on Redis or similar.

This not only meant that all request data had to be re-serialized over the
network, but that you needed to deploy and scale two separate sets of servers.
Channels 2 changes this by running the Django code in-process via a threadpool,
meaning that the network termination and application logic are combined, like
WSGI.


Application Instances
~~~~~~~~~~~~~~~~~~~~~

Because of this, all processing for a socket happens in the same process,
so ASGI applications are now instantiated once per socket and can use
local variables on ``self`` to store information, rather than the
``channel_session`` storage provided before (that is now gone entirely).

The channel layer is now only used to communicate between processes for things
like broadcast messaging - in particular, you can talk to other application
instances in direct events, rather than having to send directly to client sockets.

This means, for example, to broadcast a chat message, you would now send a
new-chat-message event to every application instance that needed it, and the application
code can handle that event, serialize the message down to the socket format,
and send it out (and apply things like multiplexing).


New Consumers
~~~~~~~~~~~~~

Because of these changes, the way consumers work has also significantly changed.
Channels 2 is now a turtles-all-the-way-down design; every aspect of the system
is designed as a valid ASGI application, including consumers and the routing
system.

The consumer base classes have changed, though if you were using the generic
consumers before, the way they work is broadly similar. However, the way that
user authentication, sessions, multiplexing, and similar features work has
changed.


Full Async
~~~~~~~~~~

Channels 2 is also built on a fundamental async foundation, and all servers
are actually running an asynchronous event loop and only jumping to synchronous
code when you interact with the Django view system or ORM. That means that
you, too, can write fully asychronous code if you wish.

It's not a requirement, but it's there if you need it. We also provide
convenience methods that let you jump between synchronous and asynchronous
worlds easily, with correct blocking semantics, so you can write most of
a consumer in an async style and then have one method that calls the Django ORM
run synchronously.


Removed Components
------------------

The binding framework has been removed entirely - it was a simplistic
implementation, and it being in the core package prevented people from exploring
their own solutions. It's likely similar concepts and APIs will appear in a
third-party (non-official-Django) package as an option for those who want them.


How to Upgrade
--------------

TODO
