# Copyright 2012 Pinterest.com
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import collections
import errno
import functools
import ipaddress
import json
import os
import platform
from unittest import mock
import socket
import unittest

import pytest

from pymemcache.client.base import (
    PooledClient,
    Client,
    normalize_server_spec,
    KeepaliveOpts,
    check_key_helper,
)
from pymemcache.exceptions import (
    MemcacheClientError,
    MemcacheServerError,
    MemcacheUnexpectedCloseError,
    MemcacheUnknownCommandError,
    MemcacheUnknownError,
    MemcacheIllegalInputError,
)

from pymemcache import pool
from pymemcache.test.utils import MockMemcacheClient


def is_ipv6(address):
    try:
        return ipaddress.ip_address(address).version == 6
    except ValueError:
        # Fail to parse as valid ip address
        return False


@pytest.mark.parametrize(
    "key,allow_unicode_keys,key_prefix,ex_exception,ex_excinfo",
    [
        ("b" * 251, True, b"", MemcacheIllegalInputError, "Key is too long"),
        ("foo bar", True, b"", MemcacheIllegalInputError, "Key contains whitespace"),
        ("\00", True, b"", MemcacheIllegalInputError, "Key contains null"),
        (None, True, b"", TypeError, None),
    ],
)
@pytest.mark.unit()
def test_check_key_helper_failing_conditions(
    key, allow_unicode_keys, key_prefix, ex_exception, ex_excinfo
):

    with pytest.raises(ex_exception) as excinfo:
        check_key_helper(key, allow_unicode_keys, key_prefix)

    # Allow to ignore the excinfo value. Different implementation (2.7,
    # pypy, 3.x) comes with various error messages for the same thing.
    # We just check the kind of the exception.
    if ex_excinfo:
        assert ex_excinfo in str(excinfo.value)


@pytest.mark.unit()
def test_check_key_helper():
    assert check_key_helper(b"key", True, b"") == b"key"
    assert check_key_helper("key", True) == b"key"
    assert isinstance(check_key_helper(b"key", True), bytes)
    assert check_key_helper("", True) == b""


class MockSocket:
    def __init__(self, recv_bufs, connect_failure=None, close_failure=None):
        self.recv_bufs = collections.deque(recv_bufs)
        self.send_bufs = []
        self.closed = False
        self.timeouts = []
        self.connect_failure = connect_failure
        self.close_failure = close_failure
        self.connections = []
        self.socket_options = []

    @property
    def family(self):
        any_ipv6 = any(is_ipv6(c[0]) for c in self.connections)
        return socket.AF_INET6 if any_ipv6 else socket.AF_INET

    def sendall(self, value):
        self.send_bufs.append(value)

    def close(self):
        if isinstance(self.close_failure, Exception):
            raise self.close_failure
        self.closed = True

    def recv(self, size):
        value = self.recv_bufs.popleft()
        if isinstance(value, Exception):
            raise value
        return value

    def settimeout(self, timeout):
        self.timeouts.append(timeout)

    def connect(self, server):
        if isinstance(self.connect_failure, Exception):
            raise self.connect_failure
        self.connections.append(server)

    def setsockopt(self, level, option, value):
        self.socket_options.append((level, option, value))


class MockUnixSocketServer:
    def __init__(self, socket_path):
        if os.path.exists(socket_path):
            os.remove(socket_path)
        self.socket_path = socket_path
        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

    def __enter__(self):
        self.socket.bind(self.socket_path)
        self.socket.listen(1)
        return self.socket

    def __exit__(self, *args):
        self.socket.close()
        os.remove(self.socket_path)


class MockSocketModule:
    def __init__(self, connect_failure=None, close_failure=None):
        self.connect_failure = connect_failure
        self.close_failure = close_failure
        self.sockets = []

    def socket(self, family, type, proto=0, fileno=None):
        socket = MockSocket(
            [], connect_failure=self.connect_failure, close_failure=self.close_failure
        )
        self.sockets.append(socket)
        return socket

    def getaddrinfo(self, host, port, family=0, type=0, proto=0, flags=0):
        family = family or (socket.AF_INET6 if is_ipv6(host) else socket.AF_INET)
        type = type or socket.SOCK_STREAM
        proto = proto or socket.IPPROTO_TCP
        sockaddr = (
            ("::1", 11211, 0, 0) if family == socket.AF_INET6 else ("127.0.0.1", 11211)
        )
        return [(family, type, proto, "", sockaddr)]

    def __getattr__(self, name):
        return getattr(socket, name)


class CustomizedClient(Client):
    def _extract_value(self, expect_cas, line, buf, remapped_keys, prefixed_keys):
        return b"key", b"value", b"END\r\n"


@pytest.mark.unit()
class ClientTestMixin:
    def make_client(self, mock_socket_values, **kwargs):
        client = Client("localhost", **kwargs)
        # mock out client._connect() rather than hard-setting client.sock to
        # ensure methods are checking whether self.sock is None before
        # attempting to use it
        sock = MockSocket(list(mock_socket_values))
        client._connect = mock.Mock(
            side_effect=functools.partial(setattr, client, "sock", sock)
        )
        return client

    def make_customized_client(self, mock_socket_values, **kwargs):
        client = CustomizedClient("localhost", **kwargs)
        # mock out client._connect() rather than hard-setting client.sock to
        # ensure methods are checking whether self.sock is None before
        # attempting to use it
        sock = MockSocket(list(mock_socket_values))
        client._connect = mock.Mock(
            side_effect=functools.partial(setattr, client, "sock", sock)
        )
        return client

    def test_set_success(self):
        client = self.make_client([b"STORED\r\n"])
        result = client.set(b"key", b"value", noreply=False)
        assert result is True

        # unit test for encoding passed in __init__()
        client = self.make_client([b"STORED\r\n"], encoding="utf-8")
        result = client.set(b"key", b"value", noreply=False)
        assert result is True

        # unit test for set operation with parameter flags
        client = self.make_client([b"STORED\r\n"], encoding="utf-8")
        result = client.set(b"key", b"value", noreply=False, flags=0x00000030)
        assert result is True

    def test_set_unicode_key(self):
        client = self.make_client([b""])

        def _set():
            client.set("\u0FFF", b"value", noreply=False)

        with pytest.raises(MemcacheIllegalInputError):
            _set()

    def test_set_unicode_key_ok(self):
        client = self.make_client([b"STORED\r\n"], allow_unicode_keys=True)

        result = client.set("\u0FFF", b"value", noreply=False)
        assert result is True

    def test_set_unicode_key_ok_snowman(self):
        client = self.make_client([b"STORED\r\n"], allow_unicode_keys=True)

        result = client.set("my☃", b"value", noreply=False)
        assert result is True

    def test_set_unicode_char_in_middle_of_key(self):
        client = self.make_client([b"STORED\r\n"])

        def _set():
            client.set("helloworld_\xb1901520_%c3", b"value", noreply=False)

        with pytest.raises(MemcacheIllegalInputError):
            _set()

    def test_set_unicode_char_in_middle_of_key_snowman(self):
        client = self.make_client([b"STORED\r\n"])

        def _set():
            client.set("my☃", b"value", noreply=False)

        with pytest.raises(MemcacheIllegalInputError):
            _set()

    def test_set_unicode_value(self):
        client = self.make_client([b""])

        def _set():
            client.set(b"key", "\u0FFF", noreply=False)

        with pytest.raises(MemcacheIllegalInputError):
            _set()

    def test_set_unicode_char_in_middle_of_key_ok(self):
        client = self.make_client([b"STORED\r\n"], allow_unicode_keys=True)

        result = client.set("helloworld_\xb1901520_%c3", b"value", noreply=False)
        assert result is True

    def test_set_noreply(self):
        client = self.make_client([])
        result = client.set(b"key", b"value", noreply=True)
        assert result is True

        # unit test for encoding passed in __init__()
        client = self.make_client([], encoding="utf-8")
        result = client.set(b"key", b"value", noreply=True)
        assert result is True

    def test_set_many_success(self):
        client = self.make_client([b"STORED\r\n"])
        result = client.set_many({b"key": b"value"}, noreply=False)
        assert result == []

        # unit test for encoding passed in __init__()
        client = self.make_client([b"STORED\r\n"], encoding="utf-8")
        result = client.set_many({b"key": b"value"}, noreply=False)
        assert result == []

    def test_set_multi_success(self):
        # Should just map to set_many
        client = self.make_client([b"STORED\r\n"])
        result = client.set_multi({b"key": b"value"}, noreply=False)
        assert result == []

        # unit test for encoding passed in __init__()
        client = self.make_client([b"STORED\r\n"], encoding="utf-8")
        result = client.set_multi({b"key": b"value"}, noreply=False)
        assert result == []

    def test_add_stored(self):
        client = self.make_client([b"STORED\r", b"\n"])
        result = client.add(b"key", b"value", noreply=False)
        assert result is True

        # unit test for encoding passed in __init__()
        client = self.make_client([b"STORED\r", b"\n"], encoding="utf-8")
        result = client.add(b"key", b"value", noreply=False)
        assert result is True

    def test_add_not_stored(self):
        client = self.make_client(
            [b"STORED\r", b"\n", b"NOT_", b"STOR", b"ED", b"\r\n"]
        )
        client.add(b"key", b"value", noreply=False)
        result = client.add(b"key", b"value", noreply=False)
        assert result is False

        # unit test for encoding passed in __init__()
        client = self.make_client(
            [b"STORED\r", b"\n", b"NOT_", b"STOR", b"ED", b"\r\n"], encoding="utf-8"
        )
        client.add(b"key", b"value", noreply=False)
        result = client.add(b"key", b"value", noreply=False)
        assert result is False

    def test_get_not_found(self):
        client = self.make_client([b"END\r\n"])
        result = client.get(b"key")
        assert result is None

        # Unit test for customized client (override _extract_value)
        client = self.make_customized_client([b"END\r\n"])
        result = client.get(b"key")
        assert result is None

    def test_space_key(self):
        client = self.make_client([b""])
        with pytest.raises(MemcacheIllegalInputError):
            client.get(b"space key")

        with pytest.raises(MemcacheIllegalInputError):
            client.set(b"space key", b"value")

    def test_get_not_found_default(self):
        client = self.make_client([b"END\r\n"])
        result = client.get(b"key", default="foobar")
        assert result == "foobar"

        # Unit test for customized client (override _extract_value)
        client = self.make_customized_client([b"END\r\n"])
        result = client.get(b"key", default="foobar")
        assert result == "foobar"

    def test_get_ignore_exc_default(self):
        client = self.make_client([b"INVALID DATA\r\n"], ignore_exc=True)
        result = client.get(b"key", default="foobar")
        assert result == "foobar"

        # Unit test for customized client (override _extract_value)
        client = self.make_client([b"INVALID DATA\r\n"], ignore_exc=True)
        result = client.get(b"key", default="foobar")
        assert result == "foobar"

    def test_get_found(self):
        client = self.make_client(
            [
                b"STORED\r\n",
                b"VALUE key 0 5\r\nvalue\r\nEND\r\n",
            ]
        )
        client.set(b"key", b"value", noreply=False)
        result = client.get(b"key")
        assert result == b"value"

        # Unit test for customized client (override _extract_value)
        client = self.make_customized_client(
            [
                b"STORED\r\n",
                b"VALUE key 0 5\r\nvalue\r\nEND\r\n",
            ]
        )
        client.set(b"key", b"value", noreply=False)
        result = client.get(b"key")
        assert result == b"value"

    def test_get_many_none_found(self):
        client = self.make_client([b"END\r\n"])
        result = client.get_many([b"key1", b"key2"])
        assert result == {}

    def test_get_multi_none_found(self):
        client = self.make_client([b"END\r\n"])
        result = client.get_multi([b"key1", b"key2"])
        assert result == {}

    def test_get_many_some_found(self):
        client = self.make_client(
            [
                b"STORED\r\n",
                b"VALUE key1 0 6\r\nvalue1\r\nEND\r\n",
            ]
        )
        client.set(b"key1", b"value1", noreply=False)
        result = client.get_many([b"key1", b"key2"])
        assert result == {b"key1": b"value1"}

    def test_get_many_all_found(self):
        client = self.make_client(
            [
                b"STORED\r\n",
                b"STORED\r\n",
                b"VALUE key1 0 6\r\nvalue1\r\n",
                b"VALUE key2 0 6\r\nvalue2\r\nEND\r\n",
            ]
        )
        client.set(b"key1", b"value1", noreply=False)
        client.set(b"key2", b"value2", noreply=False)
        result = client.get_many([b"key1", b"key2"])
        assert result == {b"key1": b"value1", b"key2": b"value2"}

    def test_get_unicode_key(self):
        client = self.make_client([b""])

        def _get():
            client.get("\u0FFF")

        with pytest.raises(MemcacheIllegalInputError):
            _get()

    def test_delete_not_found(self):
        client = self.make_client([b"NOT_FOUND\r\n"])
        result = client.delete(b"key", noreply=False)
        assert result is False

    def test_delete_found(self):
        client = self.make_client([b"STORED\r", b"\n", b"DELETED\r\n"])
        client.add(b"key", b"value", noreply=False)
        result = client.delete(b"key", noreply=False)
        assert result is True

    def test_delete_noreply(self):
        client = self.make_client([])
        result = client.delete(b"key", noreply=True)
        assert result is True

    def test_delete_many_no_keys(self):
        client = self.make_client([])
        result = client.delete_many([], noreply=False)
        assert result is True

    def test_delete_many_none_found(self):
        client = self.make_client([b"NOT_FOUND\r\n"])
        result = client.delete_many([b"key"], noreply=False)
        assert result is True

    def test_delete_many_found(self):
        client = self.make_client([b"STORED\r", b"\n", b"DELETED\r\n"])
        client.add(b"key", b"value", noreply=False)
        result = client.delete_many([b"key"], noreply=False)
        assert result is True

    def test_delete_many_some_found(self):
        client = self.make_client([b"STORED\r\n", b"DELETED\r\n", b"NOT_FOUND\r\n"])
        client.add(b"key", b"value", noreply=False)
        result = client.delete_many([b"key", b"key2"], noreply=False)
        assert result is True

    def test_delete_multi_some_found(self):
        client = self.make_client([b"STORED\r\n", b"DELETED\r\n", b"NOT_FOUND\r\n"])
        client.add(b"key", b"value", noreply=False)
        result = client.delete_multi([b"key", b"key2"], noreply=False)
        assert result is True

    def test_incr_not_found(self):
        client = self.make_client([b"NOT_FOUND\r\n"])
        result = client.incr(b"key", 1, noreply=False)
        assert result is None

    def test_incr_found(self):
        client = self.make_client([b"STORED\r\n", b"1\r\n"])
        client.set(b"key", 0, noreply=False)
        result = client.incr(b"key", 1, noreply=False)
        assert result == 1

    def test_incr_noreply(self):
        client = self.make_client([b"STORED\r\n"])
        client.set(b"key", 0, noreply=False)

        client = self.make_client([])
        result = client.incr(b"key", 1, noreply=True)
        assert result is None

    def test_decr_not_found(self):
        client = self.make_client([b"NOT_FOUND\r\n"])
        result = client.decr(b"key", 1, noreply=False)
        assert result is None

    def test_decr_found(self):
        client = self.make_client([b"STORED\r\n", b"1\r\n"])
        client.set(b"key", 2, noreply=False)
        result = client.decr(b"key", 1, noreply=False)
        assert result == 1


class TestClient(ClientTestMixin, unittest.TestCase):

    Client = Client

    def test_append_stored(self):
        client = self.make_client([b"STORED\r\n"])
        result = client.append(b"key", b"value", noreply=False)
        assert result is True

        # unit test for encoding passed in __init__()
        client = self.make_client([b"STORED\r\n"], encoding="utf-8")
        result = client.append(b"key", b"value", noreply=False)
        assert result is True

    def test_prepend_stored(self):
        client = self.make_client([b"STORED\r\n"])
        result = client.prepend(b"key", b"value", noreply=False)
        assert result is True

        # unit test for encoding passed in __init__()
        client = self.make_client([b"STORED\r\n"], encoding="utf-8")
        result = client.prepend(b"key", b"value", noreply=False)
        assert result is True

    def test_cas_malformed(self):
        client = self.make_client([b"STORED\r\n"])
        with pytest.raises(MemcacheIllegalInputError):
            client.cas(b"key", b"value", None, noreply=False)

        with pytest.raises(MemcacheIllegalInputError):
            client.cas(b"key", b"value", "nonintegerstring", noreply=False)

        with pytest.raises(MemcacheIllegalInputError):
            # even a space makes it a noninteger string
            client.cas(b"key", b"value", "123 ", noreply=False)

        with pytest.raises(MemcacheIllegalInputError):
            # non-ASCII digit
            client.cas(b"key", b"value", "⁰", noreply=False)

    def test_cas_stored(self):
        client = self.make_client([b"STORED\r\n"])
        result = client.cas(b"key", b"value", b"123", noreply=False)
        assert result is True

        # unit test for encoding passed in __init__()
        client = self.make_client([b"STORED\r\n"], encoding="utf-8")
        result = client.cas(b"key", b"value", b"123", noreply=False)
        assert result is True

    def test_cas_exists(self):
        client = self.make_client([b"EXISTS\r\n"])
        result = client.cas(b"key", b"value", b"123", noreply=False)
        assert result is False

        # unit test for encoding passed in __init__()
        client = self.make_client([b"EXISTS\r\n"], encoding="utf-8")
        result = client.cas(b"key", b"value", b"123", noreply=False)
        assert result is False

    def test_cas_not_found(self):
        client = self.make_client([b"NOT_FOUND\r\n"])
        result = client.cas(b"key", b"value", b"123", noreply=False)
        assert result is None

        # unit test for encoding passed in __init__()
        client = self.make_client([b"NOT_FOUND\r\n"], encoding="utf-8")
        result = client.cas(b"key", b"value", b"123", noreply=False)
        assert result is None

    def test_cr_nl_boundaries(self):
        client = self.make_client(
            [
                b"VALUE key1 0 6\r",
                b"\nvalue1\r\n" b"VALUE key2 0 6\r\n",
                b"value2\r\n" b"END\r\n",
            ]
        )
        result = client.get_many([b"key1", b"key2"])
        assert result == {b"key1": b"value1", b"key2": b"value2"}

        client = self.make_client(
            [
                b"VALUE key1 0 6\r\n",
                b"value1\r",
                b"\nVALUE key2 0 6\r\n",
                b"value2\r\n",
                b"END\r\n",
            ]
        )
        result = client.get_many([b"key1", b"key2"])
        assert result == {b"key1": b"value1", b"key2": b"value2"}

        client = self.make_client(
            [
                b"VALUE key1 0 6\r\n",
                b"value1\r\n",
                b"VALUE key2 0 6\r",
                b"\nvalue2\r\n",
                b"END\r\n",
            ]
        )
        result = client.get_many([b"key1", b"key2"])
        assert result == {b"key1": b"value1", b"key2": b"value2"}

        client = self.make_client(
            [
                b"VALUE key1 0 6\r\n",
                b"value1\r\n",
                b"VALUE key2 0 6\r\n",
                b"value2\r",
                b"\nEND\r\n",
            ]
        )
        result = client.get_many([b"key1", b"key2"])
        assert result == {b"key1": b"value1", b"key2": b"value2"}

        client = self.make_client(
            [
                b"VALUE key1 0 6\r\n",
                b"value1\r\n",
                b"VALUE key2 0 6\r\n",
                b"value2\r\n",
                b"END\r",
                b"\n",
            ]
        )
        result = client.get_many([b"key1", b"key2"])
        assert result == {b"key1": b"value1", b"key2": b"value2"}

        client = self.make_client(
            [
                b"VALUE key1 0 6\r",
                b"\nvalue1\r",
                b"\nVALUE key2 0 6\r",
                b"\nvalue2\r",
                b"\nEND\r",
                b"\n",
            ]
        )
        result = client.get_many([b"key1", b"key2"])
        assert result == {b"key1": b"value1", b"key2": b"value2"}

    def test_delete_exception(self):
        client = self.make_client([Exception("fail")])

        def _delete():
            client.delete(b"key", noreply=False)

        with pytest.raises(Exception):
            _delete()

        assert client.sock is None

    def test_flush_all(self):
        client = self.make_client([b"OK\r\n"])
        result = client.flush_all(noreply=False)
        assert result is True

    def test_incr_exception(self):
        client = self.make_client([Exception("fail")])

        def _incr():
            client.incr(b"key", 1)

        with pytest.raises(Exception):
            _incr()

        assert client.sock is None

    def test_get_error(self):
        client = self.make_client([b"ERROR\r\n"])

        def _get():
            client.get(b"key")

        with pytest.raises(MemcacheUnknownCommandError):
            _get()

    def test_get_recv_chunks(self):
        client = self.make_client(
            [b"VALUE key", b" 0 5\r", b"\nvalue", b"\r\n", b"END", b"\r", b"\n"]
        )
        result = client.get(b"key")
        assert result == b"value"

    def test_get_unknown_error(self):
        client = self.make_client([b"foobarbaz\r\n"])

        def _get():
            client.get(b"key")

        with pytest.raises(MemcacheUnknownError):
            _get()

    def test_gets_not_found(self):
        client = self.make_client([b"END\r\n"])
        result = client.gets(b"key")
        assert result == (None, None)

    def test_gets_not_found_defaults(self):
        client = self.make_client([b"END\r\n"])
        result = client.gets(b"key", default="foo", cas_default="bar")
        assert result == ("foo", "bar")

    def test_gets_found(self):
        client = self.make_client([b"VALUE key 0 5 10\r\nvalue\r\nEND\r\n"])
        result = client.gets(b"key")
        assert result == (b"value", b"10")

    def test_gets_many_none_found(self):
        client = self.make_client([b"END\r\n"])
        result = client.gets_many([b"key1", b"key2"])
        assert result == {}

    def test_gets_many_some_found(self):
        client = self.make_client([b"VALUE key1 0 6 11\r\nvalue1\r\nEND\r\n"])
        result = client.gets_many([b"key1", b"key2"])
        assert result == {b"key1": (b"value1", b"11")}

    def test_touch_not_found(self):
        client = self.make_client([b"NOT_FOUND\r\n"])
        result = client.touch(b"key", noreply=False)
        assert result is False

    def test_touch_found(self):
        client = self.make_client([b"TOUCHED\r\n"])
        result = client.touch(b"key", noreply=False)
        assert result is True

    def test_quit(self):
        client = self.make_client([])
        result = client.quit()
        assert result is None
        assert client.sock is None

    def test_shutdown(self):
        client = self.make_client([MemcacheUnexpectedCloseError("shutdown")])
        result = client.shutdown()
        assert result is None

    def test_shutdown_disabled(self):
        def _shutdown():
            client = self.make_client([b"ERROR: shutdown not enabled\r\n"])
            client.shutdown()

        with pytest.raises(MemcacheUnknownCommandError):
            _shutdown()

    def test_replace_stored(self):
        client = self.make_client([b"STORED\r\n"])
        result = client.replace(b"key", b"value", noreply=False)
        assert result is True

        # unit test for encoding passed in __init__()
        client = self.make_client([b"STORED\r\n"], encoding="utf-8")
        result = client.replace(b"key", b"value", noreply=False)
        assert result is True

    def test_replace_not_stored(self):
        client = self.make_client([b"NOT_STORED\r\n"])
        result = client.replace(b"key", b"value", noreply=False)
        assert result is False

        # unit test for encoding passed in __init__
        client = self.make_client([b"NOT_STORED\r\n"], encoding="utf-8")
        result = client.replace(b"key", b"value", noreply=False)
        assert result is False

    def test_serialization(self):
        class JsonSerde:
            def serialize(self, key, value):
                return json.dumps(value).encode("ascii"), 0

            def deserialize(self, key, value, flags):
                return json.loads(value.decode("ascii"))

        client = self.make_client([b"STORED\r\n"], serde=JsonSerde())
        client.set("key", {"c": "d"})
        assert client.sock.send_bufs == [b'set key 0 0 10 noreply\r\n{"c": "d"}\r\n']

    def test_serialization_flags(self):
        def _ser(key, value):
            return value, 1 if isinstance(value, int) else 0

        client = self.make_client([b"STORED\r\n", b"STORED\r\n"], serializer=_ser)
        client.set_many(
            collections.OrderedDict([(b"a", b"s"), (b"b", 0)]), noreply=False
        )
        assert client.sock.send_bufs == [b"set a 0 0 1\r\ns\r\nset b 1 0 1\r\n0\r\n"]

    def test_serialization_overridden_flags(self):
        def _ser(key, value):
            return value, 1 if isinstance(value, int) else 0

        client = self.make_client([b"STORED\r\n", b"STORED\r\n"], serializer=_ser)
        client.set_many(
            collections.OrderedDict([(b"a", b"s"), (b"b", 0)]), noreply=False, flags=5
        )
        assert client.sock.send_bufs == [b"set a 5 0 1\r\ns\r\nset b 5 0 1\r\n0\r\n"]

    def test_explicit_flags(self):
        client = self.make_client([b"STORED\r\n", b"STORED\r\n"])
        client.set_many(
            collections.OrderedDict([(b"a", b"s"), (b"b", 0)]), noreply=False, flags=5
        )
        assert client.sock.send_bufs == [b"set a 5 0 1\r\ns\r\nset b 5 0 1\r\n0\r\n"]

    def test_set_socket_handling(self):
        client = self.make_client([b"STORED\r\n"])
        result = client.set(b"key", b"value", noreply=False)
        assert result is True
        assert client.sock.closed is False
        assert len(client.sock.send_bufs) == 1

    def test_set_error(self):
        client = self.make_client([b"ERROR\r\n"])

        def _set():
            client.set(b"key", b"value", noreply=False)

        with pytest.raises(MemcacheUnknownCommandError):
            _set()

    def test_set_exception(self):
        client = self.make_client([Exception("fail")])

        def _set():
            client.set(b"key", b"value", noreply=False)

        with pytest.raises(Exception):
            _set()

        assert client.sock is None

    def test_set_client_error(self):
        client = self.make_client([b"CLIENT_ERROR some message\r\n"])

        def _set():
            client.set("key", "value", noreply=False)

        with pytest.raises(MemcacheClientError):
            _set()

    def test_set_server_error(self):
        client = self.make_client([b"SERVER_ERROR some message\r\n"])

        def _set():
            client.set(b"key", b"value", noreply=False)

        with pytest.raises(MemcacheServerError):
            _set()

    def test_closing_socket_on_unexpected_closed_error(self):
        client = self.make_client(
            [
                b"VALUE ",
                MemcacheUnexpectedCloseError("foo bar"),
            ]
        )

        def _set():
            client.set(b"key", b"value", noreply=False)

        with pytest.raises(MemcacheUnexpectedCloseError):
            _set()

        assert client.sock is None

    def test_set_unknown_error(self):
        client = self.make_client([b"foobarbaz\r\n"])

        def _set():
            client.set(b"key", b"value", noreply=False)

        with pytest.raises(MemcacheUnknownError):
            _set()

    def test_set_key_with_space(self):
        client = self.make_client([b""])

        def _set():
            client.set(b"key has space", b"value", noreply=False)

        with pytest.raises(MemcacheIllegalInputError):
            _set()

    def test_set_key_with_newline(self):
        client = self.make_client([b""])

        def _set():
            client.set(b"key\n", b"value", noreply=False)

        with pytest.raises(MemcacheIllegalInputError):
            _set()

    def test_set_key_with_carriage_return(self):
        client = self.make_client([b""])

        def _set():
            client.set(b"key\r", b"value", noreply=False)

        with pytest.raises(MemcacheIllegalInputError):
            _set()

    def test_set_key_with_null_character(self):
        client = self.make_client([b""])

        def _set():
            client.set(b"key\00", b"value", noreply=False)

        with pytest.raises(MemcacheIllegalInputError):
            _set()

    def test_set_key_with_noninteger_expire(self):
        client = self.make_client([b""])

        class _OneLike:
            """object that looks similar to the int 1"""

            def __str__(self):
                return "1"

        for noreply in (True, False):
            for expire in (1.5, _OneLike(), "1"):

                def _set():
                    client.set(b"finekey", b"finevalue", noreply=noreply, expire=expire)

                with pytest.raises(MemcacheIllegalInputError):
                    _set()

    def test_set_many_socket_handling(self):
        client = self.make_client([b"STORED\r\n"])
        result = client.set_many({b"key": b"value"}, noreply=False)
        assert result == []
        assert client.sock.closed is False
        assert len(client.sock.send_bufs) == 1

        # unit test for encoding passed in __init__()
        client = self.make_client([b"STORED\r\n"], encoding="utf-8")
        result = client.set_many({b"key": b"value"}, noreply=False)
        assert result == []
        assert client.sock.closed is False
        assert len(client.sock.send_bufs) == 1

    def test_set_many_exception(self):
        client = self.make_client([b"STORED\r\n", Exception("fail")])

        def _set():
            client.set_many({b"key": b"value", b"other": b"value"}, noreply=False)

        with pytest.raises(Exception):
            _set()

        assert client.sock is None

        # unit test for encoding passed in __init__()
        client = self.make_client([b"STORED\r\n", Exception("fail")], encoding="utf-8")

        def _set():
            client.set_many({b"key": b"value", b"other": b"value"}, noreply=False)

        with pytest.raises(Exception):
            _set()

        assert client.sock is None

    def test_stats(self):
        client = self.make_client([b"STAT fake_stats 1\r\n", b"END\r\n"])
        result = client.stats()
        assert client.sock.send_bufs == [b"stats\r\n"]
        assert result == {b"fake_stats": 1}

    def test_stats_with_args(self):
        client = self.make_client([b"STAT fake_stats 1\r\n", b"END\r\n"])
        result = client.stats("some_arg")
        assert client.sock.send_bufs == [b"stats some_arg\r\n"]
        assert result == {b"fake_stats": 1}

    def test_stats_with_blank_value(self):
        client = self.make_client([b"STAT fake_stats \r\n", b"END\r\n"])
        result = client.stats()
        assert result == {b"fake_stats": b""}

    def test_stats_conversions(self):
        client = self.make_client(
            [
                # Most stats are converted to int
                b"STAT cmd_get 2519\r\n",
                b"STAT cmd_set 3099\r\n",
                b"STAT evictions 939\r\n",
                # Unless they can't be, they remain str
                b"STAT libevent 2.0.19-stable\r\n",
                # Some named stats are explicitly converted
                b"STAT hash_is_expanding 0\r\n",
                b"STAT rusage_user 0.609165\r\n",
                b"STAT rusage_system 0.852791\r\n",
                b"STAT slab_reassign_running 1\r\n",
                b"STAT version 1.4.14\r\n",
                b"STAT umask 777\r\n",
                b"STAT auth_enabled_sasl yes\r\n",
                b"END\r\n",
            ]
        )
        result = client.stats()
        assert client.sock.send_bufs == [b"stats\r\n"]
        expected = {
            b"cmd_get": 2519,
            b"cmd_set": 3099,
            b"evictions": 939,
            b"libevent": b"2.0.19-stable",
            b"hash_is_expanding": False,
            b"rusage_user": 0.609165,
            b"rusage_system": 0.852791,
            b"slab_reassign_running": True,
            b"version": b"1.4.14",
            b"umask": 0o777,
            b"auth_enabled_sasl": True,
        }
        assert result == expected

    def test_stats_cachedump(self):
        client = self.make_client([b"ITEM bob [7 b; 0 s]\r\n", b"END\r\n"])
        result = client.stats("cachedump", "1", "1")
        assert client.sock.send_bufs == [b"stats cachedump 1 1\r\n"]
        assert result == {b"bob": b"[7 b; 0 s]"}

    def test_cache_memlimit(self):
        client = self.make_client([b"OK\r\n"])
        result = client.cache_memlimit(8)
        assert client.sock.send_bufs == [b"cache_memlimit 8\r\n"]
        assert result is True

    def test_python_dict_set_is_supported(self):
        client = self.make_client([b"STORED\r\n"])
        client[b"key"] = b"value"

    def test_python_dict_get_is_supported(self):
        client = self.make_client([b"VALUE key 0 5\r\nvalue\r\nEND\r\n"])
        assert client[b"key"] == b"value"

    def test_python_dict_get_not_found_is_supported(self):
        client = self.make_client([b"END\r\n"])

        def _get():
            client[b"key"]

        with pytest.raises(KeyError):
            _get()

    def test_python_dict_del_is_supported(self):
        client = self.make_client([b"DELETED\r\n"])
        del client[b"key"]

    def test_too_long_key(self):
        client = self.make_client([b"END\r\n"])

        with pytest.raises(MemcacheClientError):
            client.get(b"x" * 251)

    def test_too_long_unicode_key(self):
        client = self.make_client([b"STORED\r\n"], allow_unicode_keys=True)

        with pytest.raises(MemcacheClientError):
            client.get("my☃" * 150)

        with pytest.raises(MemcacheClientError):
            client.get("\u0FFF" * 150)

    def test_key_contains_space(self):
        client = self.make_client([b"END\r\n"])
        with pytest.raises(MemcacheClientError):
            client.get(b"abc xyz")

    def test_key_contains_nonascii(self):
        client = self.make_client([b"END\r\n"])

        with pytest.raises(MemcacheClientError):
            client.get("\u3053\u3093\u306b\u3061\u306f")

    def _default_noreply_false(self, cmd, args, response):
        client = self.make_client(response, default_noreply=False)
        result = getattr(client, cmd)(*args)
        assert result is False

    def _default_noreply_true(self, cmd, args, response):
        client = self.make_client(response, default_noreply=True)
        result = getattr(client, cmd)(*args)
        assert result is True

    def _default_noreply_true_and_empty_list(self, cmd, args, response):
        client = self.make_client(response, default_noreply=True)
        result = getattr(client, cmd)(*args)
        assert result == []

    def test_default_noreply_set(self):
        with pytest.raises(MemcacheUnknownError):
            self._default_noreply_false("set", (b"key", b"value"), [b"UNKNOWN\r\n"])
        self._default_noreply_false("set", (b"key", b"value"), [b"NOT_STORED\r\n"])
        self._default_noreply_true("set", (b"key", b"value"), [b"NOT_STORED\r\n"])

    def test_default_noreply_set_many(self):
        with pytest.raises(MemcacheUnknownError):
            client = self.make_client([b"UNKNOWN\r\n"], default_noreply=False)
            result = client.set_many({b"key": b"value"})
            assert result == [b"key"]
        self._default_noreply_true_and_empty_list(
            "set_many", ({b"key": b"value"},), [b"NOT_STORED\r\n"]
        )

    def test_default_noreply_add(self):
        self._default_noreply_false("add", (b"key", b"value"), [b"NOT_STORED\r\n"])
        self._default_noreply_true("add", (b"key", b"value"), [b"NOT_STORED\r\n"])

    def test_default_noreply_replace(self):
        self._default_noreply_false("replace", (b"key", b"value"), [b"NOT_STORED\r\n"])
        self._default_noreply_true("replace", (b"key", b"value"), [b"NOT_STORED\r\n"])

    def test_default_noreply_append(self):
        self._default_noreply_false("append", (b"key", b"value"), [b"NOT_STORED\r\n"])
        self._default_noreply_true("append", (b"key", b"value"), [b"NOT_STORED\r\n"])

    def test_default_noreply_prepend(self):
        self._default_noreply_false("prepend", (b"key", b"value"), [b"NOT_STORED\r\n"])
        self._default_noreply_true("prepend", (b"key", b"value"), [b"NOT_STORED\r\n"])

    def test_default_noreply_touch(self):
        self._default_noreply_false("touch", (b"key",), [b"NOT_FOUND\r\n"])
        self._default_noreply_true("touch", (b"key",), [b"NOT_FOUND\r\n"])

    def test_default_noreply_flush_all(self):
        self._default_noreply_false("flush_all", (), [b"__FAKE_RESPONSE__\r\n"])
        self._default_noreply_true("flush_all", (), [b"__FAKE_RESPONSE__\r\n"])

    def test_version_success(self):
        client = self.make_client([b"VERSION 1.2.3\r\n"], default_noreply=False)
        result = client.version()
        assert result == b"1.2.3"

    def test_version_exception(self):
        client = self.make_client([b"INVALID DATA\r\n"], default_noreply=False)
        with pytest.raises(MemcacheUnknownError):
            client.version()

    def test_raw_command_default_end_tokens(self):
        client = self.make_client([b"REPLY\r\n", b"REPLY\r\nLEFTOVER"])
        result = client.raw_command(b"misc")
        assert result == b"REPLY"
        result = client.raw_command(b"misc")
        assert result == b"REPLY"

    def test_raw_command_custom_end_tokens(self):
        client = self.make_client(
            [
                b"REPLY\r\nEND\r\n",
                b"REPLY\r\nEND\r\nLEFTOVER",
                b"REPLYEND\r\nLEFTOVER",
                b"REPLY\nLEFTOVER",
            ]
        )
        end_tokens = b"END\r\n"
        result = client.raw_command(b"misc", end_tokens)
        assert result == b"REPLY\r\n"
        result = client.raw_command(b"misc", end_tokens)
        assert result == b"REPLY\r\n"
        result = client.raw_command(b"misc", end_tokens)
        assert result == b"REPLY"
        result = client.raw_command(b"misc", b"\n")
        assert result == b"REPLY"

    def test_raw_command_missing_end_tokens(self):
        client = self.make_client([b"REPLY", b"REPLY"])
        with pytest.raises(IndexError):
            client.raw_command(b"misc")
        with pytest.raises(IndexError):
            client.raw_command(b"misc", b"END\r\n")

    def test_raw_command_empty_end_tokens(self):
        client = self.make_client([b"REPLY"])

        with pytest.raises(IndexError):
            client.raw_command(b"misc", b"")

    def test_raw_command_types(self):
        client = self.make_client(
            [b"REPLY\r\n", b"REPLY\r\n", b"REPLY\r\nLEFTOVER", b"REPLY\r\nLEFTOVER"]
        )
        assert client.raw_command("key") == b"REPLY"
        assert client.raw_command(b"key") == b"REPLY"
        assert client.raw_command("key") == b"REPLY"
        assert client.raw_command(b"key") == b"REPLY"

    def test_send_end_token_types(self):
        client = self.make_client(
            [b"REPLY\r\n", b"REPLY\r\n", b"REPLY\r\nLEFTOVER", b"REPLY\r\nLEFTOVER"]
        )
        assert client.raw_command("key", "\r\n") == b"REPLY"
        assert client.raw_command(b"key", b"\r\n") == b"REPLY"
        assert client.raw_command("key", "\r\n") == b"REPLY"
        assert client.raw_command(b"key", b"\r\n") == b"REPLY"


@pytest.mark.unit()
class TestClientSocketConnect(unittest.TestCase):
    def test_socket_connect_ipv4(self):
        server = ("127.0.0.1", 11211)

        client = Client(server, socket_module=MockSocketModule())
        client._connect()
        assert client.sock.connections == [server]
        assert client.sock.family == socket.AF_INET

        timeout = 2
        connect_timeout = 3
        client = Client(
            server,
            connect_timeout=connect_timeout,
            timeout=timeout,
            socket_module=MockSocketModule(),
        )
        client._connect()
        assert client.sock.timeouts == [connect_timeout, timeout]

        client = Client(server, socket_module=MockSocketModule())
        client._connect()
        assert client.sock.socket_options == []

        client = Client(server, socket_module=MockSocketModule(), no_delay=True)
        client._connect()
        assert client.sock.socket_options == [
            (socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        ]

    def test_socket_connect_ipv6(self):
        server = ("::1", 11211)

        client = Client(server, socket_module=MockSocketModule())
        client._connect()
        assert client.sock.connections == [server + (0, 0)]
        assert client.sock.family == socket.AF_INET6

        timeout = 2
        connect_timeout = 3
        client = Client(
            server,
            connect_timeout=connect_timeout,
            timeout=timeout,
            socket_module=MockSocketModule(),
        )
        client._connect()
        assert client.sock.timeouts == [connect_timeout, timeout]

        client = Client(server, socket_module=MockSocketModule())
        client._connect()
        assert client.sock.socket_options == []

        client = Client(server, socket_module=MockSocketModule(), no_delay=True)
        client._connect()
        assert client.sock.socket_options == [
            (socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        ]

    def test_socket_connect_unix(self):
        server = f"/tmp/pymemcache.{os.getpid()}"

        with MockUnixSocketServer(server):
            client = Client(server)
            client._connect()
            assert client.sock.family == socket.AF_UNIX

    @unittest.skipIf(
        "Linux" != platform.system(), "Socket keepalive only support Linux platforms."
    )
    def test_linux_socket_keepalive(self):
        server = ("::1", 11211)
        try:
            client = Client(
                server,
                socket_module=MockSocketModule(),
                socket_keepalive=KeepaliveOpts(),
            )
            client._connect()
        except SystemError:
            self.fail("SystemError unexpectedly raised")
        with self.assertRaises(ValueError):
            # A KeepaliveOpts object is expected, a ValueError will be raised
            Client(server, socket_module=MockSocketModule(), socket_keepalive=True)

    @mock.patch("platform.system")
    def test_osx_socket_keepalive(self, platform_mock):
        platform_mock.return_value = "Darwin"
        server = ("::1", 11211)
        # For the moment the socket keepalive is only implemented for Linux
        with self.assertRaises(SystemError):
            Client(
                server,
                socket_module=MockSocketModule(),
                socket_keepalive=KeepaliveOpts(),
            )

    @mock.patch("platform.system")
    def test_windows_socket_keepalive(self, platform_mock):
        platform_mock.return_value = "Windows"
        server = ("::1", 11211)
        # For the moment the socket keepalive is only implemented for Linux
        with self.assertRaises(SystemError):
            Client(
                server,
                socket_module=MockSocketModule(),
                socket_keepalive=KeepaliveOpts(),
            )

    def test_socket_connect_closes_on_failure(self):
        server = ("example.com", 11211)

        socket_module = MockSocketModule(connect_failure=OSError())
        client = Client(server, socket_module=socket_module)
        with pytest.raises(OSError):
            client._connect()
        assert len(socket_module.sockets) == 1
        assert socket_module.sockets[0].connections == []
        assert socket_module.sockets[0].closed

    def test_socket_close(self):
        server = ("example.com", 11211)

        client = Client(server, socket_module=MockSocketModule())
        client._connect()
        assert client.sock is not None

        client.close()
        assert client.sock is None

    def test_socket_close_exception(self):
        server = ("example.com", 11211)

        socket_module = MockSocketModule(close_failure=OSError())
        client = Client(server, socket_module=socket_module)
        client._connect()
        assert client.sock is not None

        client.close()
        assert client.sock is None


class TestPooledClient(ClientTestMixin, unittest.TestCase):
    def make_client(self, mock_socket_values, **kwargs):
        mock_client = Client("localhost", **kwargs)
        mock_client.sock = MockSocket(list(mock_socket_values))
        client = PooledClient("localhost", **kwargs)
        client.client_pool = pool.ObjectPool(lambda: mock_client)
        return client

    def _default_noreply_false(self, cmd, args, response):
        client = self.make_client(response, default_noreply=False)
        result = getattr(client, cmd)(*args)
        assert result is False

    def _default_noreply_true(self, cmd, args, response):
        client = self.make_client(response, default_noreply=True)
        result = getattr(client, cmd)(*args)
        assert result is True

    def _default_noreply_true_and_empty_list(self, cmd, args, response):
        client = self.make_client(response, default_noreply=True)
        result = getattr(client, cmd)(*args)
        assert result == []

    def test_default_noreply_set(self):
        with pytest.raises(MemcacheUnknownError):
            self._default_noreply_false("set", (b"key", b"value"), [b"UNKNOWN\r\n"])
        self._default_noreply_false("set", (b"key", b"value"), [b"NOT_STORED\r\n"])
        self._default_noreply_true("set", (b"key", b"value"), [b"NOT_STORED\r\n"])

    def test_default_noreply_set_many(self):
        with pytest.raises(MemcacheUnknownError):
            client = self.make_client([b"UNKNOWN\r\n"], default_noreply=False)
            client.set_many({b"key": b"value"})
        self._default_noreply_true_and_empty_list(
            "set_many", ({b"key": b"value"},), [b"NOT_STORED\r\n"]
        )

    def test_default_noreply_add(self):
        self._default_noreply_false("add", (b"key", b"value"), [b"NOT_STORED\r\n"])
        self._default_noreply_true("add", (b"key", b"value"), [b"NOT_STORED\r\n"])

    def test_default_noreply_replace(self):
        self._default_noreply_false("replace", (b"key", b"value"), [b"NOT_STORED\r\n"])
        self._default_noreply_true("replace", (b"key", b"value"), [b"NOT_STORED\r\n"])

    def test_default_noreply_append(self):
        self._default_noreply_false("append", (b"key", b"value"), [b"NOT_STORED\r\n"])
        self._default_noreply_true("append", (b"key", b"value"), [b"NOT_STORED\r\n"])

    def test_default_noreply_prepend(self):
        self._default_noreply_false("prepend", (b"key", b"value"), [b"NOT_STORED\r\n"])
        self._default_noreply_true("prepend", (b"key", b"value"), [b"NOT_STORED\r\n"])

    def test_default_noreply_touch(self):
        self._default_noreply_false("touch", (b"key",), [b"NOT_FOUND\r\n"])
        self._default_noreply_true("touch", (b"key",), [b"NOT_FOUND\r\n"])

    def test_default_noreply_flush_all(self):
        self._default_noreply_false("flush_all", (), [b"__FAKE_RESPONSE__\r\n"])
        self._default_noreply_true("flush_all", (), [b"__FAKE_RESPONSE__\r\n"])

    def test_custom_client(self):
        class MyClient(Client):
            pass

        client = PooledClient(("host", 11211))
        client.client_class = MyClient
        assert isinstance(client.client_pool.get(), MyClient)


class TestPooledClientIdleTimeout(ClientTestMixin, unittest.TestCase):
    def make_client(self, mock_socket_values, **kwargs):
        mock_client = Client("localhost", **kwargs)
        mock_client.sock = MockSocket(list(mock_socket_values))
        client = PooledClient("localhost", pool_idle_timeout=60, **kwargs)
        client.client_pool = pool.ObjectPool(lambda: mock_client)
        return client

    def test_free_idle(self):
        class Counter:
            count = 0

            def increment(self, obj):
                self.count += 1

        removed = Counter()

        client = self.make_client([b"VALUE key 0 5\r\nvalue\r\nEND\r\n"] * 2)
        client.client_pool._after_remove = removed.increment
        client.client_pool._idle_clock = lambda: 0

        client.set(b"key", b"value")
        assert removed.count == 0
        client.get(b"key")
        assert removed.count == 0

        # Advance clock to beyond the idle timeout.
        client.client_pool._idle_clock = lambda: 61
        client.get(b"key")
        assert removed.count == 1


class TestMockClient(ClientTestMixin, unittest.TestCase):
    def make_client(self, mock_socket_values, **kwargs):
        client = MockMemcacheClient("localhost", **kwargs)
        client.sock = MockSocket(list(mock_socket_values))
        return client

    def test_get_found(self):
        client = self.make_client(
            [
                b"STORED\r\n",
                b"VALUE key 0 5\r\nvalue\r\nEND\r\n",
            ]
        )
        result = client.set(b"key", b"value", noreply=False)
        result = client.get(b"key")
        assert result == b"value"

    def test_deserialization(self):
        class JsonSerde:
            def serialize(self, key, value):
                if isinstance(value, dict):
                    return json.dumps(value).encode("UTF-8"), 1
                return value, 0

            def deserialize(self, key, value, flags):
                if flags == 1:
                    return json.loads(value.decode("UTF-8"))
                return value

        client = self.make_client(
            [
                b"STORED\r\n",
                b"VALUE key1 0 5\r\nhello\r\nEND\r\n",
                b"STORED\r\n",
                b'VALUE key2 0 18\r\n{"hello": "world"}\r\nEND\r\n',
            ],
            serde=JsonSerde(),
        )

        result = client.set(b"key1", b"hello", noreply=False)
        result = client.get(b"key1")
        assert result == b"hello"

        result = client.set(b"key2", dict(hello="world"), noreply=False)
        result = client.get(b"key2")
        assert result == dict(hello="world")


class TestPrefixedClient(ClientTestMixin, unittest.TestCase):
    def make_client(self, mock_socket_values, **kwargs):
        client = Client("localhost", key_prefix=b"xyz:", **kwargs)
        client.sock = MockSocket(list(mock_socket_values))
        return client

    def test_get_found(self):
        client = self.make_client(
            [
                b"STORED\r\n",
                b"VALUE xyz:key 0 5\r\nvalue\r\nEND\r\n",
            ]
        )
        result = client.set(b"key", b"value", noreply=False)
        result = client.get(b"key")
        assert result == b"value"

    def test_get_many_some_found(self):
        client = self.make_client(
            [
                b"STORED\r\n",
                b"VALUE xyz:key1 0 6\r\nvalue1\r\nEND\r\n",
            ]
        )
        result = client.set(b"key1", b"value1", noreply=False)
        result = client.get_many([b"key1", b"key2"])
        assert result == {b"key1": b"value1"}

    def test_get_many_all_found(self):
        client = self.make_client(
            [
                b"STORED\r\n",
                b"STORED\r\n",
                b"VALUE xyz:key1 0 6\r\nvalue1\r\n",
                b"VALUE xyz:key2 0 6\r\nvalue2\r\nEND\r\n",
            ]
        )
        result = client.set(b"key1", b"value1", noreply=False)
        result = client.set(b"key2", b"value2", noreply=False)
        result = client.get_many([b"key1", b"key2"])
        assert result == {b"key1": b"value1", b"key2": b"value2"}

    def test_python_dict_get_is_supported(self):
        client = self.make_client([b"VALUE xyz:key 0 5\r\nvalue\r\nEND\r\n"])
        assert client[b"key"] == b"value"


class TestPrefixedPooledClient(TestPrefixedClient):
    def make_client(self, mock_socket_values, **kwargs):
        mock_client = Client("localhost", key_prefix=b"xyz:", **kwargs)
        mock_client.sock = MockSocket(list(mock_socket_values))
        client = PooledClient("localhost", key_prefix=b"xyz:", **kwargs)
        client.client_pool = pool.ObjectPool(lambda: mock_client)
        return client


@pytest.mark.unit()
class TestRetryOnEINTR(unittest.TestCase):
    def make_client(self, values):
        client = Client("localhost")
        client.sock = MockSocket(list(values))
        return client

    def test_recv(self):
        client = self.make_client(
            [
                b"VALUE ",
                socket.error(errno.EINTR, "Interrupted system call"),
                b"key1 0 6\r\nval",
                socket.error(errno.EINTR, "Interrupted system call"),
                b"ue1\r\nEND\r\n",
            ]
        )
        assert client[b"key1"] == b"value1"


@pytest.mark.unit()
class TestNormalizeServerSpec(unittest.TestCase):
    def test_normalize_server_spec(self):
        f = normalize_server_spec
        assert f(("127.0.0.1", 12345)) == ("127.0.0.1", 12345)
        assert f("unix:/run/memcached/socket") == "/run/memcached/socket"
        assert f("/run/memcached/socket") == "/run/memcached/socket"
        assert f("localhost") == ("localhost", 11211)
        assert f("localhost:12345") == ("localhost", 12345)
        assert f("[::1]") == ("::1", 11211)
        assert f("[::1]:12345") == ("::1", 12345)
        assert f("127.0.0.1") == ("127.0.0.1", 11211)
        assert f("127.0.0.1:12345") == ("127.0.0.1", 12345)

        with pytest.raises(ValueError, match="Unsupported server specification"):
            f(None)  # type: ignore

        with pytest.raises(ValueError, match="Unsupported server specification"):
            f({"host": 12345})  # type: ignore

        with pytest.raises(ValueError, match="Unsupported server specification"):
            f(12345)  # type: ignore


@pytest.mark.unit()
class TestKeepaliveopts(unittest.TestCase):
    def test_keepalive_opts(self):
        kao = KeepaliveOpts()
        assert kao.idle == 1 and kao.intvl == 1 and kao.cnt == 5
        kao = KeepaliveOpts(idle=1, intvl=4, cnt=2)
        assert kao.idle == 1 and kao.intvl == 4 and kao.cnt == 2
        kao = KeepaliveOpts(idle=8)
        assert kao.idle == 8 and kao.intvl == 1 and kao.cnt == 5
        kao = KeepaliveOpts(cnt=8)
        assert kao.idle == 1 and kao.intvl == 1 and kao.cnt == 8

        with self.assertRaises(ValueError):
            KeepaliveOpts(cnt=0)
        with self.assertRaises(ValueError):
            KeepaliveOpts(idle=-1)
