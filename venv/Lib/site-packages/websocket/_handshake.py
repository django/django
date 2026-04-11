"""
_handshake.py
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

import hashlib
import hmac
import os
from base64 import encodebytes as base64encode
from http import HTTPStatus

from ._cookiejar import SimpleCookieJar
from ._exceptions import WebSocketException, WebSocketBadStatusException
from ._http import read_headers
from ._logging import dump, error
from ._socket import send

__all__ = ["handshake_response", "handshake", "SUPPORTED_REDIRECT_STATUSES"]

# websocket supported version.
VERSION = 13

SUPPORTED_REDIRECT_STATUSES = (
    HTTPStatus.MOVED_PERMANENTLY,
    HTTPStatus.FOUND,
    HTTPStatus.SEE_OTHER,
    HTTPStatus.TEMPORARY_REDIRECT,
    HTTPStatus.PERMANENT_REDIRECT,
)
SUCCESS_STATUSES = SUPPORTED_REDIRECT_STATUSES + (HTTPStatus.SWITCHING_PROTOCOLS,)

CookieJar = SimpleCookieJar()


class handshake_response:
    def __init__(self, status: int, headers: dict, subprotocol):
        self.status = status
        self.headers = headers
        self.subprotocol = subprotocol
        CookieJar.add(headers.get("set-cookie"))


def handshake(
    sock, url: str, hostname: str, port: int, resource: str, **options
) -> handshake_response:
    headers, key = _get_handshake_headers(resource, url, hostname, port, options)

    header_str = "\r\n".join(headers)
    send(sock, header_str)
    dump("request header", header_str)

    status, resp = _get_resp_headers(sock)
    if status in SUPPORTED_REDIRECT_STATUSES:
        return handshake_response(status, resp, None)
    success, subproto = _validate(resp, key, options.get("subprotocols"))
    if not success:
        raise WebSocketException("Invalid WebSocket Header")

    return handshake_response(status, resp, subproto)


def _pack_hostname(hostname: str) -> str:
    # IPv6 address
    if ":" in hostname:
        return f"[{hostname}]"
    return hostname


def _get_handshake_headers(
    resource: str, url: str, host: str, port: int, options: dict
) -> tuple:
    headers = [f"GET {resource} HTTP/1.1", "Upgrade: websocket"]
    if port in [80, 443]:
        hostport = _pack_hostname(host)
    else:
        hostport = f"{_pack_hostname(host)}:{port}"
    if options.get("host"):
        headers.append(f'Host: {options["host"]}')
    else:
        headers.append(f"Host: {hostport}")

    # scheme indicates whether http or https is used in Origin
    # The same approach is used in parse_url of _url.py to set default port
    scheme, url = url.split(":", 1)
    if not options.get("suppress_origin"):
        if "origin" in options and options["origin"] is not None:
            headers.append(f'Origin: {options["origin"]}')
        elif scheme == "wss":
            headers.append(f"Origin: https://{hostport}")
        else:
            headers.append(f"Origin: http://{hostport}")

    key = _create_sec_websocket_key()

    # Append Sec-WebSocket-Key & Sec-WebSocket-Version if not manually specified
    if not options.get("header") or "Sec-WebSocket-Key" not in options["header"]:
        headers.append(f"Sec-WebSocket-Key: {key}")
    else:
        key = options["header"]["Sec-WebSocket-Key"]

    if not options.get("header") or "Sec-WebSocket-Version" not in options["header"]:
        headers.append(f"Sec-WebSocket-Version: {VERSION}")

    if not options.get("connection"):
        headers.append("Connection: Upgrade")
    else:
        headers.append(options["connection"])

    if subprotocols := options.get("subprotocols"):
        headers.append(f'Sec-WebSocket-Protocol: {",".join(subprotocols)}')

    if header := options.get("header"):
        if isinstance(header, dict):
            header = [": ".join([k, v]) for k, v in header.items() if v is not None]
        headers.extend(header)

    server_cookie = CookieJar.get(host)
    client_cookie = options.get("cookie", None)

    if cookie := "; ".join(filter(None, [server_cookie, client_cookie])):
        headers.append(f"Cookie: {cookie}")

    headers.extend(("", ""))
    return headers, key


def _get_resp_headers(sock, success_statuses: tuple = SUCCESS_STATUSES) -> tuple:
    status, resp_headers, status_message = read_headers(sock)
    if status not in success_statuses:
        content_len = resp_headers.get("content-length")
        if content_len:
            # Use chunked reading to avoid SSL BAD_LENGTH error on large responses
            from ._socket import recv

            response_body = b""
            remaining = int(content_len)
            while remaining > 0:
                chunk_size = min(remaining, 16384)  # Read in 16KB chunks
                chunk = recv(sock, chunk_size)
                response_body += chunk
                remaining -= len(chunk)
        else:
            response_body = None
        raise WebSocketBadStatusException(
            f"Handshake status {status} {status_message} -+-+- {resp_headers} -+-+- {response_body}",
            status,
            status_message,
            resp_headers,
            response_body,
        )
    return status, resp_headers


_HEADERS_TO_CHECK = {
    "upgrade": "websocket",
    "connection": "upgrade",
}


def _validate(headers, key: str, subprotocols) -> tuple:
    subproto = None
    for k, v in _HEADERS_TO_CHECK.items():
        r = headers.get(k, None)
        if not r:
            return False, None
        r = [x.strip().lower() for x in r.split(",")]
        if v not in r:
            return False, None

    if subprotocols:
        subproto = headers.get("sec-websocket-protocol", None)
        if not subproto or subproto.lower() not in [s.lower() for s in subprotocols]:
            error(f"Invalid subprotocol: {subprotocols}")
            return False, None
        subproto = subproto.lower()

    result = headers.get("sec-websocket-accept", None)
    if not result:
        return False, None
    result = result.lower()

    if isinstance(result, str):
        result = result.encode("utf-8")

    value = f"{key}258EAFA5-E914-47DA-95CA-C5AB0DC85B11".encode("utf-8")
    hashed = base64encode(hashlib.sha1(value).digest()).strip().lower()

    if hmac.compare_digest(hashed, result):
        return True, subproto
    else:
        return False, None


def _create_sec_websocket_key() -> str:
    randomness = os.urandom(16)
    return base64encode(randomness).decode("utf-8").strip()
