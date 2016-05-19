Frequently Asked Questions
==========================

Why are you doing this rather than just using Tornado/gevent/asyncio/etc.?
--------------------------------------------------------------------------

They're kind of solving different problems. Tornado, gevent and other
in-process async solutions are a way of making a single Python process act
asynchronously - doing other things while a HTTP request is going on, or
juggling hundreds of incoming connections without blocking on a single one.

Channels is different - all the code you write for consumers runs synchronously.
You can do all the blocking filesystem calls and CPU-bound tasks you like
and all you'll do is block the one worker you're running on; the other
worker processes will just keep on going and handling other messages.

This is partially because Django is all written in a synchronous manner, and
rewriting it to all be asynchronous would be a near-impossible task, but also
because we believe that normal developers should not have to write
asynchronous-friendly code. It's really easy to shoot yourself in the foot;
do a tight loop without yielding in the middle, or access a file that happens
to be on a slow NFS share, and you've just blocked the entire process.

Channels still uses asynchronous code, but it confines it to the interface
layer - the processes that serve HTTP, WebSocket and other requests. These do
indeed use asynchronous frameworks (currently, asyncio and Twisted) to handle
managing all the concurrent connections, but they're also fixed pieces of code;
as an end developer, you'll likely never have to touch them.

All of your work can be with standard Python libraries and patterns and the
only thing you need to look out for is worker contention - if you flood your
workers with infinite loops, of course they'll all stop working, but that's
better than a single thread of execution stopping the entire site.


Why aren't you using node/go/etc. to proxy to Django?
-----------------------------------------------------

There are a couple of solutions where you can use a more "async-friendly"
language (or Python framework) to bridge things like WebSockets to Django -
terminate them in (say) a Node process, and then bridge it to Django using
either a reverse proxy model, or Redis signalling, or some other mechanism.

The thing is, Channels actually makes it easier to do this if you wish. The
key part of Channels is introducing a standardised way to run event-triggered
pieces of code, and a standardised way to route messages via named channels
that hits the right balance between flexibility and simplicity.

While our interface servers are written in Python, there's nothing stopping
you from writing an interface server in another language, providing it follows
the same serialisation standards for HTTP/WebSocket/etc. messages. In fact,
we may ship an alternative server implementation ourselves at some point.


Why isn't there guaranteed delivery/a retry mechanism?
------------------------------------------------------

Channels' design is such that anything is allowed to fail - a consumer can
error and not send replies, the channel layer can restart and drop a few messages,
a dogpile can happen and a few incoming clients get rejected.

This is because designing a system that was fully guaranteed, end-to-end, would
result in something with incredibly low throughput, and almost no problem needs
that level of guarantee. If you want some level of guarantee, you can build on
top of what Channels provides and add it in (for example, use a database to
mark things that need to be cleaned up and resend messages if they aren't after
a while, or make idempotent consumers and over-send messages rather than
under-send).

That said, it's a good way to design a system to presume any part of it can
fail, and design for detection and recovery of that state, rather than hanging
your entire livelihood on a system working perfectly as designed. Channels
takes this idea and uses it to provide a high-throughput solution that is
mostly reliable, rather than a low-throughput one that is *nearly* completely
reliable.


Can I run HTTP requests/service calls/etc. in parallel from Django without blocking?
------------------------------------------------------------------------------------

Not directly - Channels only allows a consumer function to listen to channels
at the start, which is what kicks it off; you can't send tasks off on channels
to other consumers and then *wait on the result*. You can send them off and keep
going, but you cannot ever block waiting on a channel in a consumer, as otherwise
you'd hit deadlocks, livelocks, and similar issues.

This is partially a design feature - this falls into the class of "difficult
async concepts that it's easy to shoot yourself in the foot with" - but also
to keep the underlying channels implementation simple. By not allowing this sort
of blocking, we can have specifications for channel layers that allows horizontal
scaling and sharding.

What you can do is:

* Dispatch a whole load of tasks to run later in the background and then finish
  your current task - for example, dispatching an avatar thumbnailing task in
  the avatar upload view, then returning a "we got it!" HTTP response.

* Pass details along to the other task about how to continue, in particular
  a channel name linked to another consumer that will finish the job, or
  IDs or other details of the data (remember, message contents are just a dict
  you can put stuff into). For example, you might have a generic image fetching
  task for a variety of models that should fetch an image, store it, and pass
  the resultant ID and the ID of the object you're attaching it to onto a different
  channel depending on the model - you'd pass the next channel name and the
  ID of the target object in the message, and then the consumer could send
  a new message onto that channel name when it's done.

* Have interface servers that perform requests or slow tasks (remember, interface
  servers are the specialist code which *is* written to be highly asynchronous)
  and then send their results onto a channel when finished. Again, you can't wait
  around inside a consumer and block on the results, but you can provide another
  consumer on a new channel that will do the second half.


How do I associate data with incoming connections?
--------------------------------------------------

Channels provides full integration with Django's session and auth system for its
WebSockets support, as well as per-websocket sessions for persisting data, so
you can easily persist data on a per-connection or per-user basis.

You can also provide your own solution if you wish, keyed off of ``message.reply_channel``,
which is the unique channel representing the connection, but remember that
whatever you store in must be **network-transparent** - storing things in a
global variable won't work outside of development.


How do I talk to Channels from my non-Django application?
---------------------------------------------------------

If you have an external server or script you want to talk to Channels, you have
a few choices:

* If it's a Python program, and you've made an ``asgi.py`` file for your project
  (see :doc:`deploying`), you can import the channel layer directly as
  ``yourproject.asgi.channel_layer`` and call ``send()`` and ``receive_many()``
  on it directly. See the :doc:`ASGI spec <asgi>` for the API the channel layer
  presents.

* If you just need to send messages in when events happen, you can make a
  management command that calls ``Channel("namehere").send({...})``
  so your external program can just call
  ``manage.py send_custom_event`` (or similar) to send a message. Remember, you
  can send onto channels from any code in your project.

* If neither of these work, you'll have to communicate with Django over
  HTTP, WebSocket, or another protocol that your project talks, as normal.


Are channels Python 2, 3 or 2+3?
--------------------------------

Django-channels and all of its dependencies are compatible with Python 2.7,
3.3, and higher. This includes the parts of Twisted that some of the Channels
packages (like daphne) use.
