# -*- coding: utf-8 -*-
import unittest
from unittest.mock import Mock, patch

from websocket._handshake import _get_resp_headers
from websocket._exceptions import WebSocketBadStatusException
from websocket._ssl_compat import SSLError

"""
test_handshake_large_response.py
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

class HandshakeLargeResponseTest(unittest.TestCase):
    def test_large_error_response_chunked_reading(self):
        """Test that large HTTP error responses during handshake are read in chunks"""

        # Mock socket
        mock_sock = Mock()

        # Create a large error response body (> 16KB)
        large_response = b"Error details: " + b"A" * 20000  # 20KB+ response

        # Track recv calls to ensure chunking
        recv_calls = []

        def mock_recv(sock, bufsize):
            recv_calls.append(bufsize)
            # Simulate SSL error if trying to read > 16KB at once
            if bufsize > 16384:
                raise SSLError("[SSL: BAD_LENGTH] unknown error")
            return large_response[:bufsize]

        # Mock read_headers to return error status with large content-length
        with patch("websocket._handshake.read_headers") as mock_read_headers:
            mock_read_headers.return_value = (
                400,  # Bad request status
                {"content-length": str(len(large_response))},
                "Bad Request",
            )

            # Mock the recv function to track calls
            with patch("websocket._socket.recv", side_effect=mock_recv):
                # This should not raise SSLError, but should raise WebSocketBadStatusException
                with self.assertRaises(WebSocketBadStatusException) as cm:
                    _get_resp_headers(mock_sock)

                # Verify the response body was included in the exception
                self.assertIn(
                    b"Error details:",
                    (
                        cm.exception.args[0].encode()
                        if isinstance(cm.exception.args[0], str)
                        else cm.exception.args[0]
                    ),
                )

                # Verify chunked reading was used (multiple recv calls, none > 16KB)
                self.assertGreater(len(recv_calls), 1)
                self.assertTrue(all(call <= 16384 for call in recv_calls))

    def test_handshake_ssl_large_response_protection(self):
        """Test that the fix prevents SSL BAD_LENGTH errors during handshake"""

        mock_sock = Mock()

        # Large content that would trigger SSL error if read all at once
        large_content = b"X" * 32768  # 32KB

        chunks_returned = 0

        def mock_recv_chunked(sock, bufsize):
            nonlocal chunks_returned
            # Return data in chunks, simulating successful chunked reading
            chunk_start = chunks_returned * 16384
            chunk_end = min(chunk_start + bufsize, len(large_content))
            result = large_content[chunk_start:chunk_end]
            chunks_returned += 1 if result else 0
            return result

        with patch("websocket._handshake.read_headers") as mock_read_headers:
            mock_read_headers.return_value = (
                500,  # Server error
                {"content-length": str(len(large_content))},
                "Internal Server Error",
            )

            with patch("websocket._socket.recv", side_effect=mock_recv_chunked):
                # Should handle large response without SSL errors
                with self.assertRaises(WebSocketBadStatusException) as cm:
                    _get_resp_headers(mock_sock)

                # Verify the complete response was captured
                exception_str = str(cm.exception)
                # Response body should be in the exception message
                self.assertIn("XXXXX", exception_str)  # Part of the large content

    def test_handshake_normal_small_response(self):
        """Test that normal small responses still work correctly"""

        mock_sock = Mock()
        small_response = b"Small error message"

        def mock_recv(sock, bufsize):
            return small_response

        with patch("websocket._handshake.read_headers") as mock_read_headers:
            mock_read_headers.return_value = (
                404,  # Not found
                {"content-length": str(len(small_response))},
                "Not Found",
            )

            with patch("websocket._socket.recv", side_effect=mock_recv):
                with self.assertRaises(WebSocketBadStatusException) as cm:
                    _get_resp_headers(mock_sock)

                # Verify small response is handled correctly
                self.assertIn("Small error message", str(cm.exception))

    def test_handshake_no_content_length(self):
        """Test handshake error response without content-length header"""

        mock_sock = Mock()

        with patch("websocket._handshake.read_headers") as mock_read_headers:
            mock_read_headers.return_value = (
                403,  # Forbidden
                {},  # No content-length header
                "Forbidden",
            )

            # Should raise exception without trying to read response body
            with self.assertRaises(WebSocketBadStatusException) as cm:
                _get_resp_headers(mock_sock)

            # Should mention status but not have response body
            exception_str = str(cm.exception)
            self.assertIn("403", exception_str)
            self.assertIn("Forbidden", exception_str)


if __name__ == "__main__":
    unittest.main()
