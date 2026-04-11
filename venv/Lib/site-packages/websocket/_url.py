import ipaddress
import os
from typing import Optional
from urllib.parse import unquote, urlparse
from ._exceptions import WebSocketProxyException

"""
_url.py
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

__all__ = ["parse_url", "get_proxy_info"]


def parse_url(url: str) -> tuple:
    """
    parse url and the result is tuple of
    (hostname, port, resource path and the flag of secure mode)

    Parameters
    ----------
    url: str
        url string.
    """
    if ":" not in url:
        raise ValueError("url is invalid")

    scheme, url = url.split(":", 1)

    parsed = urlparse(url, scheme="http")
    if parsed.hostname:
        hostname = parsed.hostname
    else:
        raise ValueError("hostname is invalid")
    port = 0
    if parsed.port:
        port = parsed.port

    is_secure = False
    if scheme == "ws":
        if not port:
            port = 80
    elif scheme == "wss":
        is_secure = True
        if not port:
            port = 443
    else:
        raise ValueError("scheme %s is invalid" % scheme)

    if parsed.path:
        resource = parsed.path
    else:
        resource = "/"

    if parsed.query:
        resource += f"?{parsed.query}"

    return hostname, port, resource, is_secure


def _is_ip_address(addr: str) -> bool:
    if not isinstance(addr, str):
        raise TypeError("_is_ip_address() argument 1 must be str")
    try:
        ipaddress.ip_address(addr)
    except ValueError:
        return False
    else:
        return True


def _is_subnet_address(hostname: str) -> bool:
    try:
        ipaddress.ip_network(hostname)
    except ValueError:
        return False
    else:
        return True


def _is_address_in_network(ip: str, net: str) -> bool:
    try:
        return ipaddress.ip_network(ip).subnet_of(ipaddress.ip_network(net))
    except TypeError:
        return False


def _is_no_proxy_host(hostname: str, no_proxy: Optional[list[str]]) -> bool:
    if not no_proxy:
        if v := os.environ.get("no_proxy", os.environ.get("NO_PROXY", "")).replace(
            " ", ""
        ):
            no_proxy = v.split(",")

    if not no_proxy:
        no_proxy = []

    if "*" in no_proxy:
        return True
    if hostname in no_proxy:
        return True
    if _is_ip_address(hostname):
        return any(
            [
                _is_address_in_network(hostname, subnet)
                for subnet in no_proxy
                if _is_subnet_address(subnet)
            ]
        )
    for domain in [domain for domain in no_proxy if domain.startswith(".")]:
        endDomain = domain.lstrip(".")
        if hostname.endswith(endDomain):
            return True
    return False


def get_proxy_info(
    hostname: str,
    is_secure: bool,
    proxy_host: Optional[str] = None,
    proxy_port: int = 0,
    proxy_auth: Optional[tuple] = None,
    no_proxy: Optional[list[str]] = None,
    proxy_type: str = "http",
) -> tuple:
    """
    Try to retrieve proxy host and port from environment
    if not provided in options.
    Result is (proxy_host, proxy_port, proxy_auth).
    proxy_auth is tuple of username and password
    of proxy authentication information.

    Parameters
    ----------
    hostname: str
        Websocket server name.
    is_secure: bool
        Is the connection secure? (wss) looks for "https_proxy" in env
        instead of "http_proxy"
    proxy_host: str
        http proxy host name.
    proxy_port: str or int
        http proxy port.
    no_proxy: list
        Whitelisted host names that don't use the proxy.
    proxy_auth: tuple
        HTTP proxy auth information. Tuple of username and password. Default is None.
    proxy_type: str
        Specify the proxy protocol (http, socks4, socks4a, socks5, socks5h). Default is "http".
        Use socks4a or socks5h if you want to send DNS requests through the proxy.
    """
    if _is_no_proxy_host(hostname, no_proxy):
        return None, 0, None

    if proxy_host:
        if not proxy_port:
            raise WebSocketProxyException("Cannot use port 0 when proxy_host specified")
        port = proxy_port
        auth = proxy_auth
        return proxy_host, port, auth

    env_key = "https_proxy" if is_secure else "http_proxy"
    value = os.environ.get(env_key, os.environ.get(env_key.upper(), "")).replace(
        " ", ""
    )
    if value:
        proxy = urlparse(value)
        auth = (
            (unquote(proxy.username or ""), unquote(proxy.password or ""))
            if proxy.username
            else None
        )
        return proxy.hostname, proxy.port, auth

    return None, 0, None
