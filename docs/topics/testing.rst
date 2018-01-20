Testing
=======

Testing Channels consumers is a little trickier than testing normal Django
views due to their underlying asynchronous nature.

To help with testing, Channels provides test helpers called *Communicators*,
which allow you to wrap up an ASGI application (like a consumer) into its own
event loop and ask it questions.

They do, however, require that you have asynchronous support in your test suite.
While you can do this yourself, we recommend using ``py.test`` with its ``asyncio``
plugin, which is how we'll illustrate tests below.


Setting Up Async Tests
----------------------

Firstly, you need to get ``py.test`` set up with async test support, and
presumably Django test support as well. You can do this by installing the
``pytest-django`` and ``pytest-asyncio`` packages::

    pip install -U pytest-django pytest-asyncio

Then, you need to decorate the tests you want to run async with
``pytest.mark.asyncio``. Note that you can't mix this with ``unittest.TestCase``
subclasses; you have to write async tests as top-level test functions in the
native ``py.test`` style::

    import pytest
    from channels.testing import HttpCommunicator
    from myproject.myapp.consumers import MyConsumer

    @pytest.mark.asyncio
    async def test_my_consumer():
        communicator = HttpCommunicator(MyConsumer, "GET", "/test/")
        response = await communicator.get_response()
        assert response["body"] == b"test response"
        assert response["status"] == 200

If you have normal Django views, you can continue to test those with the
standard Django test tools and client. You only need the async setup for
code that's written as consumers.

There's a few variants of the Communicator - a plain one for generic usage,
and one each for HTTP and WebSockets specifically that have shortcut methods,


ApplicationCommunicator
-----------------------

``ApplicationCommunicator`` is the generic test helper for any ASGI application.
It gives you two basic methods - one to send events and one to receive events.

.. note::
    ``ApplicationCommunicator`` is actually provided by the base ``asgiref``
    package, but we let you import it from ``channels.testing`` for convenience.

To construct it, pass it an application and a scope::

    from channels.testing import ApplicationCommunicator
    communicator = ApplicationCommunicator(MyConsumer, {"type": "http", ...})

To send an event, call ``send_input``::

    await communicator.send_input({
        "type": "http.request",
        "body": b"chunk one \x01 chunk two",
    })

To receive an event, call ``receive_output``::

    event = communicator.receive_output(timeout=1)
    assert event["type"] == "http.response.start"

You should only need this generic class for non-HTTP/WebSocket tests, though
you might need to fall back to it if you are testing things like HTTP chunked
responses or long-polling, which aren't supported in ``HttpCommunicator`` yet.


HttpCommunicator
================

``HttpCommunicator`` is a subclass of ``ApplicationCommunicator`` specifically
tailored for HTTP requests. You need only instantiate it with your desired
options::

    from channels.testing import HttpCommunicator
    communicator = HttpCommunicator(MyHttpConsumer, "GET", "/test/")

And then wait for its response::

    response = await communicator.get_response()
    assert response["body"] == b"test response"

You can pass the following arguments to the constructor:

* ``method``: HTTP method name (unicode string, required)
* ``path``: HTTP path (unicode string, required)
* ``body``: HTTP body (bytestring, optional)

The response from the ``get_response`` method will be a dict with the following
keys::

* ``status``: HTTP status code (integer)
* ``headers``: List of headers as (name, value) tuples (both bytestrings)
* ``body``: HTTP response body (bytestring)


WebsocketCommunicator
=====================

TODO
