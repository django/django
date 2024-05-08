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
"""The Utils methods."""

import socket
from typing import Iterable
from typing import List
from typing import Optional
from typing import Union

from selenium.types import AnyKey
from selenium.webdriver.common.keys import Keys

_is_connectable_exceptions = (socket.error, ConnectionResetError)


def free_port() -> int:
    """Determines a free port using sockets."""
    free_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    free_socket.bind(("127.0.0.1", 0))
    free_socket.listen(5)
    port: int = free_socket.getsockname()[1]
    free_socket.close()
    return port


def find_connectable_ip(host: Union[str, bytes, bytearray, None], port: Optional[int] = None) -> Optional[str]:
    """Resolve a hostname to an IP, preferring IPv4 addresses.

    We prefer IPv4 so that we don't change behavior from previous IPv4-only
    implementations, and because some drivers (e.g., FirefoxDriver) do not
    support IPv6 connections.

    If the optional port number is provided, only IPs that listen on the given
    port are considered.

    :Args:
        - host - A hostname.
        - port - Optional port number.

    :Returns:
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
            connectable = is_connectable(port, sockaddr[0])

        if connectable and family == socket.AF_INET:
            return sockaddr[0]
        if connectable and not ip and family == socket.AF_INET6:
            ip = sockaddr[0]
    return ip


def join_host_port(host: str, port: int) -> str:
    """Joins a hostname and port together.

    This is a minimal implementation intended to cope with IPv6 literals. For
    example, _join_host_port('::1', 80) == '[::1]:80'.

    :Args:
        - host - A hostname.
        - port - An integer port.
    """
    if ":" in host and not host.startswith("["):
        return f"[{host}]:{port}"
    return f"{host}:{port}"


def is_connectable(port: int, host: Optional[str] = "localhost") -> bool:
    """Tries to connect to the server at port to see if it is running.

    :Args:
     - port - The port to connect.
    """
    socket_ = None
    try:
        socket_ = socket.create_connection((host, port), 1)
        result = True
    except _is_connectable_exceptions:
        result = False
    finally:
        if socket_:
            socket_.close()
    return result


def is_url_connectable(port: Union[int, str]) -> bool:
    """Tries to connect to the HTTP server at /status path and specified port
    to see if it responds successfully.

    :Args:
     - port - The port to connect.
    """
    from urllib import request as url_request

    try:
        res = url_request.urlopen(f"http://127.0.0.1:{port}/status")
        return res.getcode() == 200
    except Exception:
        return False


def keys_to_typing(value: Iterable[AnyKey]) -> List[str]:
    """Processes the values that will be typed in the element."""
    characters: List[str] = []
    for val in value:
        if isinstance(val, Keys):
            # Todo: Does this even work?
            characters.append(val)
        elif isinstance(val, (int, float)):
            characters.extend(str(val))
        else:
            characters.extend(val)
    return characters
