# -*- coding: utf-8 -*-
#
import os
import os.path
import ssl
import threading
import unittest

import websocket as ws

"""
test_app.py
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

# Skip test to access the internet unless TEST_WITH_INTERNET == 1
TEST_WITH_INTERNET = os.environ.get("TEST_WITH_INTERNET", "0") == "1"
# Skip tests relying on local websockets server unless LOCAL_WS_SERVER_PORT != -1
LOCAL_WS_SERVER_PORT = os.environ.get("LOCAL_WS_SERVER_PORT", "-1")
TEST_WITH_LOCAL_SERVER = LOCAL_WS_SERVER_PORT != "-1"
TRACEABLE = True


class WebSocketAppTest(unittest.TestCase):
    class NotSetYet:
        """A marker class for signalling that a value hasn't been set yet."""

    def setUp(self):
        ws.enableTrace(TRACEABLE)

        WebSocketAppTest.keep_running_open = WebSocketAppTest.NotSetYet()
        WebSocketAppTest.keep_running_close = WebSocketAppTest.NotSetYet()
        WebSocketAppTest.get_mask_key_id = WebSocketAppTest.NotSetYet()
        WebSocketAppTest.on_error_data = WebSocketAppTest.NotSetYet()

    def tearDown(self):
        WebSocketAppTest.keep_running_open = WebSocketAppTest.NotSetYet()
        WebSocketAppTest.keep_running_close = WebSocketAppTest.NotSetYet()
        WebSocketAppTest.get_mask_key_id = WebSocketAppTest.NotSetYet()
        WebSocketAppTest.on_error_data = WebSocketAppTest.NotSetYet()

    def close(self):
        pass

    @unittest.skipUnless(
        TEST_WITH_LOCAL_SERVER, "Tests using local websocket server are disabled"
    )
    def test_keep_running(self):
        """A WebSocketApp should keep running as long as its self.keep_running
        is not False (in the boolean context).
        """

        def on_open(self, *args, **kwargs):
            """Set the keep_running flag for later inspection and immediately
            close the connection.
            """
            self.send("hello!")
            WebSocketAppTest.keep_running_open = self.keep_running
            self.keep_running = False

        def on_message(_, message):
            print(message)
            self.close()

        def on_close(self, *args, **kwargs):
            """Set the keep_running flag for the test to use."""
            WebSocketAppTest.keep_running_close = self.keep_running

        app = ws.WebSocketApp(
            f"ws://127.0.0.1:{LOCAL_WS_SERVER_PORT}",
            on_open=on_open,
            on_close=on_close,
            on_message=on_message,
        )
        app.run_forever()

    #    @unittest.skipUnless(TEST_WITH_LOCAL_SERVER, "Tests using local websocket server are disabled")
    @unittest.skipUnless(False, "Test disabled for now (requires rel)")
    def test_run_forever_dispatcher(self):
        """A WebSocketApp should keep running as long as its self.keep_running
        is not False (in the boolean context).
        """

        def on_open(self, *args, **kwargs):
            """Send a message, receive, and send one more"""
            self.send("hello!")
            self.recv()
            self.send("goodbye!")

        def on_message(_, message):
            print(message)
            self.close()

        app = ws.WebSocketApp(
            f"ws://127.0.0.1:{LOCAL_WS_SERVER_PORT}",
            on_open=on_open,
            on_message=on_message,
        )
        app.run_forever(dispatcher="Dispatcher")  # doesn't work

    #        app.run_forever(dispatcher=rel)          # would work
    #        rel.dispatch()

    @unittest.skipUnless(
        TEST_WITH_LOCAL_SERVER, "Tests using local websocket server are disabled"
    )
    def test_run_forever_teardown_clean_exit(self):
        """The WebSocketApp.run_forever() method should return `False` when the application ends gracefully."""
        app = ws.WebSocketApp(f"ws://127.0.0.1:{LOCAL_WS_SERVER_PORT}")
        threading.Timer(interval=0.2, function=app.close).start()
        teardown = app.run_forever()
        self.assertEqual(teardown, False)

    @unittest.skipUnless(TEST_WITH_INTERNET, "Internet-requiring tests are disabled")
    def test_sock_mask_key(self):
        """A WebSocketApp should forward the received mask_key function down
        to the actual socket.
        """

        def my_mask_key_func():
            return "\x00\x00\x00\x00"

        app = ws.WebSocketApp(
            "wss://api-pub.bitfinex.com/ws/1", get_mask_key=my_mask_key_func
        )

        # if numpy is installed, this assertion fail
        # Note: We can't use 'is' for comparing the functions directly, need to use 'id'.
        self.assertEqual(id(app.get_mask_key), id(my_mask_key_func))

    @unittest.skipUnless(TEST_WITH_INTERNET, "Internet-requiring tests are disabled")
    def test_invalid_ping_interval_ping_timeout(self):
        """Test exception handling if ping_interval < ping_timeout"""

        def on_ping(app, _):
            print("Got a ping!")
            app.close()

        def on_pong(app, _):
            print("Got a pong! No need to respond")
            app.close()

        app = ws.WebSocketApp(
            "wss://api-pub.bitfinex.com/ws/1", on_ping=on_ping, on_pong=on_pong
        )
        self.assertRaises(
            ws.WebSocketException,
            app.run_forever,
            ping_interval=1,
            ping_timeout=2,
            sslopt={"cert_reqs": ssl.CERT_NONE},
        )

    @unittest.skipUnless(TEST_WITH_INTERNET, "Internet-requiring tests are disabled")
    def test_ping_interval(self):
        """Test WebSocketApp proper ping functionality"""

        def on_ping(app, _):
            print("Got a ping!")
            app.close()

        def on_pong(app, _):
            print("Got a pong! No need to respond")
            app.close()

        app = ws.WebSocketApp(
            "wss://api-pub.bitfinex.com/ws/1", on_ping=on_ping, on_pong=on_pong
        )
        app.run_forever(
            ping_interval=2, ping_timeout=1, sslopt={"cert_reqs": ssl.CERT_NONE}
        )

    @unittest.skipUnless(TEST_WITH_INTERNET, "Internet-requiring tests are disabled")
    def test_opcode_close(self):
        """Test WebSocketApp close opcode"""

        app = ws.WebSocketApp("wss://tsock.us1.twilio.com/v3/wsconnect")
        app.run_forever(ping_interval=2, ping_timeout=1, ping_payload="Ping payload")

    # This is commented out because the URL no longer responds in the expected way
    # @unittest.skipUnless(TEST_WITH_INTERNET, "Internet-requiring tests are disabled")
    # def testOpcodeBinary(self):
    #     """ Test WebSocketApp binary opcode
    #     """
    #     app = ws.WebSocketApp('wss://streaming.vn.teslamotors.com/streaming/')
    #     app.run_forever(ping_interval=2, ping_timeout=1, ping_payload="Ping payload")

    @unittest.skipUnless(TEST_WITH_INTERNET, "Internet-requiring tests are disabled")
    def test_bad_ping_interval(self):
        """A WebSocketApp handling of negative ping_interval"""
        app = ws.WebSocketApp("wss://api-pub.bitfinex.com/ws/1")
        self.assertRaises(
            ws.WebSocketException,
            app.run_forever,
            ping_interval=-5,
            sslopt={"cert_reqs": ssl.CERT_NONE},
        )

    @unittest.skipUnless(TEST_WITH_INTERNET, "Internet-requiring tests are disabled")
    def test_bad_ping_timeout(self):
        """A WebSocketApp handling of negative ping_timeout"""
        app = ws.WebSocketApp("wss://api-pub.bitfinex.com/ws/1")
        self.assertRaises(
            ws.WebSocketException,
            app.run_forever,
            ping_timeout=-3,
            sslopt={"cert_reqs": ssl.CERT_NONE},
        )

    @unittest.skipUnless(TEST_WITH_INTERNET, "Internet-requiring tests are disabled")
    def test_close_status_code(self):
        """Test extraction of close frame status code and close reason in WebSocketApp"""

        def on_close(wsapp, close_status_code, close_msg):
            print("on_close reached")

        app = ws.WebSocketApp(
            "wss://tsock.us1.twilio.com/v3/wsconnect", on_close=on_close
        )
        closeframe = ws.ABNF(
            opcode=ws.ABNF.OPCODE_CLOSE, data=b"\x03\xe8no-init-from-client"
        )
        self.assertEqual([1000, "no-init-from-client"], app._get_close_args(closeframe))

        closeframe = ws.ABNF(opcode=ws.ABNF.OPCODE_CLOSE, data=b"")
        self.assertEqual([None, None], app._get_close_args(closeframe))

        app2 = ws.WebSocketApp("wss://tsock.us1.twilio.com/v3/wsconnect")
        closeframe = ws.ABNF(opcode=ws.ABNF.OPCODE_CLOSE, data=b"")
        self.assertEqual([None, None], app2._get_close_args(closeframe))

        self.assertRaises(
            ws.WebSocketConnectionClosedException,
            app.send,
            data="test if connection is closed",
        )

    @unittest.skipUnless(
        TEST_WITH_LOCAL_SERVER, "Tests using local websocket server are disabled"
    )
    def test_callback_function_exception(self):
        """Test callback function exception handling"""

        exc = None
        passed_app = None

        def on_open(app):
            raise RuntimeError("Callback failed")

        def on_error(app, err):
            nonlocal passed_app
            passed_app = app
            nonlocal exc
            exc = err

        def on_pong(app, _):
            app.close()

        app = ws.WebSocketApp(
            f"ws://127.0.0.1:{LOCAL_WS_SERVER_PORT}",
            on_open=on_open,
            on_error=on_error,
            on_pong=on_pong,
        )
        app.run_forever(ping_interval=2, ping_timeout=1)

        self.assertEqual(passed_app, app)
        self.assertIsInstance(exc, RuntimeError)
        self.assertEqual(str(exc), "Callback failed")

    @unittest.skipUnless(
        TEST_WITH_LOCAL_SERVER, "Tests using local websocket server are disabled"
    )
    def test_callback_method_exception(self):
        """Test callback method exception handling"""

        class Callbacks:
            def __init__(self):
                self.exc = None
                self.passed_app = None
                self.app = ws.WebSocketApp(
                    f"ws://127.0.0.1:{LOCAL_WS_SERVER_PORT}",
                    on_open=self.on_open,
                    on_error=self.on_error,
                    on_pong=self.on_pong,
                )
                self.app.run_forever(ping_interval=2, ping_timeout=1)

            def on_open(self, _):
                raise RuntimeError("Callback failed")

            def on_error(self, app, err):
                self.passed_app = app
                self.exc = err

            def on_pong(self, app, _):
                app.close()

        callbacks = Callbacks()

        self.assertEqual(callbacks.passed_app, callbacks.app)
        self.assertIsInstance(callbacks.exc, RuntimeError)
        self.assertEqual(str(callbacks.exc), "Callback failed")

    @unittest.skipUnless(
        TEST_WITH_LOCAL_SERVER, "Tests using local websocket server are disabled"
    )
    def test_reconnect(self):
        """Test reconnect"""
        pong_count = 0
        exc = None

        def on_error(_, err):
            nonlocal exc
            exc = err

        def on_pong(app, _):
            nonlocal pong_count
            pong_count += 1
            if pong_count == 1:
                # First pong, shutdown socket, enforce read error
                app.sock.shutdown()
            if pong_count >= 2:
                # Got second pong after reconnect
                app.close()

        app = ws.WebSocketApp(
            f"ws://127.0.0.1:{LOCAL_WS_SERVER_PORT}", on_pong=on_pong, on_error=on_error
        )
        app.run_forever(ping_interval=2, ping_timeout=1, reconnect=3)

        self.assertEqual(pong_count, 2)
        self.assertIsInstance(exc, ws.WebSocketTimeoutException)
        self.assertEqual(str(exc), "ping/pong timed out")

    def test_dispatcher_selection_default(self):
        """Test default dispatcher selection"""
        app = ws.WebSocketApp("ws://example.com")

        # Test default dispatcher (non-SSL)
        dispatcher = app.create_dispatcher(ping_timeout=10, is_ssl=False)
        self.assertIsInstance(dispatcher, ws._dispatcher.Dispatcher)

    def test_dispatcher_selection_ssl(self):
        """Test SSL dispatcher selection"""
        app = ws.WebSocketApp("wss://example.com")

        # Test SSL dispatcher
        dispatcher = app.create_dispatcher(ping_timeout=10, is_ssl=True)
        self.assertIsInstance(dispatcher, ws._dispatcher.SSLDispatcher)

    def test_dispatcher_selection_custom(self):
        """Test custom dispatcher selection"""
        from unittest.mock import Mock

        app = ws.WebSocketApp("ws://example.com")
        custom_dispatcher = Mock()
        handle_disconnect = Mock()

        # Test wrapped dispatcher with custom dispatcher
        dispatcher = app.create_dispatcher(
            ping_timeout=10,
            dispatcher=custom_dispatcher,
            handleDisconnect=handle_disconnect,
        )
        self.assertIsInstance(dispatcher, ws._dispatcher.WrappedDispatcher)
        self.assertEqual(dispatcher.dispatcher, custom_dispatcher)
        self.assertEqual(dispatcher.handleDisconnect, handle_disconnect)

    def test_dispatcher_selection_no_ping_timeout(self):
        """Test dispatcher selection without ping timeout"""
        app = ws.WebSocketApp("ws://example.com")

        # Test with None ping_timeout (should default to 10)
        dispatcher = app.create_dispatcher(ping_timeout=None, is_ssl=False)
        self.assertIsInstance(dispatcher, ws._dispatcher.Dispatcher)
        self.assertEqual(dispatcher.ping_timeout, 10)


if __name__ == "__main__":
    unittest.main()
