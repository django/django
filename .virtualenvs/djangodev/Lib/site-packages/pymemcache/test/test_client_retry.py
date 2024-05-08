""" Test collection for the RetryingClient. """

import functools
import unittest
from unittest import mock

import pytest

from .test_client import ClientTestMixin, MockSocket
from pymemcache.client.retrying import RetryingClient
from pymemcache.client.base import Client
from pymemcache.exceptions import MemcacheUnknownError, MemcacheClientError


# Test pure passthroughs with no retry action.
class TestRetryingClientPassthrough(ClientTestMixin, unittest.TestCase):
    def make_base_client(self, mock_socket_values, **kwargs):
        base_client = Client("localhost", **kwargs)
        # mock out client._connect() rather than hard-setting client.sock to
        # ensure methods are checking whether self.sock is None before
        # attempting to use it
        sock = MockSocket(list(mock_socket_values))
        base_client._connect = mock.Mock(
            side_effect=functools.partial(setattr, base_client, "sock", sock)
        )
        return base_client

    def make_client(self, mock_socket_values, **kwargs):
        # Create a base client to wrap.
        base_client = self.make_base_client(
            mock_socket_values=mock_socket_values, **kwargs
        )

        # Wrap the client in the retrying class, disable retries.
        client = RetryingClient(base_client, attempts=1)
        return client


# Retry specific tests.
@pytest.mark.unit()
class TestRetryingClient(object):
    def make_base_client(self, mock_socket_values, **kwargs):
        """Creates a regular mock client to wrap in the RetryClient."""
        base_client = Client("localhost", **kwargs)
        # mock out client._connect() rather than hard-setting client.sock to
        # ensure methods are checking whether self.sock is None before
        # attempting to use it
        sock = MockSocket(list(mock_socket_values))
        base_client._connect = mock.Mock(
            side_effect=functools.partial(setattr, base_client, "sock", sock)
        )
        return base_client

    def make_client(self, mock_socket_values, **kwargs):
        """
        Creates a RetryingClient that will respond with the given values,
        configured using kwargs.
        """
        # Create a base client to wrap.
        base_client = self.make_base_client(mock_socket_values=mock_socket_values)

        # Wrap the client in the retrying class, and pass kwargs on.
        client = RetryingClient(base_client, **kwargs)
        return client

    # Start testing.
    def test_constructor_default(self):
        base_client = self.make_base_client([])
        RetryingClient(base_client)

        with pytest.raises(TypeError):
            RetryingClient()

    def test_constructor_attempts(self):
        base_client = self.make_base_client([])
        rc = RetryingClient(base_client, attempts=1)
        assert rc._attempts == 1

        with pytest.raises(ValueError):
            RetryingClient(base_client, attempts=0)

    def test_constructor_retry_for(self):
        base_client = self.make_base_client([])

        # Try none/default.
        rc = RetryingClient(base_client, retry_for=None)
        assert rc._retry_for == tuple()

        # Try with tuple.
        rc = RetryingClient(base_client, retry_for=tuple([Exception]))
        assert rc._retry_for == tuple([Exception])

        # Try with list.
        rc = RetryingClient(base_client, retry_for=[Exception])
        assert rc._retry_for == tuple([Exception])

        # Try with multi element list.
        rc = RetryingClient(base_client, retry_for=[Exception, IOError])
        assert rc._retry_for == (Exception, IOError)

        # With string?
        with pytest.raises(ValueError):
            RetryingClient(base_client, retry_for="haha!")

        # With collection of string and exceptions?
        with pytest.raises(ValueError):
            RetryingClient(base_client, retry_for=[Exception, str])

    def test_constructor_do_no_retry_for(self):
        base_client = self.make_base_client([])

        # Try none/default.
        rc = RetryingClient(base_client, do_not_retry_for=None)
        assert rc._do_not_retry_for == tuple()

        # Try with tuple.
        rc = RetryingClient(base_client, do_not_retry_for=tuple([Exception]))
        assert rc._do_not_retry_for == tuple([Exception])

        # Try with list.
        rc = RetryingClient(base_client, do_not_retry_for=[Exception])
        assert rc._do_not_retry_for == tuple([Exception])

        # Try with multi element list.
        rc = RetryingClient(base_client, do_not_retry_for=[Exception, IOError])
        assert rc._do_not_retry_for == (Exception, IOError)

        # With string?
        with pytest.raises(ValueError):
            RetryingClient(base_client, do_not_retry_for="haha!")

        # With collection of string and exceptions?
        with pytest.raises(ValueError):
            RetryingClient(base_client, do_not_retry_for=[Exception, str])

    def test_constructor_both_filters(self):
        base_client = self.make_base_client([])

        # Try none/default.
        rc = RetryingClient(base_client, retry_for=None, do_not_retry_for=None)
        assert rc._retry_for == tuple()
        assert rc._do_not_retry_for == tuple()

        # Try a valid config.
        rc = RetryingClient(
            base_client,
            retry_for=[Exception, IOError],
            do_not_retry_for=[ValueError, MemcacheUnknownError],
        )
        assert rc._retry_for == (Exception, IOError)
        assert rc._do_not_retry_for == (ValueError, MemcacheUnknownError)

        # Try with overlapping filters
        with pytest.raises(ValueError):
            rc = RetryingClient(
                base_client,
                retry_for=[Exception, IOError, MemcacheUnknownError],
                do_not_retry_for=[ValueError, MemcacheUnknownError],
            )

    def test_dir_passthrough(self):
        base = self.make_base_client([])
        client = RetryingClient(base)

        assert dir(base) == dir(client)

    def test_retry_dict_set_is_supported(self):
        client = self.make_client([b"UNKNOWN\r\n", b"STORED\r\n"])
        client[b"key"] = b"value"

    def test_retry_dict_get_is_supported(self):
        client = self.make_client(
            [b"UNKNOWN\r\n", b"VALUE key 0 5\r\nvalue\r\nEND\r\n"]
        )
        assert client[b"key"] == b"value"

    def test_retry_dict_get_not_found_is_supported(self):
        client = self.make_client([b"UNKNOWN\r\n", b"END\r\n"])

        with pytest.raises(KeyError):
            client[b"key"]

    def test_retry_dict_del_is_supported(self):
        client = self.make_client([b"UNKNOWN\r\n", b"DELETED\r\n"])
        del client[b"key"]

    def test_retry_get_found(self):
        client = self.make_client(
            [b"UNKNOWN\r\n", b"VALUE key 0 5\r\nvalue\r\nEND\r\n"], attempts=2
        )
        result = client.get("key")
        assert result == b"value"

    def test_retry_get_not_found(self):
        client = self.make_client([b"UNKNOWN\r\n", b"END\r\n"], attempts=2)
        result = client.get("key")
        assert result is None

    def test_retry_get_exception(self):
        client = self.make_client([b"UNKNOWN\r\n", b"UNKNOWN\r\n"], attempts=2)
        with pytest.raises(MemcacheUnknownError):
            client.get("key")

    def test_retry_set_success(self):
        client = self.make_client([b"UNKNOWN\r\n", b"STORED\r\n"], attempts=2)
        result = client.set("key", "value", noreply=False)
        assert result is True

    def test_retry_set_fail(self):
        client = self.make_client(
            [b"UNKNOWN\r\n", b"UNKNOWN\r\n", b"STORED\r\n"], attempts=2
        )
        with pytest.raises(MemcacheUnknownError):
            client.set("key", "value", noreply=False)

    def test_no_retry(self):
        client = self.make_client(
            [b"UNKNOWN\r\n", b"VALUE key 0 5\r\nvalue\r\nEND\r\n"], attempts=1
        )

        with pytest.raises(MemcacheUnknownError):
            client.get("key")

    def test_retry_for_exception_success(self):
        # Test that we retry for the exception specified.
        client = self.make_client(
            [MemcacheClientError("Whoops."), b"VALUE key 0 5\r\nvalue\r\nEND\r\n"],
            attempts=2,
            retry_for=tuple([MemcacheClientError]),
        )
        result = client.get("key")
        assert result == b"value"

    def test_retry_for_exception_fail(self):
        # Test that we do not retry for unapproved exception.
        client = self.make_client(
            [MemcacheUnknownError("Whoops."), b"VALUE key 0 5\r\nvalue\r\nEND\r\n"],
            attempts=2,
            retry_for=tuple([MemcacheClientError]),
        )

        with pytest.raises(MemcacheUnknownError):
            client.get("key")

    def test_do_not_retry_for_exception_success(self):
        # Test that we retry for exceptions not specified.
        client = self.make_client(
            [MemcacheClientError("Whoops."), b"VALUE key 0 5\r\nvalue\r\nEND\r\n"],
            attempts=2,
            do_not_retry_for=tuple([MemcacheUnknownError]),
        )
        result = client.get("key")
        assert result == b"value"

    def test_do_not_retry_for_exception_fail(self):
        # Test that we do not retry for the exception specified.
        client = self.make_client(
            [MemcacheClientError("Whoops."), b"VALUE key 0 5\r\nvalue\r\nEND\r\n"],
            attempts=2,
            do_not_retry_for=tuple([MemcacheClientError]),
        )

        with pytest.raises(MemcacheClientError):
            client.get("key")

    def test_both_exception_filters(self):
        # Test interaction between both exception filters.
        client = self.make_client(
            [
                MemcacheClientError("Whoops."),
                b"VALUE key 0 5\r\nvalue\r\nEND\r\n",
                MemcacheUnknownError("Whoops."),
                b"VALUE key 0 5\r\nvalue\r\nEND\r\n",
            ],
            attempts=2,
            retry_for=tuple([MemcacheClientError]),
            do_not_retry_for=tuple([MemcacheUnknownError]),
        )

        # Check that we succeed where allowed.
        result = client.get("key")
        assert result == b"value"

        # Check that no retries are attempted for the banned exception.
        with pytest.raises(MemcacheUnknownError):
            client.get("key")
