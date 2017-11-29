Django Channels
===============

Channels is a project that takes Django and extends its abilities beyond
HTTP - to handle WebSockets, chat protocols, IoT protocols, and more.

It does this by taking the core of Django and layering a fully asynchronous
layer underneath, running Django itself in a synchronous mode but handling
connections and sockets asynchronously, and giving you the choice to write
in either style.

To get started understanding how Channels works, read our :doc:`introduction`,
which will walk through how things work. If you're upgrading from Channels 1,
take a look at :doc:`one-to-two` to get an overview of the changes; things
are substantially different.

.. warning::
   This is incomplete documentation for an upcoming release. If you are looking
   for documentation for the stable release of Channels, please select "stable"
   in the bottom-left corner of the page.


Projects
--------

Channels is comprised of several packages:

* `Channels <https://github.com/django/channels/>`_, the Django integration layer
* `Daphne <https://github.com/django/daphne/>`_, the HTTP and Websocket termination server
* `asgiref <https://github.com/django/asgiref/>`_, the base ASGI library/memory backend
* `asgi_redis <https://github.com/django/asgi_redis/>`_, the Redis channel backend
* `asgi_rabbitmq <https://github.com/proofit404/asgi_rabbitmq/>`_, the RabbitMQ channel backend
* `asgi_ipc <https://github.com/django/asgi_ipc/>`_, the POSIX IPC channel backend

This documentation covers the system as a whole; individual release notes and
instructions can be found in the individual repositories.


Topics
------

.. toctree::
   :maxdepth: 2

   introduction
   installation
   deploying
   one-to-two
   javascript
   channel_layer_spec
   community
   contributing
   releases/index
