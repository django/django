# -*- coding: utf-8 -*-
import socket
import unittest
from unittest.mock import Mock, patch, MagicMock
import threading
import time

import websocket
from websocket._dispatcher import (
    Dispatcher,
    DispatcherBase,
    SSLDispatcher,
    WrappedDispatcher,
)

"""
test_dispatcher.py
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

class MockApp:
    """Mock WebSocketApp for testing"""

    def __init__(self):
        self.keep_running = True
        self.sock = Mock()
        self.sock.sock = Mock()


class MockSocket:
    """Mock socket for testing"""

    def __init__(self):
        self.pending_return = False

    def pending(self):
        return self.pending_return


class MockDispatcher:
    """Mock external dispatcher for WrappedDispatcher testing"""

    def __init__(self):
        self.signal_calls = []
        self.abort_calls = []
        self.read_calls = []
        self.buffwrite_calls = []
        self.timeout_calls = []

    def signal(self, sig, handler):
        self.signal_calls.append((sig, handler))

    def abort(self):
        self.abort_calls.append(True)

    def read(self, sock, callback):
        self.read_calls.append((sock, callback))

    def buffwrite(self, sock, data, send_func, disconnect_handler):
        self.buffwrite_calls.append((sock, data, send_func, disconnect_handler))

    def timeout(self, seconds, callback, *args):
        self.timeout_calls.append((seconds, callback, args))


class DispatcherTest(unittest.TestCase):
    def setUp(self):
        self.app = MockApp()

    def test_dispatcher_base_init(self):
        """Test DispatcherBase initialization"""
        dispatcher = DispatcherBase(self.app, 30.0)

        self.assertEqual(dispatcher.app, self.app)
        self.assertEqual(dispatcher.ping_timeout, 30.0)

    def test_dispatcher_base_timeout(self):
        """Test DispatcherBase timeout method"""
        dispatcher = DispatcherBase(self.app, 30.0)
        callback = Mock()

        # Test with seconds=None (should call callback immediately)
        dispatcher.timeout(None, callback)
        callback.assert_called_once()

        # Test with seconds > 0 (would sleep in real implementation)
        callback.reset_mock()
        start_time = time.time()
        dispatcher.timeout(0.1, callback)
        elapsed = time.time() - start_time

        callback.assert_called_once()
        self.assertGreaterEqual(elapsed, 0.05)  # Allow some tolerance

    def test_dispatcher_base_reconnect(self):
        """Test DispatcherBase reconnect method"""
        dispatcher = DispatcherBase(self.app, 30.0)
        reconnector = Mock()

        # Test normal reconnect
        dispatcher.reconnect(1, reconnector)
        reconnector.assert_called_once_with(reconnecting=True)

        # Test reconnect with KeyboardInterrupt
        reconnector.reset_mock()
        reconnector.side_effect = KeyboardInterrupt("User interrupted")

        with self.assertRaises(KeyboardInterrupt):
            dispatcher.reconnect(1, reconnector)

    def test_dispatcher_base_send(self):
        """Test DispatcherBase send method"""
        dispatcher = DispatcherBase(self.app, 30.0)
        mock_sock = Mock()
        test_data = b"test data"

        with patch("websocket._dispatcher.send") as mock_send:
            mock_send.return_value = len(test_data)
            result = dispatcher.send(mock_sock, test_data)

            mock_send.assert_called_once_with(mock_sock, test_data)
            self.assertEqual(result, len(test_data))

    def test_dispatcher_read(self):
        """Test Dispatcher read method"""
        dispatcher = Dispatcher(self.app, 5.0)
        read_callback = Mock(return_value=True)
        check_callback = Mock()
        mock_sock = Mock()

        # Mock the selector to control the loop
        with patch("selectors.DefaultSelector") as mock_selector_class:
            mock_selector = Mock()
            mock_selector_class.return_value = mock_selector

            # Make select return immediately (timeout)
            mock_selector.select.return_value = []

            # Stop after first iteration
            def side_effect(*args):
                self.app.keep_running = False
                return []

            mock_selector.select.side_effect = side_effect

            dispatcher.read(mock_sock, read_callback, check_callback)

            # Verify selector was used correctly
            mock_selector.register.assert_called()
            mock_selector.select.assert_called_with(5.0)
            mock_selector.close.assert_called()
            check_callback.assert_called()

    def test_dispatcher_read_with_data(self):
        """Test Dispatcher read method when data is available"""
        dispatcher = Dispatcher(self.app, 5.0)
        read_callback = Mock(return_value=True)
        check_callback = Mock()
        mock_sock = Mock()

        with patch("selectors.DefaultSelector") as mock_selector_class:
            mock_selector = Mock()
            mock_selector_class.return_value = mock_selector

            # First call returns data, second call stops the loop
            call_count = 0

            def select_side_effect(*args):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return [True]  # Data available
                else:
                    self.app.keep_running = False
                    return []

            mock_selector.select.side_effect = select_side_effect

            dispatcher.read(mock_sock, read_callback, check_callback)

            read_callback.assert_called()
            check_callback.assert_called()

    def test_ssl_dispatcher_read(self):
        """Test SSLDispatcher read method"""
        dispatcher = SSLDispatcher(self.app, 5.0)
        read_callback = Mock(return_value=True)
        check_callback = Mock()

        # Mock socket with pending data
        mock_ssl_sock = MockSocket()
        self.app.sock.sock = mock_ssl_sock

        with patch("selectors.DefaultSelector") as mock_selector_class:
            mock_selector = Mock()
            mock_selector_class.return_value = mock_selector
            mock_selector.select.return_value = []

            # Stop after first iteration
            def side_effect(*args):
                self.app.keep_running = False
                return []

            mock_selector.select.side_effect = side_effect

            dispatcher.read(None, read_callback, check_callback)

            mock_selector.register.assert_called()
            check_callback.assert_called()

    def test_ssl_dispatcher_select_with_pending(self):
        """Test SSLDispatcher select method with pending data"""
        dispatcher = SSLDispatcher(self.app, 5.0)
        mock_ssl_sock = MockSocket()
        mock_ssl_sock.pending_return = True
        self.app.sock.sock = mock_ssl_sock
        mock_selector = Mock()

        result = dispatcher.select(None, mock_selector)

        # When pending() returns True, should return [sock]
        self.assertEqual(result, [mock_ssl_sock])

    def test_ssl_dispatcher_select_without_pending(self):
        """Test SSLDispatcher select method without pending data"""
        dispatcher = SSLDispatcher(self.app, 5.0)
        mock_ssl_sock = MockSocket()
        mock_ssl_sock.pending_return = False
        self.app.sock.sock = mock_ssl_sock
        mock_selector = Mock()
        mock_selector.select.return_value = [(mock_ssl_sock, None)]

        result = dispatcher.select(None, mock_selector)

        # Should return the first element of first result tuple
        self.assertEqual(result, mock_ssl_sock)
        mock_selector.select.assert_called_with(5.0)

    def test_ssl_dispatcher_select_no_results(self):
        """Test SSLDispatcher select method with no results"""
        dispatcher = SSLDispatcher(self.app, 5.0)
        mock_ssl_sock = MockSocket()
        mock_ssl_sock.pending_return = False
        self.app.sock.sock = mock_ssl_sock
        mock_selector = Mock()
        mock_selector.select.return_value = []

        result = dispatcher.select(None, mock_selector)

        # Should return None when no results (function doesn't return anything when len(r) == 0)
        self.assertIsNone(result)

    def test_wrapped_dispatcher_init(self):
        """Test WrappedDispatcher initialization"""
        mock_dispatcher = MockDispatcher()
        handle_disconnect = Mock()

        wrapped = WrappedDispatcher(self.app, 10.0, mock_dispatcher, handle_disconnect)

        self.assertEqual(wrapped.app, self.app)
        self.assertEqual(wrapped.ping_timeout, 10.0)
        self.assertEqual(wrapped.dispatcher, mock_dispatcher)
        self.assertEqual(wrapped.handleDisconnect, handle_disconnect)

        # Should have set up signal handler
        self.assertEqual(len(mock_dispatcher.signal_calls), 1)
        sig, handler = mock_dispatcher.signal_calls[0]
        self.assertEqual(sig, 2)  # SIGINT
        self.assertEqual(handler, mock_dispatcher.abort)

    def test_wrapped_dispatcher_read(self):
        """Test WrappedDispatcher read method"""
        mock_dispatcher = MockDispatcher()
        handle_disconnect = Mock()
        wrapped = WrappedDispatcher(self.app, 10.0, mock_dispatcher, handle_disconnect)

        mock_sock = Mock()
        read_callback = Mock()
        check_callback = Mock()

        wrapped.read(mock_sock, read_callback, check_callback)

        # Should delegate to wrapped dispatcher
        self.assertEqual(len(mock_dispatcher.read_calls), 1)
        self.assertEqual(mock_dispatcher.read_calls[0], (mock_sock, read_callback))

        # Should call timeout for ping_timeout
        self.assertEqual(len(mock_dispatcher.timeout_calls), 1)
        timeout_call = mock_dispatcher.timeout_calls[0]
        self.assertEqual(timeout_call[0], 10.0)  # timeout seconds
        self.assertEqual(timeout_call[1], check_callback)  # callback

    def test_wrapped_dispatcher_read_no_ping_timeout(self):
        """Test WrappedDispatcher read method without ping timeout"""
        mock_dispatcher = MockDispatcher()
        handle_disconnect = Mock()
        wrapped = WrappedDispatcher(self.app, None, mock_dispatcher, handle_disconnect)

        mock_sock = Mock()
        read_callback = Mock()
        check_callback = Mock()

        wrapped.read(mock_sock, read_callback, check_callback)

        # Should delegate to wrapped dispatcher
        self.assertEqual(len(mock_dispatcher.read_calls), 1)

        # Should NOT call timeout when ping_timeout is None
        self.assertEqual(len(mock_dispatcher.timeout_calls), 0)

    def test_wrapped_dispatcher_send(self):
        """Test WrappedDispatcher send method"""
        mock_dispatcher = MockDispatcher()
        handle_disconnect = Mock()
        wrapped = WrappedDispatcher(self.app, 10.0, mock_dispatcher, handle_disconnect)

        mock_sock = Mock()
        test_data = b"test data"

        with patch("websocket._dispatcher.send") as mock_send:
            result = wrapped.send(mock_sock, test_data)

            # Should delegate to dispatcher.buffwrite
            self.assertEqual(len(mock_dispatcher.buffwrite_calls), 1)
            call = mock_dispatcher.buffwrite_calls[0]
            self.assertEqual(call[0], mock_sock)
            self.assertEqual(call[1], test_data)
            self.assertEqual(call[2], mock_send)
            self.assertEqual(call[3], handle_disconnect)

            # Should return data length
            self.assertEqual(result, len(test_data))

    def test_wrapped_dispatcher_timeout(self):
        """Test WrappedDispatcher timeout method"""
        mock_dispatcher = MockDispatcher()
        handle_disconnect = Mock()
        wrapped = WrappedDispatcher(self.app, 10.0, mock_dispatcher, handle_disconnect)

        callback = Mock()
        args = ("arg1", "arg2")

        wrapped.timeout(5.0, callback, *args)

        # Should delegate to wrapped dispatcher
        self.assertEqual(len(mock_dispatcher.timeout_calls), 1)
        call = mock_dispatcher.timeout_calls[0]
        self.assertEqual(call[0], 5.0)
        self.assertEqual(call[1], callback)
        self.assertEqual(call[2], args)

    def test_wrapped_dispatcher_reconnect(self):
        """Test WrappedDispatcher reconnect method"""
        mock_dispatcher = MockDispatcher()
        handle_disconnect = Mock()
        wrapped = WrappedDispatcher(self.app, 10.0, mock_dispatcher, handle_disconnect)

        reconnector = Mock()

        wrapped.reconnect(3, reconnector)

        # Should delegate to timeout method with reconnect=True
        self.assertEqual(len(mock_dispatcher.timeout_calls), 1)
        call = mock_dispatcher.timeout_calls[0]
        self.assertEqual(call[0], 3)
        self.assertEqual(call[1], reconnector)
        self.assertEqual(call[2], (True,))


if __name__ == "__main__":
    unittest.main()
