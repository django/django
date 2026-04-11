# -*- coding: utf-8 -*-
import errno
import socket
import unittest
from unittest.mock import Mock, patch, MagicMock
import time

from websocket._socket import recv, recv_line, send, DEFAULT_SOCKET_OPTION
from websocket._ssl_compat import (
    SSLError,
    SSLEOFError,
    SSLWantWriteError,
    SSLWantReadError,
)
from websocket._exceptions import (
    WebSocketTimeoutException,
    WebSocketConnectionClosedException,
)

"""
test_socket.py
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

class SocketTest(unittest.TestCase):
    def test_default_socket_option(self):
        """Test DEFAULT_SOCKET_OPTION contains expected options"""
        self.assertIsInstance(DEFAULT_SOCKET_OPTION, list)
        self.assertGreater(len(DEFAULT_SOCKET_OPTION), 0)

        # Should contain TCP_NODELAY option
        tcp_nodelay_found = any(
            opt[1] == socket.TCP_NODELAY for opt in DEFAULT_SOCKET_OPTION
        )
        self.assertTrue(tcp_nodelay_found)

    def test_recv_normal(self):
        """Test normal recv operation"""
        mock_sock = Mock()
        mock_sock.recv.return_value = b"test data"

        result = recv(mock_sock, 9)

        self.assertEqual(result, b"test data")
        mock_sock.recv.assert_called_once_with(9)

    def test_recv_timeout_error(self):
        """Test recv with TimeoutError"""
        mock_sock = Mock()
        mock_sock.recv.side_effect = TimeoutError("Connection timed out")

        with self.assertRaises(WebSocketTimeoutException) as cm:
            recv(mock_sock, 9)

        self.assertEqual(str(cm.exception), "Connection timed out")

    def test_recv_socket_timeout(self):
        """Test recv with socket.timeout"""
        mock_sock = Mock()
        timeout_exc = socket.timeout("Socket timed out")
        timeout_exc.args = ("Socket timed out",)
        mock_sock.recv.side_effect = timeout_exc
        mock_sock.gettimeout.return_value = 30.0

        with self.assertRaises(WebSocketTimeoutException) as cm:
            recv(mock_sock, 9)

        # In Python 3.10+, socket.timeout is a subclass of TimeoutError
        # so it's caught by the TimeoutError handler with hardcoded message
        # In Python 3.9, socket.timeout is caught by socket.timeout handler
        # which preserves the original message
        import sys

        if sys.version_info >= (3, 10):
            self.assertEqual(str(cm.exception), "Connection timed out")
        else:
            self.assertEqual(str(cm.exception), "Socket timed out")

    def test_recv_ssl_timeout(self):
        """Test recv with SSL timeout error"""
        mock_sock = Mock()
        ssl_exc = SSLError("The operation timed out")
        ssl_exc.args = ("The operation timed out",)
        mock_sock.recv.side_effect = ssl_exc

        with self.assertRaises(WebSocketTimeoutException) as cm:
            recv(mock_sock, 9)

        self.assertEqual(str(cm.exception), "The operation timed out")

    def test_recv_ssl_non_timeout_error(self):
        """Test recv with SSL non-timeout error"""
        mock_sock = Mock()
        ssl_exc = SSLError("SSL certificate error")
        ssl_exc.args = ("SSL certificate error",)
        mock_sock.recv.side_effect = ssl_exc

        # Should re-raise the original SSL error
        with self.assertRaises(SSLError):
            recv(mock_sock, 9)

    def test_recv_empty_response(self):
        """Test recv with empty response (connection closed)"""
        mock_sock = Mock()
        mock_sock.recv.return_value = b""

        with self.assertRaises(WebSocketConnectionClosedException) as cm:
            recv(mock_sock, 9)

        self.assertEqual(str(cm.exception), "Connection to remote host was lost.")

    def test_recv_ssl_want_read_error(self):
        """Test recv with SSLWantReadError (should retry)"""
        mock_sock = Mock()

        # First call raises SSLWantReadError, second call succeeds
        mock_sock.recv.side_effect = [SSLWantReadError(), b"data after retry"]

        with patch("selectors.DefaultSelector") as mock_selector_class:
            mock_selector = Mock()
            mock_selector_class.return_value = mock_selector
            mock_selector.select.return_value = [True]  # Ready to read

            result = recv(mock_sock, 100)

            self.assertEqual(result, b"data after retry")
            mock_selector.register.assert_called()
            mock_selector.close.assert_called()

    def test_recv_ssl_want_read_timeout(self):
        """Test recv with SSLWantReadError that times out"""
        mock_sock = Mock()
        mock_sock.recv.side_effect = SSLWantReadError()
        mock_sock.gettimeout.return_value = 1.0

        with patch("selectors.DefaultSelector") as mock_selector_class:
            mock_selector = Mock()
            mock_selector_class.return_value = mock_selector
            mock_selector.select.return_value = []  # Timeout

            with self.assertRaises(WebSocketTimeoutException):
                recv(mock_sock, 100)

    def test_recv_line(self):
        """Test recv_line functionality"""
        mock_sock = Mock()

        # Mock recv to return one character at a time
        recv_calls = [b"H", b"e", b"l", b"l", b"o", b"\n"]

        with patch("websocket._socket.recv", side_effect=recv_calls) as mock_recv:
            result = recv_line(mock_sock)

            self.assertEqual(result, b"Hello\n")
            self.assertEqual(mock_recv.call_count, 6)

    def test_send_normal(self):
        """Test normal send operation"""
        mock_sock = Mock()
        mock_sock.send.return_value = 9
        mock_sock.gettimeout.return_value = 30.0

        result = send(mock_sock, b"test data")

        self.assertEqual(result, 9)
        mock_sock.send.assert_called_with(b"test data")

    def test_send_zero_timeout(self):
        """Test send with zero timeout (non-blocking)"""
        mock_sock = Mock()
        mock_sock.send.return_value = 9
        mock_sock.gettimeout.return_value = 0

        result = send(mock_sock, b"test data")

        self.assertEqual(result, 9)
        mock_sock.send.assert_called_once_with(b"test data")

    def test_send_ssl_eof_error(self):
        """Test send with SSLEOFError"""
        mock_sock = Mock()
        mock_sock.gettimeout.return_value = 30.0
        mock_sock.send.side_effect = SSLEOFError("Connection closed")

        with self.assertRaises(WebSocketConnectionClosedException) as cm:
            send(mock_sock, b"test data")

        self.assertEqual(str(cm.exception), "socket is already closed.")

    def test_send_ssl_want_write_error(self):
        """Test send with SSLWantWriteError (should retry)"""
        mock_sock = Mock()
        mock_sock.gettimeout.return_value = 30.0

        # First call raises SSLWantWriteError, second call succeeds
        mock_sock.send.side_effect = [SSLWantWriteError(), 9]

        with patch("selectors.DefaultSelector") as mock_selector_class:
            mock_selector = Mock()
            mock_selector_class.return_value = mock_selector
            mock_selector.select.return_value = [True]  # Ready to write

            result = send(mock_sock, b"test data")

            self.assertEqual(result, 9)
            mock_selector.register.assert_called()
            mock_selector.close.assert_called()

    def test_send_socket_eagain_error(self):
        """Test send with EAGAIN error (should retry)"""
        mock_sock = Mock()
        mock_sock.gettimeout.return_value = 30.0

        # Create socket error with EAGAIN
        eagain_error = socket.error("Resource temporarily unavailable")
        eagain_error.errno = errno.EAGAIN
        eagain_error.args = (errno.EAGAIN, "Resource temporarily unavailable")

        # First call raises EAGAIN, second call succeeds
        mock_sock.send.side_effect = [eagain_error, 9]

        with patch("selectors.DefaultSelector") as mock_selector_class:
            mock_selector = Mock()
            mock_selector_class.return_value = mock_selector
            mock_selector.select.return_value = [True]  # Ready to write

            result = send(mock_sock, b"test data")

            self.assertEqual(result, 9)

    def test_send_socket_ewouldblock_error(self):
        """Test send with EWOULDBLOCK error (should retry)"""
        mock_sock = Mock()
        mock_sock.gettimeout.return_value = 30.0

        # Create socket error with EWOULDBLOCK
        ewouldblock_error = socket.error("Operation would block")
        ewouldblock_error.errno = errno.EWOULDBLOCK
        ewouldblock_error.args = (errno.EWOULDBLOCK, "Operation would block")

        # First call raises EWOULDBLOCK, second call succeeds
        mock_sock.send.side_effect = [ewouldblock_error, 9]

        with patch("selectors.DefaultSelector") as mock_selector_class:
            mock_selector = Mock()
            mock_selector_class.return_value = mock_selector
            mock_selector.select.return_value = [True]  # Ready to write

            result = send(mock_sock, b"test data")

            self.assertEqual(result, 9)

    def test_send_socket_other_error(self):
        """Test send with other socket error (should raise)"""
        mock_sock = Mock()
        mock_sock.gettimeout.return_value = 30.0

        # Create socket error with different errno
        other_error = socket.error("Connection reset by peer")
        other_error.errno = errno.ECONNRESET
        other_error.args = (errno.ECONNRESET, "Connection reset by peer")

        mock_sock.send.side_effect = other_error

        with self.assertRaises(socket.error):
            send(mock_sock, b"test data")

    def test_send_socket_error_no_errno(self):
        """Test send with socket error that has no errno"""
        mock_sock = Mock()
        mock_sock.gettimeout.return_value = 30.0

        # Create socket error without errno attribute
        no_errno_error = socket.error("Generic socket error")
        no_errno_error.args = ("Generic socket error",)

        mock_sock.send.side_effect = no_errno_error

        with self.assertRaises(socket.error):
            send(mock_sock, b"test data")

    def test_send_write_timeout(self):
        """Test send write operation timeout"""
        mock_sock = Mock()
        mock_sock.gettimeout.return_value = 30.0

        # First call raises EAGAIN
        eagain_error = socket.error("Resource temporarily unavailable")
        eagain_error.errno = errno.EAGAIN
        eagain_error.args = (errno.EAGAIN, "Resource temporarily unavailable")

        mock_sock.send.side_effect = eagain_error

        with patch("selectors.DefaultSelector") as mock_selector_class:
            mock_selector = Mock()
            mock_selector_class.return_value = mock_selector
            mock_selector.select.return_value = []  # Timeout - nothing ready

            result = send(mock_sock, b"test data")

            # Should return 0 when write times out
            self.assertEqual(result, 0)

    def test_send_string_data(self):
        """Test send with string data (should be encoded)"""
        mock_sock = Mock()
        mock_sock.send.return_value = 9
        mock_sock.gettimeout.return_value = 30.0

        result = send(mock_sock, "test data")

        self.assertEqual(result, 9)
        mock_sock.send.assert_called_with(b"test data")

    def test_send_partial_send_retry(self):
        """Test send retry mechanism"""
        mock_sock = Mock()
        mock_sock.gettimeout.return_value = 30.0

        # Create a scenario where send succeeds after selector retry
        eagain_error = socket.error("Resource temporarily unavailable")
        eagain_error.errno = errno.EAGAIN
        eagain_error.args = (errno.EAGAIN, "Resource temporarily unavailable")

        # Mock the internal _send function behavior
        mock_sock.send.side_effect = [eagain_error, 9]

        with patch("selectors.DefaultSelector") as mock_selector_class:
            mock_selector = Mock()
            mock_selector_class.return_value = mock_selector
            mock_selector.select.return_value = [True]  # Socket ready for writing

            result = send(mock_sock, b"test data")

            self.assertEqual(result, 9)
            # Verify selector was used for retry mechanism
            mock_selector.register.assert_called()
            mock_selector.select.assert_called()
            mock_selector.close.assert_called()


if __name__ == "__main__":
    unittest.main()
