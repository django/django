django-channels
===============

This is a work-in-progress code branch of Django implemented as a third-party
app, which aims to bring some asynchrony to Django and expand the options
for code beyond the request-response model.

The proposal itself is detailed in `a very long Gist <https://gist.github.com/andrewgodwin/b3f826a879eb84a70625>`_
and there is discussion about it on `django-developers <https://groups.google.com/forum/#!forum/django-developers>`_.

If you wish to use this in your own project, there's basic integration
instructions below - but be warned! This is not stable and may change massively 
at any time!

Integration
-----------

Make sure you're running Django 1.8. This doesn't work with 1.7 (yet?)

If you want to use WebSockets (and that's kind of the point) you'll need
``autobahn`` and ``twisted`` packages too. Python 3/asyncio support coming soon.

``pip install django-channels`` and then add ``channels`` to the **TOP**
of your ``INSTALLED_APPS`` list (if it is not at the top you won't get the
new runserver command).

You now have a ``runserver`` that actually runs a WSGI interface and a
worker in two different threads, ``runworker`` to run separate workers,
and ``runwsserver`` to run a Twisted-based WebSocket server.

You should place consumers in either your ``views.py`` or a ``consumers.py``.
Here's an example of WebSocket consumers for basic chat::

    import redis
    from channels import Channel

    redis_conn = redis.Redis("localhost", 6379)

    @Channel.consumer("django.websockets.connect")
    def ws_connect(path, send_channel, **kwargs):
        redis_conn.sadd("chatroom", send_channel)

    @Channel.consumer("django.websocket.receive")
    def ws_receive(channel, send_channel, content, binary, **kwargs):
        # Ignore binary messages
        if binary:
            return
        # Re-dispatch message
        for channel in redis_conn.smembers("chatroom"):
            Channel(channel).send(content=content, binary=False)

    @Channel.consumer("django.websocket.disconnect")
    def ws_disconnect(channel, send_channel, **kwargs):
        redis_conn.srem("chatroom", send_channel)
        # NOTE: this does not clean up server crash disconnects,
        # you'd want expiring keys here in real life.

Alternately, you can just push some code outside of a normal view into a worker
thread::

    
    from django.shortcuts import render
    from channels import Channel

    def my_view(request):
        # Dispatch a task to run outside the req/response cycle
        Channel("a_task_channel").send(value=3)
        # Return a response
        return render(request, "test.html")

    @Channel.consumer("a_task_channel")
    def some_task(channel, value):
        print "My value was %s from channel %s" % (value, channel)

Limitations
-----------

The ``runserver`` this command provides currently does not support static
media serving, streamed responses or autoreloading.

In addition, this library is a preview and basically might do anything to your
code, or change drastically at any time.

If you have opinions, please provide feedback via the appropriate
`django-developers thread <https://groups.google.com/forum/#!forum/django-developers>`_.
