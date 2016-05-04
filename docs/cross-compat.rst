Cross-Compatibility
===================

Channels is being released as both a third-party app for Django 1.8 and 1.9,
and being integrated into Django in 1.10. Both of these implementations are
very similar, and code for one will work on the other with minimal changes.

The only difference between the two is the import paths. Mostly, where you
imported from ``channels`` for the third-party app, you instead import from
``django.channels`` for the built-in solution.

For example::

    from channels import Channel
    from channels.auth import channel_session_user

Becomes::

    from django.channels import Channel
    from django.channels.auth import channel_session_user

There are a few exceptions to this rule, where classes were moved to other parts
of Django in 1.10 that made more sense:

* ``channels.tests.ChannelTestCase`` is found under ``django.test.channels.ChannelTestCase``
* ``channels.handler`` is moved to ``django.core.handlers.asgi``
* ``channels.staticfiles`` is moved to ``django.contrib.staticfiles.consumers``
* The ``runserver`` and ``runworker`` commands are in ``django.core.management.commands``


Writing third-party apps against Channels
-----------------------------------------

If you're writing a third-party app that is designed to work with both the
``channels`` third-party app as well as ``django.channels``, we suggest you use
a try-except pattern for imports, like this::

    try:
        from django.channels import Channel
    except ImportError:
        from channels import Channel

All the objects in both versions act the same way, they simply are located
on different import paths. There should be no need to change logic.
