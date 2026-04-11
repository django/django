import inspect
import socket
import threading
import time
from typing import Any, Callable, Optional, Union

from . import _logging
from ._abnf import ABNF
from ._core import WebSocket, getdefaulttimeout
from ._exceptions import (
    WebSocketConnectionClosedException,
    WebSocketException,
    WebSocketTimeoutException,
)
from ._ssl_compat import SSLEOFError
from ._url import parse_url
from ._dispatcher import Dispatcher, DispatcherBase, SSLDispatcher, WrappedDispatcher

"""
_app.py
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

__all__ = ["WebSocketApp"]

RECONNECT = 0


def set_reconnect(reconnectInterval: int) -> None:
    global RECONNECT
    RECONNECT = reconnectInterval


class WebSocketApp:
    """
    Higher level of APIs are provided. The interface is like JavaScript WebSocket object.
    """

    def __init__(
        self,
        url: str,
        header: Optional[
            Union[
                list[str],
                dict[str, str],
                Callable[[], Union[list[str], dict[str, str]]],
            ]
        ] = None,
        on_open: Optional[Callable[["WebSocketApp"], None]] = None,
        on_reconnect: Optional[Callable[["WebSocketApp"], None]] = None,
        on_message: Optional[Callable[["WebSocketApp", Any], None]] = None,
        on_error: Optional[Callable[["WebSocketApp", Any], None]] = None,
        on_close: Optional[Callable[["WebSocketApp", Any, Any], None]] = None,
        on_ping: Optional[Callable] = None,
        on_pong: Optional[Callable] = None,
        on_cont_message: Optional[Callable] = None,
        keep_running: bool = True,
        get_mask_key: Optional[Callable] = None,
        cookie: Optional[str] = None,
        subprotocols: Optional[list[str]] = None,
        on_data: Optional[Callable] = None,
        socket: Optional[socket.socket] = None,
    ) -> None:
        """
        WebSocketApp initialization

        Parameters
        ----------
        url: str
            Websocket url.
        header: list or dict or Callable
            Custom header for websocket handshake.
            If the parameter is a callable object, it is called just before the connection attempt.
            The returned dict or list is used as custom header value.
            This could be useful in order to properly setup timestamp dependent headers.
        on_open: function
            Callback object which is called at opening websocket.
            on_open has one argument.
            The 1st argument is this class object.
        on_reconnect: function
            Callback object which is called at reconnecting websocket.
            on_reconnect has one argument.
            The 1st argument is this class object.
        on_message: function
            Callback object which is called when received data.
            on_message has 2 arguments.
            The 1st argument is this class object.
            The 2nd argument is utf-8 data received from the server.
        on_error: function
            Callback object which is called when we get error.
            on_error has 2 arguments.
            The 1st argument is this class object.
            The 2nd argument is exception object.
        on_close: function
            Callback object which is called when connection is closed.
            on_close has 3 arguments.
            The 1st argument is this class object.
            The 2nd argument is close_status_code.
            The 3rd argument is close_msg.
        on_cont_message: function
            Callback object which is called when a continuation
            frame is received.
            on_cont_message has 3 arguments.
            The 1st argument is this class object.
            The 2nd argument is utf-8 string which we get from the server.
            The 3rd argument is continue flag. if 0, the data continue
            to next frame data
        on_data: function
            Callback object which is called when a message received.
            This is called before on_message or on_cont_message,
            and then on_message or on_cont_message is called.
            on_data has 4 argument.
            The 1st argument is this class object.
            The 2nd argument is utf-8 string which we get from the server.
            The 3rd argument is data type. ABNF.OPCODE_TEXT or ABNF.OPCODE_BINARY will be came.
            The 4th argument is continue flag. If 0, the data continue
        keep_running: bool
            This parameter is obsolete and ignored.
        get_mask_key: function
            A callable function to get new mask keys, see the
            WebSocket.set_mask_key's docstring for more information.
        cookie: str
            Cookie value.
        subprotocols: list
            List of available sub protocols. Default is None.
        socket: socket
            Pre-initialized stream socket.
        """
        self.url = url
        self.header = header if header is not None else []
        self.cookie = cookie

        self.on_open = on_open
        self.on_reconnect = on_reconnect
        self.on_message = on_message
        self.on_data = on_data
        self.on_error = on_error
        self.on_close = on_close
        self.on_ping = on_ping
        self.on_pong = on_pong
        self.on_cont_message = on_cont_message
        self.keep_running = False
        self.get_mask_key = get_mask_key
        self.sock: Optional[WebSocket] = None
        self.last_ping_tm = float(0)
        self.last_pong_tm = float(0)
        self.ping_thread: Optional[threading.Thread] = None
        self.stop_ping: Optional[threading.Event] = None
        self.ping_interval = float(0)
        self.ping_timeout: Optional[Union[float, int]] = None
        self.ping_payload = ""
        self.subprotocols = subprotocols
        self.prepared_socket = socket
        self.has_errored = False
        self.has_done_teardown = False
        self.has_done_teardown_lock = threading.Lock()

    def send(self, data: Union[bytes, str], opcode: int = ABNF.OPCODE_TEXT) -> None:
        """
        send message

        Parameters
        ----------
        data: str
            Message to send. If you set opcode to OPCODE_TEXT,
            data must be utf-8 string or unicode.
        opcode: int
            Operation code of data. Default is OPCODE_TEXT.
        """

        if not self.sock or self.sock.send(data, opcode) == 0:
            raise WebSocketConnectionClosedException("Connection is already closed.")

    def send_text(self, text_data: str) -> None:
        """
        Sends UTF-8 encoded text.
        """
        if not self.sock or self.sock.send(text_data, ABNF.OPCODE_TEXT) == 0:
            raise WebSocketConnectionClosedException("Connection is already closed.")

    def send_bytes(self, data: Union[bytes, bytearray]) -> None:
        """
        Sends a sequence of bytes.
        """
        if not self.sock or self.sock.send(data, ABNF.OPCODE_BINARY) == 0:
            raise WebSocketConnectionClosedException("Connection is already closed.")

    def close(self, **kwargs) -> None:
        """
        Close websocket connection.
        """
        self.keep_running = False
        if self.sock:
            self.sock.close(**kwargs)
            self.sock = None

    def _start_ping_thread(self) -> None:
        self.last_ping_tm = self.last_pong_tm = float(0)
        self.stop_ping = threading.Event()
        self.ping_thread = threading.Thread(target=self._send_ping)
        self.ping_thread.daemon = True
        self.ping_thread.start()

    def _stop_ping_thread(self) -> None:
        if self.stop_ping:
            self.stop_ping.set()
        if self.ping_thread and self.ping_thread.is_alive():
            self.ping_thread.join(3)
            # Handle thread leak - if thread doesn't terminate within timeout,
            # force cleanup and log warning instead of abandoning the thread
            if self.ping_thread.is_alive():
                _logging.warning(
                    "Ping thread failed to terminate within 3 seconds, "
                    "forcing cleanup. Thread may be blocked."
                )
                # Force cleanup by clearing references even if thread is still alive
                # The daemon thread will eventually be cleaned up by Python's GC
                # but we prevent resource leaks by not holding references

        # Always clean up references regardless of thread state
        self.ping_thread = None
        self.stop_ping = None
        self.last_ping_tm = self.last_pong_tm = float(0)

    def _send_ping(self) -> None:
        if self.stop_ping is None:
            return
        if self.stop_ping.wait(self.ping_interval) or self.keep_running is False:
            return
        while not self.stop_ping.wait(self.ping_interval) and self.keep_running is True:
            if self.sock:
                self.last_ping_tm = time.time()
                try:
                    _logging.debug("Sending ping")
                    self.sock.ping(self.ping_payload)
                except Exception as e:
                    _logging.debug(f"Failed to send ping: {e}")

    def ready(self):
        return self.sock and self.sock.connected

    def run_forever(
        self,
        sockopt: tuple = None,
        sslopt: dict = None,
        ping_interval: Union[float, int] = 0,
        ping_timeout: Optional[Union[float, int]] = None,
        ping_payload: str = "",
        http_proxy_host: str = None,
        http_proxy_port: Union[int, str] = None,
        http_no_proxy: list = None,
        http_proxy_auth: tuple = None,
        http_proxy_timeout: Optional[float] = None,
        skip_utf8_validation: bool = False,
        host: str = None,
        origin: str = None,
        dispatcher=None,
        suppress_origin: bool = False,
        proxy_type: str = None,
        reconnect: int = None,
    ) -> bool:
        """
        Run event loop for WebSocket framework.

        This loop is an infinite loop and is alive while websocket is available.

        Parameters
        ----------
        sockopt: tuple
            Values for socket.setsockopt.
            sockopt must be tuple
            and each element is argument of sock.setsockopt.
        sslopt: dict
            Optional dict object for ssl socket option.
        ping_interval: int or float
            Automatically send "ping" command
            every specified period (in seconds).
            If set to 0, no ping is sent periodically.
        ping_timeout: int or float
            Timeout (in seconds) if the pong message is not received.
        ping_payload: str
            Payload message to send with each ping.
        http_proxy_host: str
            HTTP proxy host name.
        http_proxy_port: int or str
            HTTP proxy port. If not set, set to 80.
        http_no_proxy: list
            Whitelisted host names that don't use the proxy.
        http_proxy_timeout: int or float
            HTTP proxy timeout, default is 60 sec as per python-socks.
        http_proxy_auth: tuple
            HTTP proxy auth information. tuple of username and password. Default is None.
        skip_utf8_validation: bool
            skip utf8 validation.
        host: str
            update host header.
        origin: str
            update origin header.
        dispatcher: Dispatcher object
            customize reading data from socket.
        suppress_origin: bool
            suppress outputting origin header.
        proxy_type: str
            type of proxy from: http, socks4, socks4a, socks5, socks5h
        reconnect: int
            delay interval when reconnecting

        Returns
        -------
        teardown: bool
            False if the `WebSocketApp` is closed or caught KeyboardInterrupt,
            True if any other exception was raised during a loop.
        """

        if reconnect is None:
            reconnect = RECONNECT

        if ping_timeout is not None and ping_timeout <= 0:
            raise WebSocketException("Ensure ping_timeout > 0")
        if ping_interval is not None and ping_interval < 0:
            raise WebSocketException("Ensure ping_interval >= 0")
        if ping_timeout and ping_interval and ping_interval <= ping_timeout:
            raise WebSocketException("Ensure ping_interval > ping_timeout")
        if not sockopt:
            sockopt = ()
        if not sslopt:
            sslopt = {}
        if self.sock:
            raise WebSocketException("socket is already opened")

        self.ping_interval = ping_interval
        self.ping_timeout = ping_timeout
        self.ping_payload = ping_payload
        self.has_done_teardown = False
        self.keep_running = True

        def teardown(close_frame: ABNF = None):
            """
            Tears down the connection.

            Parameters
            ----------
            close_frame: ABNF frame
                If close_frame is set, the on_close handler is invoked
                with the statusCode and reason from the provided frame.
            """

            # teardown() is called in many code paths to ensure resources are cleaned up and on_close is fired.
            # To ensure the work is only done once, we use this bool and lock.
            with self.has_done_teardown_lock:
                if self.has_done_teardown:
                    return
                self.has_done_teardown = True

            self._stop_ping_thread()
            self.keep_running = False

            if self.sock:
                # in cases like handleDisconnect, the "on_error" callback is called first. If the WebSocketApp
                # is being used in a multithreaded application, we nee to make sure that "self.sock" is cleared
                # before calling close, otherwise logic built around the sock being set can cause issues -
                # specifically calling "run_forever" again, since is checks if "self.sock" is set.
                current_sock = self.sock
                self.sock = None
                current_sock.close()

            close_status_code, close_reason = self._get_close_args(
                close_frame if close_frame else None
            )
            # Finally call the callback AFTER all teardown is complete
            self._callback(self.on_close, close_status_code, close_reason)

        def initialize_socket(reconnecting: bool = False) -> None:
            if reconnecting and self.sock:
                self.sock.shutdown()

            self.sock = WebSocket(
                self.get_mask_key,
                sockopt=sockopt,
                sslopt=sslopt,
                fire_cont_frame=self.on_cont_message is not None,
                skip_utf8_validation=skip_utf8_validation,
                enable_multithread=True,
                dispatcher=dispatcher,
            )

            self.sock.settimeout(getdefaulttimeout())
            try:
                header = self.header() if callable(self.header) else self.header

                self.sock.connect(
                    self.url,
                    header=header,
                    cookie=self.cookie,
                    http_proxy_host=http_proxy_host,
                    http_proxy_port=http_proxy_port,
                    http_no_proxy=http_no_proxy,
                    http_proxy_auth=http_proxy_auth,
                    http_proxy_timeout=http_proxy_timeout,
                    subprotocols=self.subprotocols,
                    host=host,
                    origin=origin,
                    suppress_origin=suppress_origin,
                    proxy_type=proxy_type,
                    socket=self.prepared_socket,
                )

                _logging.info("Websocket connected")

                if self.ping_interval:
                    self._start_ping_thread()

                if reconnecting and self.on_reconnect:
                    self._callback(self.on_reconnect)
                else:
                    self._callback(self.on_open)

                dispatcher.read(self.sock.sock, read, check)
            except (
                WebSocketConnectionClosedException,
                ConnectionRefusedError,
                KeyboardInterrupt,
                SystemExit,
                Exception,
            ) as e:
                handleDisconnect(e, reconnecting)

        def read() -> bool:
            if not self.keep_running:
                teardown()
                return False

            if self.sock is None:
                return False

            try:
                op_code, frame = self.sock.recv_data_frame(True)
            except (
                WebSocketConnectionClosedException,
                KeyboardInterrupt,
                SSLEOFError,
            ) as e:
                if custom_dispatcher:
                    return closed(e)
                else:
                    raise e

            if op_code == ABNF.OPCODE_CLOSE:
                return closed(frame)
            elif op_code == ABNF.OPCODE_PING:
                self._callback(self.on_ping, frame.data)
            elif op_code == ABNF.OPCODE_PONG:
                self.last_pong_tm = time.time()
                self._callback(self.on_pong, frame.data)
            elif op_code == ABNF.OPCODE_CONT and self.on_cont_message:
                self._callback(self.on_data, frame.data, frame.opcode, frame.fin)
                self._callback(self.on_cont_message, frame.data, frame.fin)
            else:
                data = frame.data
                if op_code == ABNF.OPCODE_TEXT and not skip_utf8_validation:
                    data = data.decode("utf-8")
                self._callback(self.on_data, data, frame.opcode, True)
                self._callback(self.on_message, data)

            return True

        def check() -> bool:
            if self.ping_timeout:
                has_timeout_expired = (
                    time.time() - self.last_ping_tm > self.ping_timeout
                )
                has_pong_not_arrived_after_last_ping = (
                    self.last_pong_tm - self.last_ping_tm < 0
                )
                has_pong_arrived_too_late = (
                    self.last_pong_tm - self.last_ping_tm > self.ping_timeout
                )

                if (
                    self.last_ping_tm
                    and has_timeout_expired
                    and (
                        has_pong_not_arrived_after_last_ping
                        or has_pong_arrived_too_late
                    )
                ):
                    raise WebSocketTimeoutException("ping/pong timed out")
            return True

        def closed(
            e: Union[
                WebSocketConnectionClosedException,
                ConnectionRefusedError,
                KeyboardInterrupt,
                SystemExit,
                Exception,
                str,
            ] = "closed unexpectedly",
        ) -> bool:
            if type(e) is str:
                e = WebSocketConnectionClosedException(e)
            return handleDisconnect(e, bool(reconnect))  # type: ignore[arg-type]

        def handleDisconnect(
            e: Union[
                WebSocketConnectionClosedException,
                ConnectionRefusedError,
                KeyboardInterrupt,
                SystemExit,
                Exception,
            ],
            reconnecting: bool = False,
        ) -> bool:
            self.has_errored = True
            self._stop_ping_thread()
            if not reconnecting:
                self._callback(self.on_error, e)

            if isinstance(e, (KeyboardInterrupt, SystemExit)):
                teardown()
                # Propagate further
                raise

            if reconnect:
                _logging.info(f"{e} - reconnect")
                if custom_dispatcher:
                    _logging.debug(
                        f"Calling custom dispatcher reconnect [{len(inspect.stack())} frames in stack]"
                    )
                    dispatcher.reconnect(reconnect, initialize_socket)
            else:
                _logging.error(f"{e} - goodbye")
                teardown()
            return self.has_errored

        custom_dispatcher = bool(dispatcher)
        dispatcher = self.create_dispatcher(
            ping_timeout, dispatcher, parse_url(self.url)[3], closed
        )

        try:
            initialize_socket()
            if not custom_dispatcher and reconnect:
                while self.keep_running:
                    _logging.debug(
                        f"Calling dispatcher reconnect [{len(inspect.stack())} frames in stack]"
                    )
                    dispatcher.reconnect(reconnect, initialize_socket)
        except (KeyboardInterrupt, Exception) as e:
            _logging.info(f"tearing down on exception {e}")
            teardown()
        finally:
            if not custom_dispatcher:
                # Ensure teardown was called before returning from run_forever
                teardown()

        return self.has_errored

    def create_dispatcher(
        self,
        ping_timeout: Optional[Union[float, int]],
        dispatcher: Optional[DispatcherBase] = None,
        is_ssl: bool = False,
        handleDisconnect: Callable = None,
    ) -> Union[Dispatcher, SSLDispatcher, WrappedDispatcher]:
        if dispatcher:  # If custom dispatcher is set, use WrappedDispatcher
            return WrappedDispatcher(self, ping_timeout, dispatcher, handleDisconnect)
        timeout = ping_timeout or 10
        if is_ssl:
            return SSLDispatcher(self, timeout)
        return Dispatcher(self, timeout)

    def _get_close_args(self, close_frame: ABNF) -> list:
        """
        _get_close_args extracts the close code and reason from the close body
        if it exists (RFC6455 says WebSocket Connection Close Code is optional)
        """
        # Need to catch the case where close_frame is None
        # Otherwise the following if statement causes an error
        if not self.on_close or not close_frame:
            return [None, None]

        # Extract close frame status code
        if close_frame.data and len(close_frame.data) >= 2:
            close_status_code = 256 * int(close_frame.data[0]) + int(
                close_frame.data[1]
            )
            reason = close_frame.data[2:]
            if isinstance(reason, bytes):
                reason = reason.decode("utf-8")
            return [close_status_code, reason]
        else:
            # Most likely reached this because len(close_frame_data.data) < 2
            return [None, None]

    def _callback(self, callback, *args) -> None:
        if callback:
            try:
                callback(self, *args)

            except Exception as e:
                _logging.error(f"error from callback {callback}: {e}")
                # Bug fix: Prevent infinite recursion by not calling on_error
                # when the failing callback IS on_error itself
                if self.on_error and callback is not self.on_error:
                    self.on_error(self, e)
