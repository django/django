Integration Plan
================

*DRAFT VERSION - NOT FINAL*

Channels is to become a built-in feature for Django 1.10, but in order to aid adoption and to encourage community usage and support, it will also be backported to Django 1.8 and 1.9 via a third-party app.

Obviously, we want to do this with as little code duplication as is sensible, so this document outlines the plan of how Channels will be integrated into Django and how it will be importable and usable from the supported versions.

Separate Components
-------------------

The major step in code reuse will be developing the main interface server as a separate project still released under the Django umbrella (current codename is ``daphne``).

This piece of software will likely have its own release cycle but still be developed and maintained by Django as part of the core project, and will speak HTTP, WebSockets, and likely HTTP2 natively. It will be designed to be used either directly exposed to the Internet or behind a reverse proxy that serves static files, much like gunicorn or uwsgi would be deployed.

This would then be supplemented by two implementations of the "worker" end of the Channels stack - one native in Django 1.10, and one as a third-party app for earlier Django versions. They would act very similarly, and there will be some code duplication between them, but the 1.10 version should be cleaner and faster as there's no need to re-route around the existing Django internals (though it can be done, as the current third-party app approach shows).

All three components would need to share the channel backend implementations - there is still an unanswered question here about if those should be separate packages, or somehow bundled into the implementations themselves.

Preserving Simplicity
---------------------

A main goal of the channels project is to keep the ability to just download and use Django as simple as it is now, which means that for every external dependency we introduce, there needs to be a way to work round it to just run Django in "classic" mode if the user wants to.

To this end, Django will still be deployable with a WSGI server as it is now, with all channels-dependent features disabled, and when it ships, will fall back to a standard WSGI `runserver` if the dependencies to run a more complex interface server aren't installed (but if they are, `runserver` will become websocket-aware).

There will also be options to plug Channels into a WSGI server as a WSGI application that then forwards into a channel backend, if users wish to keep using familiar webservers but still run a worker cluster and gain things like background tasks (or WebSockets using a second server process)

Standardization
---------------

Given the intention to develop this as two codebases (though Django will still mean the combination of both), it will likely be sensible if not necessary to standardise the way the two talk to each other.

There are two levels to this standardisation - firstly, the message formats for how to encode different events, requests and responses (which you can see the initial version of over in :doc:`message-standards`), and secondly, the actual transports themselves, the channel backends.

Message format standardisation shouldn't be too hard; the top-level constraint on messages will be that they must be JSON-serializable dicts with no size limit; from there, developing sensible mappings for HTTP and WebSocket is not too hard, especially drawing on the WSGI spec for the former (indeed, Channels will have to be able to reconstitude WSGI-style properties and variables to let existing view code continue to work)

Transport standardisation is different, though; the current approach is to have a standard backend interface that either core backends or third-party ones can implement, much like Django's database support; this would seem to fill the immediate need of both having core, tested and scalable transports as well as the option for more complex projects with special requirements to write their own.

That said, the current proposed system is just one transport standard away from being able to interoperate with other languages; specifically, one can imagine an interface server written in a compiled language like Go or Rust that is more efficient than its Python equivalent (or even a Python implementation that uses a concurrency model that doesn't fit the channel backend's poll-style interface).

It may be that the Redis backend itself is written up and standardised as well to provide a clear spec that third parties can code against from scratch; however, this will need to be after a period of iterative testing to ensure whatever is proposed can scale to handle both large messages and large volumes of messages, and can shard horizontally.

There is no intention to propose a WSGI replacement at this point, but there's potential to do that at the fundamental Python level of "your code will get given messages, and can send them, and here's the message formats". However, such an effort should not be taken lightly and only attempted if and when channels proves itself to work as effectively as WSGI as the abstraction for handling web requests, and its servers are as stable and mature as those for WSGI; Django will continue to support WSGI for the foreseeable future.

Imports
-------

Having Channels as a third-party package on some versions of Django and as a core package on others presents an issue for anyone trying to write portable code; the import path will differ.

Specifically, for the third party app you might import from ``channels``, whereas for the native one you might import from ``django.channels``.

There are two sensible solutions to this:

1. Make both versions available under the import path ``django.channels``
2. Make people do try/except imports for portable code

Neither are perfect; the first likely means some nasty monkeypatching or more, especially on Python 2.7, while the second involves verbose code. More research is needed here.

WSGI attribute access
---------------------

While Channels transports across a lot of the data available on a WSGI request - like paths, remote client IPs, POST data and so forth - it cannot reproduce everything. Specifically, the following changes will happen to Django request objects when they come via Channels:

- ``request.META`` will not contain any environment variables from the system.
- The ``wsgi`` keys in ``request.META`` will change as follows:
  - ``wsgi.version`` will be set to ``(1, 0)``
  - ``wsgi.url_scheme`` will be populated correctly
  - ``wsgi.input`` will work, but point to a StringIO or File object with the entire request body buffered already
  - ``wsgi.errors`` will point to ``sys.stderr``
  - ``wsgi.multithread`` will always be ``True``
  - ``wsgi.multiprocess`` will always be ``True``
  - ``wsgi.run_once`` will always be ``False``

This is a best-attempt effort to mirror these variables' meanings to allow code to keep working on multiple Django versions; we will encourage people using ``url_scheme`` to switch to ``request.is_secure``, however, and people using ``input`` to use the ``read()`` or ``body`` attributes on ``request``.

All of the ``wsgi`` variable emulation will be subject to the usual Django deprecation cycle and after this will not be available unless Django is running in a WSGI environment.

Running Workers
---------------

It is not intended for there to be a separate command to run a Django worker; instead, ``manage.py runworker`` will be the recommended method, along with a wrapping process manager that handles logging and auto-restart (such as systemd or supervisord).
