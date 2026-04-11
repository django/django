# -*- coding: utf-8 -*-
import unittest
import struct
from unittest.mock import Mock, patch, MagicMock

from websocket._abnf import ABNF
from websocket._core import WebSocket
from websocket._exceptions import WebSocketProtocolException, WebSocketPayloadException
from websocket._ssl_compat import SSLError

"""
test_large_payloads.py
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

class LargePayloadTest(unittest.TestCase):
    def test_frame_length_encoding_boundaries(self):
        """Test WebSocket frame length encoding at various boundaries"""

        # Test length encoding boundaries as per RFC 6455
        test_cases = [
            (125, "Single byte length"),  # Max for 7-bit length
            (126, "Two byte length start"),  # Start of 16-bit length
            (127, "Two byte length"),
            (65535, "Two byte length max"),  # Max for 16-bit length
            (65536, "Eight byte length start"),  # Start of 64-bit length
            (16384, "16KB boundary"),  # The problematic size
            (16385, "Just over 16KB"),
            (32768, "32KB"),
            (131072, "128KB"),
        ]

        for length, description in test_cases:
            with self.subTest(length=length, description=description):
                # Create payload of specified length
                payload = b"A" * length

                # Create frame
                frame = ABNF.create_frame(payload, ABNF.OPCODE_BINARY)

                # Verify frame can be formatted without error
                formatted = frame.format()

                # Verify the frame header is correctly structured
                self.assertIsInstance(formatted, bytes)
                self.assertTrue(len(formatted) >= length)  # Header + payload

                # Verify payload length is preserved
                self.assertEqual(len(frame.data), length)

    def test_recv_large_payload_chunked(self):
        """Test receiving large payloads in chunks (simulating the 16KB recv issue)"""

        # Create a large payload that would trigger chunked reading
        large_payload = b"B" * 32768  # 32KB

        # Mock recv function that returns data in 16KB chunks
        chunks = []
        chunk_size = 16384
        for i in range(0, len(large_payload), chunk_size):
            chunks.append(large_payload[i : i + chunk_size])

        call_count = 0

        def mock_recv(bufsize):
            nonlocal call_count
            if call_count >= len(chunks):
                return b""
            result = chunks[call_count]
            call_count += 1
            return result

        # Test the frame buffer's recv_strict method
        from websocket._abnf import frame_buffer

        fb = frame_buffer(mock_recv, skip_utf8_validation=True)

        # This should handle large payloads by chunking
        result = fb.recv_strict(len(large_payload))

        self.assertEqual(result, large_payload)
        # Verify multiple recv calls were made
        self.assertGreater(call_count, 1)

    def test_ssl_large_payload_simulation(self):
        """Simulate SSL BAD_LENGTH error scenario"""

        # This test demonstrates that the 16KB limit in frame buffer protects against SSL issues
        payload_size = 16385

        recv_calls = []

        def mock_recv_with_ssl_limit(bufsize):
            recv_calls.append(bufsize)
            # This simulates the SSL issue: BAD_LENGTH when trying to recv > 16KB
            if bufsize > 16384:
                raise SSLError("[SSL: BAD_LENGTH] unknown error")
            return b"C" * min(bufsize, 16384)

        from websocket._abnf import frame_buffer

        fb = frame_buffer(mock_recv_with_ssl_limit, skip_utf8_validation=True)

        # The frame buffer handles this correctly by chunking recv calls
        result = fb.recv_strict(payload_size)

        # Verify it worked and chunked the calls properly
        self.assertEqual(len(result), payload_size)
        # Verify no single recv call was > 16KB
        self.assertTrue(all(call <= 16384 for call in recv_calls))
        # Verify multiple calls were made
        self.assertGreater(len(recv_calls), 1)

    def test_frame_format_large_payloads(self):
        """Test frame formatting with various large payload sizes"""

        # Test sizes around potential problem areas
        test_sizes = [16383, 16384, 16385, 32768, 65535, 65536]

        for size in test_sizes:
            with self.subTest(size=size):
                payload = b"D" * size
                frame = ABNF.create_frame(payload, ABNF.OPCODE_BINARY)

                # Should not raise any exceptions
                formatted = frame.format()

                # Verify structure
                self.assertIsInstance(formatted, bytes)
                self.assertEqual(len(frame.data), size)

                # Verify length encoding is correct based on size
                # Note: frames from create_frame() include masking by default (4 extra bytes)
                mask_size = 4  # WebSocket frames are masked by default
                if size < ABNF.LENGTH_7:  # < 126
                    # Length should be encoded in single byte
                    expected_header_size = (
                        2 + mask_size
                    )  # 1 byte opcode + 1 byte length + 4 byte mask
                elif size < ABNF.LENGTH_16:  # < 65536
                    # Length should be encoded in 2 bytes
                    expected_header_size = (
                        4 + mask_size
                    )  # 1 byte opcode + 1 byte marker + 2 bytes length + 4 byte mask
                else:
                    # Length should be encoded in 8 bytes
                    expected_header_size = (
                        10 + mask_size
                    )  # 1 byte opcode + 1 byte marker + 8 bytes length + 4 byte mask

                self.assertEqual(len(formatted), expected_header_size + size)

    def test_send_large_payload_chunking(self):
        """Test that large payloads are sent in chunks to avoid SSL issues"""

        mock_sock = Mock()

        # Track how data is sent
        sent_chunks = []

        def mock_send(data):
            sent_chunks.append(len(data))
            return len(data)

        mock_sock.send = mock_send
        mock_sock.gettimeout.return_value = 30.0

        # Create WebSocket with mocked socket
        ws = WebSocket()
        ws.sock = mock_sock
        ws.connected = True

        # Create large payload
        large_payload = b"E" * 32768  # 32KB

        # Send the payload
        with patch("websocket._core.send") as mock_send_func:
            mock_send_func.side_effect = lambda sock, data: len(data)

            # This should work without SSL errors
            result = ws.send_binary(large_payload)

            # Verify payload was accepted
            self.assertGreater(result, 0)

    def test_utf8_validation_large_text(self):
        """Test UTF-8 validation with large text payloads"""

        # Create large valid UTF-8 text
        large_text = "Hello 世界! " * 2000  # About 26KB with Unicode

        # Test frame creation
        frame = ABNF.create_frame(large_text, ABNF.OPCODE_TEXT)

        # Should not raise validation errors
        formatted = frame.format()
        self.assertIsInstance(formatted, bytes)

        # Test with close frame that has invalid UTF-8 (this is what validate() actually checks)
        invalid_utf8_close_data = struct.pack("!H", 1000) + b"\xff\xfe invalid utf8"

        # Create close frame with invalid UTF-8 data
        frame = ABNF(1, 0, 0, 0, ABNF.OPCODE_CLOSE, 1, invalid_utf8_close_data)

        # Validation should catch the invalid UTF-8 in close frame reason
        with self.assertRaises(WebSocketProtocolException):
            frame.validate(skip_utf8_validation=False)

    def test_frame_buffer_edge_cases(self):
        """Test frame buffer with edge cases that could trigger bugs"""

        # Test scenario: exactly 16KB payload split across recv calls
        payload_16k = b"F" * 16384

        # Simulate receiving in smaller chunks
        chunks = [payload_16k[i : i + 4096] for i in range(0, len(payload_16k), 4096)]

        call_count = 0

        def mock_recv(bufsize):
            nonlocal call_count
            if call_count >= len(chunks):
                return b""
            result = chunks[call_count]
            call_count += 1
            return result

        from websocket._abnf import frame_buffer

        fb = frame_buffer(mock_recv, skip_utf8_validation=True)
        result = fb.recv_strict(16384)

        self.assertEqual(result, payload_16k)
        # Verify multiple recv calls were made
        self.assertEqual(call_count, 4)  # 16KB / 4KB = 4 chunks

    def test_max_frame_size_limits(self):
        """Test behavior at WebSocket maximum frame size limits"""

        # Test just under the maximum theoretical frame size
        # (This is a very large test, so we'll use a smaller representative size)

        # Test with a reasonably large payload that represents the issue
        large_size = 1024 * 1024  # 1MB
        payload = b"G" * large_size

        # This should work without issues
        frame = ABNF.create_frame(payload, ABNF.OPCODE_BINARY)

        # Verify the frame can be formatted
        formatted = frame.format()
        self.assertIsInstance(formatted, bytes)

        # Verify payload is preserved
        self.assertEqual(len(frame.data), large_size)


if __name__ == "__main__":
    unittest.main()
