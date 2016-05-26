from __future__ import unicode_literals
from django.test import SimpleTestCase

from channels.routing import Router, route, route_class, include
from channels.message import Message
from channels.utils import name_that_thing
from channels.generic import BaseConsumer


# Fake consumers and routing sets that can be imported by string
def consumer_1():
    pass


def consumer_2():
    pass


def consumer_3():
    pass


class TestClassConsumer(BaseConsumer):

    method_mapping = {
        "test.channel": "some_method",
    }

    def some_method(self, message, **kwargs):
        pass


chatroom_routing = [
    route("websocket.connect", consumer_2, path=r"^/chat/(?P<room>[^/]+)/$"),
    route("websocket.connect", consumer_3, path=r"^/mentions/$"),
]

chatroom_routing_nolinestart = [
    route("websocket.connect", consumer_2, path=r"/chat/(?P<room>[^/]+)/$"),
    route("websocket.connect", consumer_3, path=r"/mentions/$"),
]

class_routing = [
    route_class(TestClassConsumer, path=r"^/foobar/$"),
]


class RoutingTests(SimpleTestCase):
    """
    Tests that the router's routing code works correctly.
    """

    def assertRoute(self, router, channel, content, consumer, kwargs=None):
        """
        Asserts that asking the `router` to route the `content` as a message
        from `channel` means it returns consumer `consumer`, optionally
        testing it also returns `kwargs` to be passed in

        Use `consumer` = None to assert that no route is found.
        """
        message = Message(content, channel, channel_layer="fake channel layer")
        match = router.match(message)
        if match is None:
            if consumer is None:
                return
            else:
                self.fail("No route found for %s on %s; expecting %s" % (
                    content,
                    channel,
                    name_that_thing(consumer),
                ))
        else:
            mconsumer, mkwargs = match
            if consumer is None:
                self.fail("Route found for %s on %s; expecting no route." % (
                    content,
                    channel,
                ))
            self.assertEqual(consumer, mconsumer, "Route found for %s on %s; but wrong consumer (%s not %s)." % (
                content,
                channel,
                name_that_thing(mconsumer),
                name_that_thing(consumer),
            ))
            if kwargs is not None:
                self.assertEqual(kwargs, mkwargs, "Route found for %s on %s; but wrong kwargs (%s not %s)." % (
                    content,
                    channel,
                    mkwargs,
                    kwargs,
                ))

    def test_assumption(self):
        """
        Ensures the test consumers don't compare equal, as if this ever happens
        this test file will pass and miss most bugs.
        """
        self.assertEqual(consumer_1, consumer_1)
        self.assertNotEqual(consumer_1, consumer_2)
        self.assertNotEqual(consumer_1, consumer_3)

    def test_dict(self):
        """
        Tests dict expansion
        """
        router = Router({
            "http.request": consumer_1,
            "http.disconnect": consumer_2,
        })
        self.assertRoute(
            router,
            channel="http.request",
            content={},
            consumer=consumer_1,
            kwargs={},
        )
        self.assertRoute(
            router,
            channel="http.request",
            content={"path": "/chat/"},
            consumer=consumer_1,
            kwargs={},
        )
        self.assertRoute(
            router,
            channel="http.disconnect",
            content={},
            consumer=consumer_2,
            kwargs={},
        )

    def test_filters(self):
        """
        Tests that filters catch things correctly.
        """
        router = Router([
            route("http.request", consumer_1, path=r"^/chat/$"),
            route("http.disconnect", consumer_2),
            route("http.request", consumer_3),
        ])
        # Filter hit
        self.assertRoute(
            router,
            channel="http.request",
            content={"path": "/chat/"},
            consumer=consumer_1,
            kwargs={},
        )
        # Fall-through
        self.assertRoute(
            router,
            channel="http.request",
            content={},
            consumer=consumer_3,
            kwargs={},
        )
        self.assertRoute(
            router,
            channel="http.request",
            content={"path": "/liveblog/"},
            consumer=consumer_3,
            kwargs={},
        )

    def test_include(self):
        """
        Tests inclusion without a prefix
        """
        router = Router([
            include("channels.tests.test_routing.chatroom_routing"),
        ])
        self.assertRoute(
            router,
            channel="websocket.connect",
            content={"path": "/boom/"},
            consumer=None,
        )
        self.assertRoute(
            router,
            channel="websocket.connect",
            content={"path": "/chat/django/"},
            consumer=consumer_2,
            kwargs={"room": "django"},
        )
        self.assertRoute(
            router,
            channel="websocket.connect",
            content={"path": "/mentions/"},
            consumer=consumer_3,
            kwargs={},
        )

    def test_route_class(self):
        """
        Tests route_class with/without prefix
        """
        router = Router([
            include("channels.tests.test_routing.class_routing"),
        ])
        self.assertRoute(
            router,
            channel="websocket.connect",
            content={"path": "/foobar/"},
            consumer=None,
        )
        self.assertRoute(
            router,
            channel="test.channel",
            content={"path": "/foobar/"},
            consumer=TestClassConsumer,
        )
        self.assertRoute(
            router,
            channel="test.channel",
            content={"path": "/"},
            consumer=None,
        )

    def test_include_prefix(self):
        """
        Tests inclusion with a prefix
        """
        router = Router([
            include("channels.tests.test_routing.chatroom_routing", path="^/ws/v(?P<version>[0-9]+)"),
        ])
        self.assertRoute(
            router,
            channel="websocket.connect",
            content={"path": "/boom/"},
            consumer=None,
        )
        self.assertRoute(
            router,
            channel="websocket.connect",
            content={"path": "/chat/django/"},
            consumer=None,
        )
        self.assertRoute(
            router,
            channel="websocket.connect",
            content={"path": "/ws/v2/chat/django/"},
            consumer=consumer_2,
            kwargs={"version": "2", "room": "django"},
        )
        self.assertRoute(
            router,
            channel="websocket.connect",
            content={"path": "/ws/v1/mentions/"},
            consumer=consumer_3,
            kwargs={"version": "1"},
        )
        # Check it works without the ^s too.
        router = Router([
            include("channels.tests.test_routing.chatroom_routing_nolinestart", path="/ws/v(?P<version>[0-9]+)"),
        ])
        self.assertRoute(
            router,
            channel="websocket.connect",
            content={"path": "/ws/v2/chat/django/"},
            consumer=consumer_2,
            kwargs={"version": "2", "room": "django"},
        )

    def test_positional_pattern(self):
        """
        Tests that regexes with positional groups are rejected.
        """
        with self.assertRaises(ValueError):
            Router([
                route("http.request", consumer_1, path=r"^/chat/([^/]+)/$"),
            ])

    def test_mixed_unicode_bytes(self):
        """
        Tests that having the message key be bytes and pattern unicode (or vice-versa)
        still works.
        """
        # Unicode patterns, byte message
        router = Router([
            route("websocket.connect", consumer_1, path="^/foo/"),
            include("channels.tests.test_routing.chatroom_routing", path="^/ws/v(?P<version>[0-9]+)"),
        ])
        self.assertRoute(
            router,
            channel="websocket.connect",
            content={"path": b"/boom/"},
            consumer=None,
        )
        self.assertRoute(
            router,
            channel="websocket.connect",
            content={"path": b"/foo/"},
            consumer=consumer_1,
        )
        self.assertRoute(
            router,
            channel="websocket.connect",
            content={"path": b"/ws/v2/chat/django/"},
            consumer=consumer_2,
            kwargs={"version": "2", "room": "django"},
        )
        # Byte patterns, unicode message
        router = Router([
            route("websocket.connect", consumer_1, path=b"^/foo/"),
            include("channels.tests.test_routing.chatroom_routing", path=b"^/ws/v(?P<version>[0-9]+)"),
        ])
        self.assertRoute(
            router,
            channel="websocket.connect",
            content={"path": "/boom/"},
            consumer=None,
        )
        self.assertRoute(
            router,
            channel="websocket.connect",
            content={"path": "/foo/"},
            consumer=consumer_1,
        )
        self.assertRoute(
            router,
            channel="websocket.connect",
            content={"path": "/ws/v2/chat/django/"},
            consumer=consumer_2,
            kwargs={"version": "2", "room": "django"},
        )

    def test_channels(self):
        """
        Tests that the router reports channels to listen on correctly
        """
        router = Router([
            route("http.request", consumer_1, path=r"^/chat/$"),
            route("http.disconnect", consumer_2),
            route("http.request", consumer_3),
            route_class(TestClassConsumer),
        ])
        # Initial check
        self.assertEqual(
            router.channels,
            {"http.request", "http.disconnect", "test.channel"},
        )
        # Dynamically add route, recheck
        router.add_route(route("websocket.receive", consumer_1))
        self.assertEqual(
            router.channels,
            {"http.request", "http.disconnect", "websocket.receive", "test.channel"},
        )
