Testing Consumers
=================

When you want to write unit tests for your new Channels consumers, you'll
realize that you can't use the standard Django test client to submit fake HTTP
requests - instead, you'll need to submit fake Messages to your consumers,
and inspect what Messages they send themselves.

We provide a ``TestCase`` subclass that sets all of this up for you,
however, so you can easily write tests and check what your consumers are sending.


ChannelTestCase
---------------

If your tests inherit from the ``channels.tests.ChannelTestCase`` base class,
whenever you run tests your channel layer will be swapped out for a captive
in-memory layer, meaning you don't need an external server running to run tests.

Moreover, you can inject messages onto this layer and inspect ones sent to it
to help test your consumers.

To inject a message onto the layer, simply call ``Channel.send()`` inside
any test method on a ``ChannelTestCase`` subclass, like so::

    from channels import Channel
    from channels.tests import ChannelTestCase

    class MyTests(ChannelTestCase):
        def test_a_thing(self):
            # This goes onto an in-memory channel, not the real backend.
            Channel("some-channel-name").send({"foo": "bar"})

To receive a message from the layer, you can use ``self.get_next_message(channel)``,
which handles receiving the message and converting it into a Message object for
you (if you want, you can call ``receive_many`` on the underlying channel layer,
but you'll get back a raw dict and channel name, which is not what consumers want).

You can use this both to get Messages to send to consumers as their primary
argument, as well as to get Messages from channels that consumers are supposed
to send on to verify that they did.

You can even pass ``require=True`` to ``get_next_message`` to make the test
fail if there is no message on the channel (by default, it will return you
``None`` instead).

Here's an extended example testing a consumer that's supposed to take a value
and post the square of it to the ``"result"`` channel::


    from channels import Channel
    from channels.tests import ChannelTestCase

    class MyTests(ChannelTestCase):
        def test_a_thing(self):
            # Inject a message onto the channel to use in a consumer
            Channel("input").send({"value": 33})
            # Run the consumer with the new Message object
            my_consumer(self.get_next_message("input", require=True))
            # Verify there's a result and that it's accurate
            result = self.get_next_message("result", require=True)
            self.assertEqual(result['value'], 1089)


Generic Consumers
-----------------

You can use ``ChannelTestCase`` to test generic consumers as well. Just pass the message
object from ``get_next_message`` to the constructor of the class. To test replies to a specific channel,
use the ``reply_channel`` property on the ``Message`` object. For example::

    from channels import Channel
    from channels.tests import ChannelTestCase

    from myapp.consumers import MyConsumer

    class MyTests(ChannelTestCase):

        def test_a_thing(self):
            # Inject a message onto the channel to use in a consumer
            Channel("input").send({"value": 33})
            # Run the consumer with the new Message object
            message = self.get_next_message("input", require=True)
            MyConsumer(message)
            # Verify there's a reply and that it's accurate
            result = self.get_next_message(message.reply_channel.name, require=True)
            self.assertEqual(result['value'], 1089)


Groups
------

You can test Groups in the same way as Channels inside a ``ChannelTestCase``;
the entire channel layer is flushed each time a test is run, so it's safe to
do group adds and sends during a test. For example::

    from channels import Group
    from channels.tests import ChannelTestCase

    class MyTests(ChannelTestCase):
        def test_a_thing(self):
            # Add a test channel to a test group
            Group("test-group").add("test-channel")
            # Send to the group
            Group("test-group").send({"value": 42})
            # Verify the message got into the destination channel
            result = self.get_next_message("test-channel", require=True)
            self.assertEqual(result['value'], 42)


Multiple Channel Layers
-----------------------

If you want to test code that uses multiple channel layers, specify the alias
of the layers you want to mock as the ``test_channel_aliases`` attribute on
the ``ChannelTestCase`` subclass; by default, only the ``default`` layer is
mocked.

You can pass an ``alias`` argument to ``get_next_message`` and ``Channel``
to use a different layer too.
