Django Channels
===============

.. image:: https://api.travis-ci.org/django/channels.svg
    :target: https://travis-ci.org/django/channels

.. image:: https://readthedocs.org/projects/channels/badge/?version=latest
    :target: https://channels.readthedocs.io/en/latest/?badge=latest

.. image:: https://img.shields.io/pypi/v/channels.svg
    :target: https://pypi.python.org/pypi/channels

.. image:: https://img.shields.io/pypi/l/channels.svg
    :target: https://pypi.python.org/pypi/channels

Channels augments Django to bring WebSocket, long-poll HTTP,
task offloading and other async support to your code, using familiar Django
design patterns and a flexible underlying framework that lets you not only
customize behaviours but also write support for your own protocols and needs.

Documentation, installation and getting started instructions are at
https://channels.readthedocs.io

Channels is an official Django Project and as such has a deprecation policy.
Details about what's deprecated or pending deprecation for each release is in
the `release notes <http://channels.readthedocs.io/en/latest/releases/index.html>`_.

Support can be obtained through several locations - see our
`support docs <https://channels.readthedocs.io/en/latest/support.html>`_ for more.

You can install channels from PyPI as the ``channels`` package.
See our `installation <https://channels.readthedocs.io/en/latest/installation.html>`_
and `tutorial <https://channels.readthedocs.io/en/latest/tutorial/index.html>`_ docs for more.

Dependencies
------------

All Channels projects currently support 3.5 and up. ``channels`` is compatible
with Django 1.11, 2.1, and 2.2.


Contributing
------------

To learn more about contributing, please `read our contributing docs <https://channels.readthedocs.io/en/latest/contributing.html>`_.


Maintenance and Security
------------------------

To report security issues, please contact security@djangoproject.com. For GPG
signatures and more security process information, see
https://docs.djangoproject.com/en/dev/internals/security/.

To report bugs or request new features, please open a new GitHub issue. For
larger discussions, please post to the
`django-developers mailing list <https://groups.google.com/d/forum/django-developers>`_.

Maintenance is overseen by Carlton Gibson with help from others. It is a
best-effort basis - we unfortunately can only dedicate guaranteed time to fixing
security holes.

If you are interested in joining the maintenance team, please
`read more about contributing <https://channels.readthedocs.io/en/latest/contributing.html>`_
and get in touch!


Other Projects
--------------

The Channels project is made up of several packages; the others are:

* `Daphne <https://github.com/django/daphne/>`_, the HTTP and Websocket termination server
* `channels_redis <https://github.com/django/channels_redis/>`_, the Redis channel backend
* `asgiref <https://github.com/django/asgiref/>`_, the base ASGI library/memory backend
