# Copyright 2014-2021 The aiosmtpd Developers
# SPDX-License-Identifier: Apache-2.0

import asyncio
import inspect
import socket
import ssl
import warnings
from contextlib import suppress
from functools import wraps
from smtplib import SMTP as SMTPClient
from typing import Any, Callable, Generator, NamedTuple, Optional, Type, TypeVar

import pytest
from pkg_resources import resource_filename
from pytest_mock import MockFixture

from aiosmtpd.controller import Controller
from aiosmtpd.handlers import Sink

try:
    from asyncio.proactor_events import _ProactorBasePipeTransport

    HAS_PROACTOR = True
except ImportError:
    _ProactorBasePipeTransport = None
    HAS_PROACTOR = False


__all__ = [
    "controller_data",
    "handler_data",
    "Global",
    "AUTOSTOP_DELAY",
    "SERVER_CRT",
    "SERVER_KEY",
]


# region #### Aliases #################################################################

controller_data = pytest.mark.controller_data
handler_data = pytest.mark.handler_data

# endregion

# region #### Custom datatypes ########################################################


class HostPort(NamedTuple):
    host: str = "localhost"
    port: int = 8025


RT = TypeVar("RT")  # "ReturnType"


# endregion


# region #### Constants & Global Vars #################################################


class Global:
    SrvAddr: HostPort = HostPort()
    FQDN: str = socket.getfqdn()

    @classmethod
    def set_addr_from(cls, contr: Controller):
        cls.SrvAddr = HostPort(contr.hostname, contr.port)


# If less than 1.0, might cause intermittent error if test system
# is too busy/overloaded.
AUTOSTOP_DELAY = 1.5
SERVER_CRT = resource_filename("aiosmtpd.tests.certs", "server.crt")
SERVER_KEY = resource_filename("aiosmtpd.tests.certs", "server.key")

# endregion


# region #### Optimizing Fixtures #####################################################


# autouse=True and scope="session" automatically apply this fixture to ALL test cases
@pytest.fixture(autouse=True, scope="session")
def cache_fqdn(session_mocker: MockFixture):
    """
    This fixture "caches" the socket.getfqdn() call. VERY necessary to prevent
    situations where quick repeated getfqdn() causes extreme slowdown. Probably due to
    the DNS server thinking it was an attack or something.
    """
    session_mocker.patch("socket.getfqdn", return_value=Global.FQDN)


# endregion


# region #### Common Fixtures #########################################################


@pytest.fixture
def get_controller(request: pytest.FixtureRequest) -> Callable[..., Controller]:
    """
    Provides a function that will return an instance of a controller.

    Default class of the controller is Controller,
    but can be changed via the ``class_`` parameter to the function,
    or via the ``class_`` parameter of :func:`controller_data`

    Example usage::

        def test_case(get_controller):
            handler = SomeHandler()
            controller = get_controller(handler, class_=SomeController)
            ...
    """
    default_class = Controller
    marker = request.node.get_closest_marker("controller_data")
    if marker and marker.kwargs:
        # Must copy so marker data do not change between test cases if marker is
        # applied to test class
        markerdata = marker.kwargs.copy()
    else:
        markerdata = {}

    def getter(
        handler: Any,
        class_: Optional[Type[Controller]] = None,
        **server_kwargs,
    ) -> Controller:
        """
        :param handler: The handler object
        :param class_: If set to None, check controller_data(class_).
            If both are none, defaults to Controller.
        """
        assert not inspect.isclass(handler)
        marker_class: Optional[Type[Controller]]
        marker_class = markerdata.pop("class_", default_class)
        class_ = class_ or marker_class
        if class_ is None:
            raise RuntimeError(
                f"Fixture '{request.fixturename}' needs controller_data to specify "
                f"what class to use"
            )
        ip_port: HostPort = markerdata.pop("host_port", HostPort())
        # server_kwargs takes precedence, so it's rightmost (PEP448)
        server_kwargs = {**markerdata, **server_kwargs}
        server_kwargs.setdefault("hostname", ip_port.host)
        server_kwargs.setdefault("port", ip_port.port)
        return class_(
            handler,
            **server_kwargs,
        )

    return getter


@pytest.fixture
def get_handler(request: pytest.FixtureRequest) -> Callable:
    """
    Provides a function that will return an instance of
    a :ref:`handler class <handlers>`.

    Default class of the handler is Sink,
    but can be changed via the ``class_`` parameter to the function,
    or via the ``class_`` parameter of :func:`handler_data`

    Example usage::

        def test_case(get_handler):
            handler = get_handler(class_=SomeHandler)
            controller = Controller(handler)
            ...
    """
    default_class = Sink
    marker = request.node.get_closest_marker("handler_data")
    if marker and marker.kwargs:
        # Must copy so marker data do not change between test cases if marker is
        # applied to test class
        markerdata = marker.kwargs.copy()
    else:
        markerdata = {}

    def getter(*args, **kwargs) -> Any:
        if marker:
            class_ = markerdata.pop("class_", default_class)
            # *args overrides args_ in handler_data()
            args_ = markerdata.pop("args_", tuple())
            # Do NOT inline the above into the line below! We *need* to pop "args_"!
            args = args or args_
            # **kwargs override markerdata, so it's rightmost (PEP448)
            kwargs = {**markerdata, **kwargs}
        else:
            class_ = default_class
        # noinspection PyArgumentList
        return class_(*args, **kwargs)

    return getter


@pytest.fixture
def temp_event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            default_loop = asyncio.get_event_loop()
        except (DeprecationWarning, RuntimeError):
            default_loop = None
    new_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(new_loop)
    #
    yield new_loop
    #
    new_loop.close()
    if default_loop is not None:
        asyncio.set_event_loop(default_loop)


@pytest.fixture
def autostop_loop(
    temp_event_loop: asyncio.AbstractEventLoop,
) -> asyncio.AbstractEventLoop:
    # Create a new event loop, and arrange for that loop to end almost
    # immediately.  This will allow the calls to main() in these tests to
    # also exit almost immediately.  Otherwise, the foreground test
    # process will hang.
    temp_event_loop.call_later(AUTOSTOP_DELAY, temp_event_loop.stop)
    #
    return temp_event_loop


@pytest.fixture
def plain_controller(
    get_handler: Callable, get_controller: Callable
) -> Generator[Controller, None, None]:
    """
    Returns a Controller that, by default, gets invoked with no optional args.
    Hence the moniker "plain".

    Internally uses the :fixture:`get_controller` and :fixture:`get_handler` fixtures,
    so optional args/kwargs can be specified for the Controller and the handler
    via the :func:`controller_data` and :func:`handler_data` markers,
    respectively.
    """
    handler = get_handler()
    controller = get_controller(handler)
    controller.start()
    Global.set_addr_from(controller)
    #
    yield controller
    #
    # Some test cases need to .stop() the controller inside themselves
    # in such cases, we must suppress Controller's raise of AssertionError
    # because Controller doesn't like .stop() to be invoked more than once
    with suppress(AssertionError):
        controller.stop()


@pytest.fixture
def nodecode_controller(
    get_handler: Callable, get_controller: Callable
) -> Generator[Controller, None, None]:
    """
    Same as :fixture:`plain_controller`,
    except that ``decode_data=False`` is enforced.
    """
    handler = get_handler()
    controller = get_controller(handler, decode_data=False)
    controller.start()
    Global.set_addr_from(controller)
    #
    yield controller
    #
    # Some test cases need to .stop() the controller inside themselves
    # in such cases, we must suppress Controller's raise of AssertionError
    # because Controller doesn't like .stop() to be invoked more than once
    with suppress(AssertionError):
        controller.stop()


@pytest.fixture
def decoding_controller(
    get_handler: Callable, get_controller: Callable
) -> Generator[Controller, None, None]:
    handler = get_handler()
    controller = get_controller(handler, decode_data=True)
    controller.start()
    Global.set_addr_from(controller)
    #
    yield controller
    #
    # Some test cases need to .stop() the controller inside themselves
    # in such cases, we must suppress Controller's raise of AssertionError
    # because Controller doesn't like .stop() to be invoked more than once
    with suppress(AssertionError):
        controller.stop()


@pytest.fixture
def client(request: pytest.FixtureRequest) -> Generator[SMTPClient, None, None]:
    """
    Generic SMTP Client,
    will connect to the ``host:port`` defined in ``Global.SrvAddr``
    unless overriden using :func:`client_data` marker.
    """
    marker = request.node.get_closest_marker("client_data")
    if marker:
        markerdata = marker.kwargs or {}
    else:
        markerdata = {}
    addrport = markerdata.get("connect_to", Global.SrvAddr)
    with SMTPClient(*addrport) as client:
        yield client


@pytest.fixture
def ssl_context_server() -> ssl.SSLContext:
    """
    Provides a server-side SSL Context
    """
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.check_hostname = False
    context.load_cert_chain(SERVER_CRT, SERVER_KEY)
    #
    return context


@pytest.fixture
def ssl_context_client() -> ssl.SSLContext:
    """
    Provides a client-side SSL Context
    """
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
    context.check_hostname = False
    context.load_verify_locations(SERVER_CRT)
    #
    return context


# Please keep the scope as "module"; setting it as "function" (the default) somehow
# causes the 'hidden' exception to be detected when the loop starts over in the next
# test case, defeating the silencing.
@pytest.fixture(scope="module")
def silence_event_loop_closed() -> bool:
    """
    Mostly used to suppress "unhandled exception" error due to
    ``_ProactorBasePipeTransport`` raising an exception when doing ``__del__``
    """
    if not HAS_PROACTOR:
        return False
    assert _ProactorBasePipeTransport is not None
    if hasattr(_ProactorBasePipeTransport, "old_del"):
        return True

    # From: https://github.com/aio-libs/aiohttp/issues/4324#issuecomment-733884349
    def silencer(func: Callable[..., RT]) -> Callable[..., RT]:
        @wraps(func)
        def wrapper(self: Any, *args, **kwargs) -> RT:
            try:
                return func(self, *args, **kwargs)
            except RuntimeError as e:
                if str(e) != "Event loop is closed":
                    raise

        return wrapper

    # noinspection PyUnresolvedReferences
    old_del = _ProactorBasePipeTransport.__del__
    _ProactorBasePipeTransport._old_del = old_del
    _ProactorBasePipeTransport.__del__ = silencer(old_del)
    return True


# endregion
