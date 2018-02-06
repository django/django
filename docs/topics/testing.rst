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

To wait for an application to exit (you'll need to either do this or wait for
it to send you output before you can see what it did using mocks or inspection),
use ``wait``::

    await communicator.wait(timeout=1)

If you're expecting your application to raise an exception, use ``pytest.raises``
around ``wait``::

    with pytest.raises(ValueError):
        await communicator.wait()

You should only need this generic class for non-HTTP/WebSocket tests, though
you might need to fall back to it if you are testing things like HTTP chunked
responses or long-polling, which aren't supported in ``HttpCommunicator`` yet.


HttpCommunicator
----------------

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
---------------------

``WebsocketCommunicator`` allows you to more easily test WebSocket consumers.
It provides several convenience methods for interacting with a WebSocket
application, as shown in this example::

    from channels.testing import WebsocketCommunicator
    communicator = WebsocketCommunicator(SimpleWebsocketApp, "/testws/")
    connected, subprotocol = await communicator.connect()
    assert connected
    # Test sending text
    await communicator.send_to(text_data="hello")
    response = await communicator.receive_from()
    assert response == "hello"
    # Close
    await communicator.disconnect()

.. note::

    All of these methods are coroutines, which means you must ``await`` them.
    If you do not, your test will either time out (if you forgot to await a
    send) or try comparing things to a coroutine object (if you forgot to
    await a receive).

.. important::

    If you don't call ``WebsocketCommunicator.disconnect()`` before your test
    suite ends, you may find yourself getting ``RuntimeWarnings`` about
    things never being awaited, as you will be killing your app off in the
    middle of its lifecycle.

connect
~~~~~~~

Triggers the connection phase of the WebSocket and waits for the application
to either accept or deny the connection. Takes no parameters and returns
either:

* ``(True, <chosen_subprotocol>)`` if the socket was accepted.
  ``chosen_subprotocol`` defaults to ``None``.
* ``(False, <close_code>)`` if the socket was rejected.
  ``close_code`` defaults to ``1000``.

send_to
~~~~~~~

Sends a data frame to the application. Takes exactly one of ``bytes_data``
or ``text_data`` as parameters, and returns nothing::

    await communicator.send_to(bytes_data=b"hi\0")

This method will type-check your parameters for you to ensure what you are
sending really is text or bytes.

send_json_to
~~~~~~~~~~~~

Sends a JSON payload to the application as a text frame. Call it with
an object and it will JSON-encode it for you, and return nothing::

    await communicator.send_json_to({"hello": "world"})

receive_from
~~~~~~~~~~~~

Receives a frame from the application and gives you either ``bytes`` or
``text`` back depending on the frame type::

    response = await communicator.receive_from()

Takes an optional ``timeout`` argument with a number of seconds to wait before
timing out, which defaults to 1. It will typecheck your application's responses
for you as well, to ensure that text frames contain text data, and binary
frames contain binary data.

receive_json_from
~~~~~~~~~~~~~~~~~

Receives a text frame from the application and decodes it for you::

    response = await communicator.receive_json_from()
    assert response == {"hello": "world"}

Takes an optional ``timeout`` argument with a number of seconds to wait before
timing out, which defaults to 1.

disconnect
~~~~~~~~~~

Closes the socket from the client side. Takes nothing and returns nothing.


ChannelsLiveServerTestCase
--------------------------

If you just want to run standard Selenium or other tests that require a
webserver to be running for external programs, you can use
``ChannelsLiveServerTestCase``, which is a drop-in replacement for the
standard Django ``LiveServerTestCase``::

    from channels.testing import ChannelsLiveServerTestCase

    class SomeLiveTests(ChannelsLiveServerTestCase):

        def test_live_stuff(self):
            call_external_testing_thing(self.live_server_url)
