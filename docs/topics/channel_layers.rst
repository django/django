Channel Layers
==============

Channel layers allow you to talk between different instances of an application.
They're a useful part of making a distributed realtime application if you don't
want to have to shuttle all of your messages or events through a database.

Additionally, they can also be used in combination with a worker process
to make a basic task queue or to offload tasks - read more in
:doc:`/topics/worker`.

Channels does not ship with any channel layers you can use out of the box, as
each one depends on a different way of transporting data across a network. We
would recommend you use ``asgi_redis``, which is an offical Django-maintained
layer that uses Redis as a transport and what we'll focus the examples on here.


Configuration
-------------

TODO


Groups
------

TODO - mention manual version too
