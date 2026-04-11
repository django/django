# -*- coding: utf-8 -*-
import sys
import unittest
from unittest.mock import patch

"""
test_utils.py
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

class UtilsTest(unittest.TestCase):
    def test_nolock(self):
        """Test NoLock context manager"""
        from websocket._utils import NoLock

        lock = NoLock()

        # Test that it can be used as context manager
        with lock:
            pass  # Should not raise any exception

        # Test enter/exit methods directly
        self.assertIsNone(lock.__enter__())
        self.assertIsNone(lock.__exit__(None, None, None))

    def test_utf8_validation_with_wsaccel(self):
        """Test UTF-8 validation when wsaccel is available"""
        # Import normally (wsaccel should be available in test environment)
        from websocket._utils import validate_utf8

        # Test valid UTF-8 strings (convert to bytes for wsaccel)
        self.assertTrue(validate_utf8("Hello, World!".encode("utf-8")))
        self.assertTrue(validate_utf8("🌟 Unicode test".encode("utf-8")))
        self.assertTrue(validate_utf8(b"Hello, bytes"))
        self.assertTrue(validate_utf8("Héllo with accénts".encode("utf-8")))

        # Test invalid UTF-8 sequences
        self.assertFalse(validate_utf8(b"\xff\xfe"))  # Invalid UTF-8
        self.assertFalse(validate_utf8(b"\x80\x80"))  # Invalid continuation

    def test_utf8_validation_fallback(self):
        """Test UTF-8 validation fallback when wsaccel is not available"""
        # Remove _utils from modules to force reimport
        if "websocket._utils" in sys.modules:
            del sys.modules["websocket._utils"]

        # Mock wsaccel import to raise ImportError
        import builtins

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if "wsaccel" in name:
                raise ImportError(f"No module named '{name}'")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            import websocket._utils as utils

            # Test valid UTF-8 strings with fallback implementation (convert strings to bytes)
            self.assertTrue(utils.validate_utf8("Hello, World!".encode("utf-8")))
            self.assertTrue(utils.validate_utf8(b"Hello, bytes"))
            self.assertTrue(utils.validate_utf8("ASCII text".encode("utf-8")))

            # Test Unicode strings (convert to bytes)
            self.assertTrue(utils.validate_utf8("🌟 Unicode test".encode("utf-8")))
            self.assertTrue(utils.validate_utf8("Héllo with accénts".encode("utf-8")))

            # Test empty string/bytes
            self.assertTrue(utils.validate_utf8("".encode("utf-8")))
            self.assertTrue(utils.validate_utf8(b""))

            # Test invalid UTF-8 sequences (should return False)
            self.assertFalse(utils.validate_utf8(b"\xff\xfe"))
            self.assertFalse(utils.validate_utf8(b"\x80\x80"))

            # Note: The fallback implementation may have different validation behavior
            # than wsaccel, so we focus on clearly invalid sequences

    def test_extract_err_message(self):
        """Test extract_err_message function"""
        from websocket._utils import extract_err_message

        # Test with exception that has args
        exc_with_args = Exception("Test error message")
        self.assertEqual(extract_err_message(exc_with_args), "Test error message")

        # Test with exception that has multiple args
        exc_multi_args = Exception("First arg", "Second arg")
        self.assertEqual(extract_err_message(exc_multi_args), "First arg")

        # Test with exception that has no args
        exc_no_args = Exception()
        self.assertIsNone(extract_err_message(exc_no_args))

    def test_extract_error_code(self):
        """Test extract_error_code function"""
        from websocket._utils import extract_error_code

        # Test with exception that has integer as first arg
        exc_with_code = Exception(404, "Not found")
        self.assertEqual(extract_error_code(exc_with_code), 404)

        # Test with exception that has string as first arg
        exc_with_string = Exception("Error message", "Second arg")
        self.assertIsNone(extract_error_code(exc_with_string))

        # Test with exception that has only one arg
        exc_single_arg = Exception("Single arg")
        self.assertIsNone(extract_error_code(exc_single_arg))

        # Test with exception that has no args
        exc_no_args = Exception()
        self.assertIsNone(extract_error_code(exc_no_args))

    def tearDown(self):
        """Clean up after tests"""
        # Ensure _utils is reimported fresh for next test
        if "websocket._utils" in sys.modules:
            del sys.modules["websocket._utils"]


if __name__ == "__main__":
    unittest.main()
