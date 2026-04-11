# -*- coding: utf-8 -*-
import errno
import socket
import unittest
from unittest.mock import Mock, patch

from websocket._socket import recv
from websocket._ssl_compat import SSLWantReadError
from websocket._exceptions import (
    WebSocketTimeoutException,
    WebSocketConnectionClosedException,
)

"""
test_socket_bugs.py
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

class SocketBugsTest(unittest.TestCase):
    """Test bugs found in socket handling logic"""

    def test_bug_implicit_none_return_from_ssl_want_read_fixed(self):
        """
        BUG #5 FIX VERIFICATION: Test SSLWantReadError timeout now raises correct exception

        Bug was in _socket.py:100-101 - SSLWantReadError except block returned None implicitly
        Fixed: Now properly handles timeout with WebSocketTimeoutException
        """
        mock_sock = Mock()
        mock_sock.recv.side_effect = SSLWantReadError()
        mock_sock.gettimeout.return_value = 1.0

        with patch("selectors.DefaultSelector") as mock_selector_class:
            mock_selector = Mock()
            mock_selector_class.return_value = mock_selector
            mock_selector.select.return_value = []  # Timeout - no data ready

            with self.assertRaises(WebSocketTimeoutException) as cm:
                recv(mock_sock, 100)

            # Verify correct timeout exception and message
            self.assertIn("Connection timed out waiting for data", str(cm.exception))

    def test_bug_implicit_none_return_from_socket_error_fixed(self):
        """
        BUG #5 FIX VERIFICATION: Test that socket.error with EAGAIN now handles timeout correctly

        Bug was in _socket.py:102-105 - socket.error except block returned None implicitly
        Fixed: Now properly handles timeout with WebSocketTimeoutException
        """
        mock_sock = Mock()

        # Create socket error with EAGAIN (should be retried)
        eagain_error = OSError(errno.EAGAIN, "Resource temporarily unavailable")

        # First call raises EAGAIN, selector times out on retry
        mock_sock.recv.side_effect = eagain_error
        mock_sock.gettimeout.return_value = 1.0

        with patch("selectors.DefaultSelector") as mock_selector_class:
            mock_selector = Mock()
            mock_selector_class.return_value = mock_selector
            mock_selector.select.return_value = []  # Timeout - no data ready

            with self.assertRaises(WebSocketTimeoutException) as cm:
                recv(mock_sock, 100)

            # Verify correct timeout exception and message
            self.assertIn("Connection timed out waiting for data", str(cm.exception))

    def test_bug_wrong_exception_for_selector_timeout_fixed(self):
        """
        BUG #6 FIX VERIFICATION: Test that selector timeout now raises correct exception type

        Bug was in _socket.py:115 returning None for timeout, treated as connection error
        Fixed: Now raises WebSocketTimeoutException directly
        """
        mock_sock = Mock()
        mock_sock.recv.side_effect = SSLWantReadError()  # Trigger retry path
        mock_sock.gettimeout.return_value = 1.0

        with patch("selectors.DefaultSelector") as mock_selector_class:
            mock_selector = Mock()
            mock_selector_class.return_value = mock_selector
            mock_selector.select.return_value = []  # TIMEOUT - this is key!

            with self.assertRaises(WebSocketTimeoutException) as cm:
                recv(mock_sock, 100)

            # Verify it's the correct timeout exception with proper message
            self.assertIn("Connection timed out waiting for data", str(cm.exception))

            # This proves the fix works:
            # 1. selector.select() returns [] (timeout)
            # 2. _recv() now raises WebSocketTimeoutException directly
            # 3. No more misclassification as connection closed error!

    def test_socket_timeout_exception_handling(self):
        """
        Test that socket.timeout exceptions are properly handled
        """
        mock_sock = Mock()
        mock_sock.gettimeout.return_value = 1.0

        # Simulate a real socket.timeout scenario
        mock_sock.recv.side_effect = socket.timeout("Operation timed out")

        # This works correctly - socket.timeout raises WebSocketTimeoutException
        with self.assertRaises(WebSocketTimeoutException) as cm:
            recv(mock_sock, 100)

        # In Python 3.10+, socket.timeout is a subclass of TimeoutError
        # so it's caught by the TimeoutError handler with hardcoded message
        # In Python 3.9, socket.timeout is caught by socket.timeout handler
        # which preserves the original message
        import sys

        if sys.version_info >= (3, 10):
            self.assertIn("Connection timed out", str(cm.exception))
        else:
            self.assertIn("Operation timed out", str(cm.exception))

    def test_correct_ssl_want_read_retry_behavior(self):
        """Test the correct behavior when SSLWantReadError is properly handled"""
        mock_sock = Mock()

        # First call raises SSLWantReadError, second call succeeds
        mock_sock.recv.side_effect = [SSLWantReadError(), b"data after retry"]
        mock_sock.gettimeout.return_value = 1.0

        with patch("selectors.DefaultSelector") as mock_selector_class:
            mock_selector = Mock()
            mock_selector_class.return_value = mock_selector
            mock_selector.select.return_value = [True]  # Data ready after wait

            # This should work correctly
            result = recv(mock_sock, 100)
            self.assertEqual(result, b"data after retry")

            # Selector should be used for retry
            mock_selector.register.assert_called()
            mock_selector.select.assert_called()


if __name__ == "__main__":
    unittest.main()
