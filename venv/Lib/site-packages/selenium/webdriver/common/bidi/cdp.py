# The MIT License(MIT)
#
# Copyright(c) 2018 Hyperion Gray
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files(the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and / or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
# This code comes from https://github.com/HyperionGray/trio-chrome-devtools-protocol/tree/master/trio_cdp

import contextvars
import importlib
import itertools
import json
import logging
import pathlib
from collections import defaultdict
from collections.abc import AsyncGenerator, AsyncIterator, Generator
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass
from typing import Any, TypeVar

import trio
from trio_websocket import ConnectionClosed as WsConnectionClosed
from trio_websocket import connect_websocket_url

logger = logging.getLogger("trio_cdp")
T = TypeVar("T")
MAX_WS_MESSAGE_SIZE = 2**24

devtools = None
version = None


def import_devtools(ver):
    """Attempt to load the current latest available devtools into the module cache for use later."""
    global devtools
    global version
    version = ver
    base = "selenium.webdriver.common.devtools.v"
    try:
        devtools = importlib.import_module(f"{base}{ver}")
        return devtools
    except ModuleNotFoundError:
        # Attempt to parse and load the 'most recent' devtools module. This is likely
        # because cdp has been updated but selenium python has not been released yet.
        devtools_path = pathlib.Path(__file__).parents[1].joinpath("devtools")
        versions = tuple(f.name for f in devtools_path.iterdir() if f.is_dir())
        latest = max(int(x[1:]) for x in versions)
        selenium_logger = logging.getLogger(__name__)
        selenium_logger.debug("Falling back to loading `devtools`: v%s", latest)
        devtools = importlib.import_module(f"{base}{latest}")
        return devtools


_connection_context: contextvars.ContextVar = contextvars.ContextVar("connection_context")
_session_context: contextvars.ContextVar = contextvars.ContextVar("session_context")


def get_connection_context(fn_name):
    """Look up the current connection.

    If there is no current connection, raise a ``RuntimeError`` with a
    helpful message.
    """
    try:
        return _connection_context.get()
    except LookupError:
        raise RuntimeError(f"{fn_name}() must be called in a connection context.")


def get_session_context(fn_name):
    """Look up the current session.

    If there is no current session, raise a ``RuntimeError`` with a
    helpful message.
    """
    try:
        return _session_context.get()
    except LookupError:
        raise RuntimeError(f"{fn_name}() must be called in a session context.")


@contextmanager
def connection_context(connection):
    """Context manager installs ``connection`` as the session context for the current Trio task."""
    token = _connection_context.set(connection)
    try:
        yield
    finally:
        _connection_context.reset(token)


@contextmanager
def session_context(session):
    """Context manager installs ``session`` as the session context for the current Trio task."""
    token = _session_context.set(session)
    try:
        yield
    finally:
        _session_context.reset(token)


def set_global_connection(connection):
    """Install ``connection`` in the root context so that it will become the default connection for all tasks.

    This is generally not recommended, except it may be necessary in
    certain use cases such as running inside Jupyter notebook.
    """
    global _connection_context
    _connection_context = contextvars.ContextVar("_connection_context", default=connection)


def set_global_session(session):
    """Install ``session`` in the root context so that it will become the default session for all tasks.

    This is generally not recommended, except it may be necessary in
    certain use cases such as running inside Jupyter notebook.
    """
    global _session_context
    _session_context = contextvars.ContextVar("_session_context", default=session)


class BrowserError(Exception):
    """This exception is raised when the browser's response to a command indicates that an error occurred."""

    def __init__(self, obj):
        self.code = obj.get("code")
        self.message = obj.get("message")
        self.detail = obj.get("data")

    def __str__(self):
        return f"BrowserError<code={self.code} message={self.message}> {self.detail}"


class CdpConnectionClosed(WsConnectionClosed):
    """Raised when a public method is called on a closed CDP connection."""

    def __init__(self, reason):
        """Constructor.

        Args:
            reason: wsproto.frame_protocol.CloseReason
        """
        self.reason = reason

    def __repr__(self):
        """Return representation."""
        return f"{self.__class__.__name__}<{self.reason}>"


class InternalError(Exception):
    """This exception is only raised when there is faulty logic in TrioCDP or the integration with PyCDP."""

    pass


@dataclass
class CmEventProxy:
    """A proxy object returned by :meth:`CdpBase.wait_for()``.

    After the context manager executes, this proxy object will have a
    value set that contains the returned event.
    """

    value: Any = None


class CdpBase:
    def __init__(self, ws, session_id, target_id):
        self.ws = ws
        self.session_id = session_id
        self.target_id = target_id
        self.channels = defaultdict(set)
        self.id_iter = itertools.count()
        self.inflight_cmd = {}
        self.inflight_result = {}

    async def execute(self, cmd: Generator[dict, T, Any]) -> T:
        """Execute a command on the server and wait for the result.

        Args:
            cmd: any CDP command

        Returns:
            a CDP result
        """
        cmd_id = next(self.id_iter)
        cmd_event = trio.Event()
        self.inflight_cmd[cmd_id] = cmd, cmd_event
        request = next(cmd)
        request["id"] = cmd_id
        if self.session_id:
            request["sessionId"] = self.session_id
        request_str = json.dumps(request)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Sending CDP message: {cmd_id} {cmd_event}: {request_str}")
        try:
            await self.ws.send_message(request_str)
        except WsConnectionClosed as wcc:
            raise CdpConnectionClosed(wcc.reason) from None
        await cmd_event.wait()
        response = self.inflight_result.pop(cmd_id)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Received CDP message: {response}")
        if isinstance(response, Exception):
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Exception raised by {cmd_event} message: {type(response).__name__}")
            raise response
        return response

    def listen(self, *event_types, buffer_size=10):
        """Listen for events.

        Returns:
            An async iterator that iterates over events matching the indicated types.
        """
        sender, receiver = trio.open_memory_channel(buffer_size)
        for event_type in event_types:
            self.channels[event_type].add(sender)
        return receiver

    @asynccontextmanager
    async def wait_for(self, event_type: type[T], buffer_size=10) -> AsyncGenerator[CmEventProxy, None]:
        """Wait for an event of the given type and return it.

        This is an async context manager, so you should open it inside
        an async with block. The block will not exit until the indicated
        event is received.
        """
        sender: trio.MemorySendChannel
        receiver: trio.MemoryReceiveChannel
        sender, receiver = trio.open_memory_channel(buffer_size)
        self.channels[event_type].add(sender)
        proxy = CmEventProxy()
        yield proxy
        async with receiver:
            event = await receiver.receive()
        proxy.value = event

    def _handle_data(self, data):
        """Handle incoming WebSocket data.

        Args:
            data: a JSON dictionary
        """
        if "id" in data:
            self._handle_cmd_response(data)
        else:
            self._handle_event(data)

    def _handle_cmd_response(self, data: dict):
        """Handle a response to a command.

        This will set an event flag that will return control to the
        task that called the command.

        Args:
            data: response as a JSON dictionary
        """
        cmd_id = data["id"]
        try:
            cmd, event = self.inflight_cmd.pop(cmd_id)
        except KeyError:
            logger.warning("Got a message with a command ID that does not exist: %s", data)
            return
        if "error" in data:
            # If the server reported an error, convert it to an exception and do
            # not process the response any further.
            self.inflight_result[cmd_id] = BrowserError(data["error"])
        else:
            # Otherwise, continue the generator to parse the JSON result
            # into a CDP object.
            try:
                _ = cmd.send(data["result"])
                raise InternalError("The command's generator function did not exit when expected!")
            except StopIteration as exit:
                return_ = exit.value
            self.inflight_result[cmd_id] = return_
        event.set()

    def _handle_event(self, data: dict):
        """Handle an event.

        Args:
            data: event as a JSON dictionary
        """
        global devtools
        if devtools is None:
            raise RuntimeError("CDP devtools module not loaded. Call import_devtools() first.")
        event = devtools.util.parse_json_event(data)
        logger.debug("Received event: %s", event)
        to_remove = set()
        for sender in self.channels[type(event)]:
            try:
                sender.send_nowait(event)
            except trio.WouldBlock:
                logger.error('Unable to send event "%r" due to full channel %s', event, sender)
            except trio.BrokenResourceError:
                to_remove.add(sender)
        if to_remove:
            self.channels[type(event)] -= to_remove


class CdpSession(CdpBase):
    """Contains the state for a CDP session.

    Generally you should not instantiate this object yourself; you should call
    :meth:`CdpConnection.open_session`.
    """

    def __init__(self, ws, session_id, target_id):
        """Constructor.

        Args:
            ws: trio_websocket.WebSocketConnection
            session_id: devtools.target.SessionID
            target_id: devtools.target.TargetID
        """
        super().__init__(ws, session_id, target_id)

        self._dom_enable_count = 0
        self._dom_enable_lock = trio.Lock()
        self._page_enable_count = 0
        self._page_enable_lock = trio.Lock()

    @asynccontextmanager
    async def dom_enable(self):
        """Context manager that executes ``dom.enable()`` when it enters and then calls ``dom.disable()``.

        This keeps track of concurrent callers and only disables DOM
        events when all callers have exited.
        """
        global devtools
        async with self._dom_enable_lock:
            self._dom_enable_count += 1
            if self._dom_enable_count == 1:
                await self.execute(devtools.dom.enable())

        yield

        async with self._dom_enable_lock:
            self._dom_enable_count -= 1
            if self._dom_enable_count == 0:
                await self.execute(devtools.dom.disable())

    @asynccontextmanager
    async def page_enable(self):
        """Context manager executes ``page.enable()`` when it enters and then calls ``page.disable()`` when it exits.

        This keeps track of concurrent callers and only disables page
        events when all callers have exited.
        """
        global devtools
        async with self._page_enable_lock:
            self._page_enable_count += 1
            if self._page_enable_count == 1:
                await self.execute(devtools.page.enable())

        yield

        async with self._page_enable_lock:
            self._page_enable_count -= 1
            if self._page_enable_count == 0:
                await self.execute(devtools.page.disable())


class CdpConnection(CdpBase, trio.abc.AsyncResource):
    """Contains the connection state for a Chrome DevTools Protocol server.

    CDP can multiplex multiple "sessions" over a single connection. This
    class corresponds to the "root" session, i.e. the implicitly created
    session that has no session ID. This class is responsible for
    reading incoming WebSocket messages and forwarding them to the
    corresponding session, as well as handling messages targeted at the
    root session itself. You should generally call the
    :func:`open_cdp()` instead of instantiating this class directly.
    """

    def __init__(self, ws):
        """Constructor.

        Args:
            ws: trio_websocket.WebSocketConnection
        """
        super().__init__(ws, session_id=None, target_id=None)
        self.sessions = {}

    async def aclose(self):
        """Close the underlying WebSocket connection.

        This will cause the reader task to gracefully exit when it tries
        to read the next message from the WebSocket. All of the public
        APIs (``execute()``, ``listen()``, etc.) will raise
        ``CdpConnectionClosed`` after the CDP connection is closed. It
        is safe to call this multiple times.
        """
        await self.ws.aclose()

    @asynccontextmanager
    async def open_session(self, target_id) -> AsyncIterator[CdpSession]:
        """Context manager opens a session and enables the "simple" style of calling CDP APIs.

        For example, inside a session context, you can call ``await
        dom.get_document()`` and it will execute on the current session
        automatically.
        """
        session = await self.connect_session(target_id)
        with session_context(session):
            yield session

    async def connect_session(self, target_id) -> "CdpSession":
        """Returns a new :class:`CdpSession` connected to the specified target."""
        global devtools
        if devtools is None:
            raise RuntimeError("CDP devtools module not loaded. Call import_devtools() first.")
        session_id = await self.execute(devtools.target.attach_to_target(target_id, True))
        session = CdpSession(self.ws, session_id, target_id)
        self.sessions[session_id] = session
        return session

    async def _reader_task(self):
        """Runs in the background and handles incoming messages.

        Dispatches responses to commands and events to listeners.
        """
        global devtools
        if devtools is None:
            raise RuntimeError("CDP devtools module not loaded. Call import_devtools() first.")
        while True:
            try:
                message = await self.ws.get_message()
            except WsConnectionClosed:
                # If the WebSocket is closed, we don't want to throw an
                # exception from the reader task. Instead we will throw
                # exceptions from the public API methods, and we can quietly
                # exit the reader task here.
                break
            try:
                data = json.loads(message)
            except json.JSONDecodeError:
                raise BrowserError({"code": -32700, "message": "Client received invalid JSON", "data": message})
            logger.debug("Received message %r", data)
            if "sessionId" in data:
                session_id = devtools.target.SessionID(data["sessionId"])
                try:
                    session = self.sessions[session_id]
                except KeyError:
                    raise BrowserError(
                        {
                            "code": -32700,
                            "message": "Browser sent a message for an invalid session",
                            "data": f"{session_id!r}",
                        }
                    )
                session._handle_data(data)
            else:
                self._handle_data(data)

        for _, session in self.sessions.items():
            for _, senders in session.channels.items():
                for sender in senders:
                    sender.close()


@asynccontextmanager
async def open_cdp(url) -> AsyncIterator[CdpConnection]:
    """Async context manager opens a connection to the browser then closes the connection when the block exits.

    The context manager also sets the connection as the default
    connection for the current task, so that commands like ``await
    target.get_targets()`` will run on this connection automatically. If
    you want to use multiple connections concurrently, it is recommended
    to open each on in a separate task.
    """
    async with trio.open_nursery() as nursery:
        conn = await connect_cdp(nursery, url)
        try:
            with connection_context(conn):
                yield conn
        finally:
            await conn.aclose()


async def connect_cdp(nursery, url) -> CdpConnection:
    """Connect to the browser specified by ``url`` and spawn a background task in the specified nursery.

    The ``open_cdp()`` context manager is preferred in most situations.
    You should only use this function if you need to specify a custom
    nursery. This connection is not automatically closed! You can either
    use the connection object as a context manager (``async with
    conn:``) or else call ``await conn.aclose()`` on it when you are
    done with it. If ``set_context`` is True, then the returned
    connection will be installed as the default connection for the
    current task. This argument is for unusual use cases, such as
    running inside of a notebook.
    """
    ws = await connect_websocket_url(nursery, url, max_message_size=MAX_WS_MESSAGE_SIZE)
    cdp_conn = CdpConnection(ws)
    nursery.start_soon(cdp_conn._reader_task)
    return cdp_conn
