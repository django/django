Django Channels
===============

Channels is a project to make Django able to handle more than just plain
HTTP requests, including WebSockets and HTTP2, as well as the ability to
run code after a response has been sent for things like thumbnailing or
background calculation.

It's an easy-to-understand extension of the Django view model, and easy
to integrate and deploy.

First, read our :doc:`concepts` documentation to get an idea of the
data model underlying Channels and how they're used inside Django.

Then, read :doc:`getting-started` to see how to get up and running with
WebSockets with only 30 lines of code.

If you want a quick overview, start with :doc:`inshort`.

If you are interested in contributing, please read our :doc:`contributing` docs!


Projects
--------

Channels is comprised of five packages:

* `Channels <https://github.com/django/channels/>`_, the Django integration layer
* `Daphne <https://github.com/django/daphne/>`_, the HTTP and Websocket termination server
* `asgiref <https://github.com/django/asgiref/>`_, the base ASGI library/memory backend
* `asgi_redis <https://github.com/django/asgi_redis/>`_, the Redis channel backend
* `asgi_ipc <https://github.com/django/asgi_ipc/>`_, the POSIX IPC channel backend

This documentation covers the system as a whole; individual release notes and
instructions can be found in the individual repositories.


Topics
------

.. toctree::
   :maxdepth: 2

   inshort
   concepts
   installation
   getting-started
   deploying
   generics
   routing
   binding
   backends
   testing
   cross-compat
   reference
   faqs
   asgi
   community
   contributing
