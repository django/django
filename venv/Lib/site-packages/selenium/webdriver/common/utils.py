# Licensed to the Software Freedom Conservancy (SFC) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The SFC licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

"""Utility functions."""

import json
import socket
import urllib.request
from collections.abc import Iterable

from selenium.webdriver.common.keys import Keys

_is_connectable_exceptions = (socket.error, ConnectionResetError)


def free_port() -> int:
    """Determines a free port using sockets.

    First try IPv4, but use IPv6 if it can't bind (IPv6-only system).
    """
    free_socket = None
    try:
        # IPv4
        free_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        free_socket.bind(("127.0.0.1", 0))
    except OSError:
        if free_socket:
            free_socket.close()
        # IPv6
        try:
            free_socket = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
            free_socket.bind(("::1", 0))
        except OSError:
            if free_socket:
                free_socket.close()
            raise RuntimeError("Can't find free port (Unable to bind to IPv4 or IPv6)")
    try:
        port: int = free_socket.getsockname()[1]
    except Exception as e:
        raise RuntimeError(f"Can't find free port: ({e})")
    finally:
        free_socket.close()
    return port


def find_connectable_ip(host: str | bytes | bytearray | None, port: int | None = None) -> str | None:
    """Resolve a hostname to an IP, preferring IPv4 addresses.

    We prefer IPv4 so that we don't change behavior from previous IPv4-only
    implementations, and because some drivers (e.g., FirefoxDriver) do not
    support IPv6 connections.

    If the optional port number is provided, only IPs that listen on the given
    port are considered.

    Args:
        host: hostname
        port: port number

    Returns:
        A single IP address, as a string. If any IPv4 address is found, one is
        returned. Otherwise, if any IPv6 address is found, one is returned. If
        neither, then None is returned.
    """
    try:
        addrinfos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return None

    ip = None
    for family, _, _, _, sockaddr in addrinfos:
        connectable = True
        if port:
            connectable = is_connectable(port, str(sockaddr[0]))

        if connectable and family == socket.AF_INET:
            return str(sockaddr[0])
        if connectable and not ip and family == socket.AF_INET6:
            ip = str(sockaddr[0])
    return ip


def join_host_port(host: str, port: int) -> str:
    """Joins a hostname and port together.

    This is a minimal implementation intended to cope with IPv6 literals. For
    example, _join_host_port('::1', 80) == '[::1]:80'.

    Args:
        host: hostname or IP
        port: port number
    """
    if ":" in host and not host.startswith("["):
        return f"[{host}]:{port}"
    return f"{host}:{port}"


def is_connectable(port: int, host: str | None = "localhost") -> bool:
    """Tries to connect to the server at port to see if it is running.

    Args:
        port: port number
        host: hostname or IP
    """
    socket_ = None
    try:
        socket_ = socket.create_connection((host, port), 1)
        result = True
    except _is_connectable_exceptions:
        result = False
    finally:
        if socket_:
            try:
                socket_.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
            socket_.close()
    return result


def is_url_connectable(
    port: int | str,
    host: str = "localhost",
    scheme: str = "http",
) -> bool:
    """Send a request to the HTTP server at the /status endpoint to verify connectivity.

    Args:
        port: port number
        host: hostname or IP
        scheme: URL scheme

    Returns:
        True if the service is ready to accept new sessions, False otherwise.
    """
    try:
        # Disable proxy for localhost connections
        proxy_handler = urllib.request.ProxyHandler({})
        opener = urllib.request.build_opener(proxy_handler)

        request = urllib.request.Request(f"{scheme}://{host}:{port}/status")
        with opener.open(request, timeout=1) as res:
            if res.getcode() != 200:
                return False

            body = res.read().decode("utf-8")
            data = json.loads(body)

            # Check top-level and value.ready, some browsers wrap it under 'value', e.g., ChromeDriver
            ready = data.get("ready")
            if ready is None:
                ready = data.get("value", {}).get("ready")
            return ready is True
    except Exception:
        return False


def keys_to_typing(value: Iterable[str | int | float]) -> list[str]:
    """Processes the values that will be typed in the element."""
    characters: list[str] = []
    for val in value:
        if isinstance(val, Keys):
            # Todo: Does this even work?
            characters.append(str(val))
        elif isinstance(val, (int, float)):
            characters.extend(str(val))
        else:
            characters.extend(val)
    return characters
