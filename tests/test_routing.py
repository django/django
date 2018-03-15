from unittest.mock import MagicMock

import django
import pytest
from django.conf.urls import url

from channels.http import AsgiHandler
from channels.routing import ChannelNameRouter, ProtocolTypeRouter, URLRouter


def test_protocol_type_router():
    """
    Tests the ProtocolTypeRouter
    """
    # Test basic operation
    router = ProtocolTypeRouter({
        "websocket": MagicMock(return_value="ws"),
        "http": MagicMock(return_value="http"),
    })
    assert router({"type": "websocket"}) == "ws"
    assert router({"type": "http"}) == "http"
    # Test defaulting to AsgiHandler
    router = ProtocolTypeRouter({
        "websocket": MagicMock(return_value="ws"),
    })
    assert isinstance(router({"type": "http"}), AsgiHandler)
    # Test an unmatched type
    with pytest.raises(ValueError):
        router({"type": "aprs"})
    # Test a scope with no type
    with pytest.raises(KeyError):
        router({"tyyyype": "http"})


def test_channel_name_router():
    """
    Tests the ChannelNameRouter
    """
    # Test basic operation
    router = ChannelNameRouter({
        "test": MagicMock(return_value=1),
        "other_test": MagicMock(return_value=2),
    })
    assert router({"channel": "test"}) == 1
    assert router({"channel": "other_test"}) == 2
    # Test an unmatched channel
    with pytest.raises(ValueError):
        router({"channel": "chat"})
    # Test a scope with no channel
    with pytest.raises(ValueError):
        router({"type": "http"})


def test_url_router():
    """
    Tests the URLRouter
    """
    posarg_app = MagicMock(return_value=4)
    kwarg_app = MagicMock(return_value=5)
    router = URLRouter([
        url(r"^$", MagicMock(return_value=1)),
        url(r"^foo/$", MagicMock(return_value=2)),
        url(r"^bar", MagicMock(return_value=3)),
        url(r"^posarg/(\d+)/$", posarg_app),
        url(r"^kwarg/(?P<name>\w+)/$", kwarg_app),
    ])
    # Valid basic matches
    assert router({"type": "http", "path": "/"}) == 1
    assert router({"type": "http", "path": "/foo/"}) == 2
    assert router({"type": "http", "path": "/bar/"}) == 3
    assert router({"type": "http", "path": "/bar/baz/"}) == 3
    # Valid positional matches
    assert router({"type": "http", "path": "/posarg/123/"}) == 4
    assert posarg_app.call_args[0][0]["url_route"] == {"args": ("123",), "kwargs": {}}
    assert router({"type": "http", "path": "/posarg/456/"}) == 4
    assert posarg_app.call_args[0][0]["url_route"] == {"args": ("456",), "kwargs": {}}
    # Valid keyword argument matches
    assert router({"type": "http", "path": "/kwarg/hello/"}) == 5
    assert kwarg_app.call_args[0][0]["url_route"] == {"args": tuple(), "kwargs": {"name": "hello"}}
    assert router({"type": "http", "path": "/kwarg/hellothere/"}) == 5
    assert kwarg_app.call_args[0][0]["url_route"] == {"args": tuple(), "kwargs": {"name": "hellothere"}}
    # Invalid matches
    with pytest.raises(ValueError):
        router({"type": "http", "path": "/nonexistent/"})


def test_url_router_nesting():
    """
    Tests that nested URLRouters add their keyword captures together.
    """
    test_app = MagicMock(return_value=1)
    inner_router = URLRouter([
        url(r"^book/(?P<book>[\w\-]+)/page/(?P<page>\d+)/$", test_app),
        url(r"^test/(\d+)/$", test_app),
    ])
    outer_router = URLRouter([
        url(r"^universe/(?P<universe>\d+)/author/(?P<author>\w+)/", inner_router),
        url(r"^positional/(\w+)/", inner_router),
    ])
    assert outer_router({"type": "http", "path": "/universe/42/author/andrewgodwin/book/channels-guide/page/10/"}) == 1
    assert test_app.call_args[0][0]["url_route"] == {
        "args": (),
        "kwargs": {"book": "channels-guide", "author": "andrewgodwin", "page": "10", "universe": "42"},
    }

    assert outer_router({"type": "http", "path": "/positional/foo/test/3/"}) == 1
    assert test_app.call_args[0][0]["url_route"] == {
        "args": ("foo", "3"),
        "kwargs": {},
    }


@pytest.mark.skipif(django.VERSION[0] < 2, reason="Needs Django 2.x")
def test_url_router_nesting_path():
    """
    Tests that nested URLRouters add their keyword captures together when used
    with path().
    """
    from django.urls import path
    test_app = MagicMock(return_value=1)
    inner_router = URLRouter([
        path("test/<int:page>/", test_app),
    ])

    def asgi_middleware(inner):
        # Some middleware which hides the fact that we have an inner URLRouter
        def app(scope):
            return inner(scope)
        app._path_routing = True
        return app

    outer_router = URLRouter([
        path("number/<int:number>/", asgi_middleware(inner_router)),
    ])

    assert inner_router({"type": "http", "path": "/test/3/"}) == 1
    assert outer_router({"type": "http", "path": "/number/42/test/3/"}) == 1
    assert test_app.call_args[0][0]["url_route"] == {
        "args": (),
        "kwargs": {"number": 42, "page": 3},
    }
    with pytest.raises(ValueError):
        assert outer_router({"type": "http", "path": "/number/42/test/3/bla/"})
    with pytest.raises(ValueError):
        assert outer_router({"type": "http", "path": "/number/42/blub/"})


@pytest.mark.skipif(django.VERSION[0] < 2, reason="Needs Django 2.x")
def test_url_router_path():
    """
    Tests that URLRouter also works with path()
    """
    from django.urls import path
    kwarg_app = MagicMock(return_value=3)
    router = URLRouter([
        path("", MagicMock(return_value=1)),
        path("foo/", MagicMock(return_value=2)),
        path("author/<name>/", kwarg_app),
        path("year/<int:year>/", kwarg_app),
    ])
    # Valid basic matches
    assert router({"type": "http", "path": "/"}) == 1
    assert router({"type": "http", "path": "/foo/"}) == 2
    # Named without typecasting
    assert router({"type": "http", "path": "/author/andrewgodwin/"}) == 3
    assert kwarg_app.call_args[0][0]["url_route"] == {"args": tuple(), "kwargs": {"name": "andrewgodwin"}}
    # Named with typecasting
    assert router({"type": "http", "path": "/year/2012/"}) == 3
    assert kwarg_app.call_args[0][0]["url_route"] == {"args": tuple(), "kwargs": {"year": 2012}}
    # Invalid matches
    with pytest.raises(ValueError):
        router({"type": "http", "path": "/nonexistent/"})


# @pytest.mark.xfail
def test_path_remaining():
    inner_router = URLRouter([
        url(r'^no-match/$', MagicMock(return_value=1)),
    ])
    test_app = MagicMock(return_value=2)
    outer_router = URLRouter([
        url(r'^prefix/', inner_router),
        url(r'^prefix/stuff/$', test_app),
    ])
    outermost_router = URLRouter([
        url(r'', outer_router),
    ])

    assert outermost_router({"type": "http", "path": "/prefix/stuff/"}) == 2
