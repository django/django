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

Channels loads into Django as a pluggable app to bring WebSocket, long-poll HTTP,
task offloading and other asynchrony support to your code, using familiar Django
design patterns and a flexible underlying framework that lets you not only
customize behaviours but also write support for your own protocols and needs.

Documentation, installation and getting started instructions are at
https://channels.readthedocs.io

Channels is an official Django Project and as such has a deprecation policy.
Details about what's deprecated or pending deprecation for each release is in
the `release notes <http://channels.readthedocs.io/en/latest/releases/index.html>`_.

Support can be obtained either here via issues, or in the ``#django-channels``
channel on Freenode.

You can install channels from PyPI as the ``channels`` package.
You'll likely also want to ``asgi_redis`` to provide the Redis channel layer.
See our `installation <https://channels.readthedocs.io/en/latest/installation.html>`_
and `getting started <https://channels.readthedocs.io/en/latest/getting-started.html>`_ docs for more.

Dependencies
------------

All Channels projects currently support Python 2.7, 3.4 and 3.5. `channels` supports all released
Django versions, namely 1.8-1.10.


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

Django Core Shepherd: Andrew Godwin <andrew@aeracode.org>

Maintenance team:

* Andrew Godwin <andrew@aeracode.org>
* Steven Davidson
* Jeremy Spencer

If you are interested in joining the maintenance team, please
`read more about contributing <https://channels.readthedocs.io/en/latest/contributing.html>`_
and get in touch!


Other Projects
--------------

The Channels project is made up of several packages; the others are:

* `Daphne <https://github.com/django/daphne/>`_, the HTTP and Websocket termination server
* `asgiref <https://github.com/django/asgiref/>`_, the base ASGI library/memory backend
* `asgi_redis <https://github.com/django/asgi_redis/>`_, the Redis channel backend
* `asgi_ipc <https://github.com/django/asgi_ipc/>`_, the POSIX IPC channel backend
