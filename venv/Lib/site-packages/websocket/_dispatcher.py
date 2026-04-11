import time
import socket
import inspect
import selectors
from typing import TYPE_CHECKING, Callable, Optional, Union

if TYPE_CHECKING:
    from ._app import WebSocketApp
from . import _logging
from ._socket import send

"""
_dispatcher.py
websocket - WebSocket client library for Python

Copyright 2025 engn33r

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

class DispatcherBase:
    """
    DispatcherBase
    """

    def __init__(
        self, app: "WebSocketApp", ping_timeout: Optional[Union[float, int]]
    ) -> None:
        self.app = app
        self.ping_timeout = ping_timeout

    def timeout(self, seconds: Optional[Union[float, int]], callback: Callable) -> None:
        if seconds is not None:
            time.sleep(seconds)
        callback()

    def reconnect(self, seconds: int, reconnector: Callable) -> None:
        try:
            _logging.info(
                f"reconnect() - retrying in {seconds} seconds [{len(inspect.stack())} frames in stack]"
            )
            time.sleep(seconds)
            reconnector(reconnecting=True)
        except KeyboardInterrupt as e:
            _logging.info(f"User exited {e}")
            raise e

    def send(self, sock: socket.socket, data: Union[str, bytes]) -> int:
        return send(sock, data)


class Dispatcher(DispatcherBase):
    """
    Dispatcher
    """

    def read(
        self,
        sock: socket.socket,
        read_callback: Callable,
        check_callback: Callable,
    ) -> None:
        if self.app.sock is None or self.app.sock.sock is None:
            return
        sel = selectors.DefaultSelector()
        sel.register(self.app.sock.sock, selectors.EVENT_READ)
        try:
            while self.app.keep_running:
                if sel.select(self.ping_timeout):
                    if not read_callback():
                        break
                check_callback()
        finally:
            sel.close()


class SSLDispatcher(DispatcherBase):
    """
    SSLDispatcher
    """

    def read(
        self,
        sock: socket.socket,
        read_callback: Callable,
        check_callback: Callable,
    ) -> None:
        if self.app.sock is None or self.app.sock.sock is None:
            return
        sock = self.app.sock.sock
        sel = selectors.DefaultSelector()
        sel.register(sock, selectors.EVENT_READ)
        try:
            while self.app.keep_running:
                if self.select(sock, sel):
                    if not read_callback():
                        break
                check_callback()
        finally:
            sel.close()

    def select(self, sock, sel: selectors.DefaultSelector):
        if self.app.sock is None:
            return None
        sock = self.app.sock.sock
        if sock.pending():
            return [
                sock,
            ]

        r = sel.select(self.ping_timeout)

        if len(r) > 0:
            return r[0][0]
        return None


class WrappedDispatcher:
    """
    WrappedDispatcher
    """

    def __init__(
        self,
        app: "WebSocketApp",
        ping_timeout: Optional[Union[float, int]],
        dispatcher,
        handleDisconnect,
    ) -> None:
        self.app = app
        self.ping_timeout = ping_timeout
        self.dispatcher = dispatcher
        self.handleDisconnect = handleDisconnect
        dispatcher.signal(2, dispatcher.abort)  # keyboard interrupt

    def read(
        self,
        sock: socket.socket,
        read_callback: Callable,
        check_callback: Callable,
    ) -> None:
        self.dispatcher.read(sock, read_callback)
        if self.ping_timeout:
            self.timeout(self.ping_timeout, check_callback)

    def send(self, sock: socket.socket, data: Union[str, bytes]) -> int:
        self.dispatcher.buffwrite(sock, data, send, self.handleDisconnect)
        return len(data)

    def timeout(self, seconds: float, callback: Callable, *args) -> None:
        self.dispatcher.timeout(seconds, callback, *args)

    def reconnect(self, seconds: int, reconnector: Callable) -> None:
        self.timeout(seconds, reconnector, True)
