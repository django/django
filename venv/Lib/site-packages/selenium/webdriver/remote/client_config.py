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

import base64
import os
import socket
from enum import Enum
from urllib import parse

import certifi

from selenium.webdriver.common.proxy import Proxy, ProxyType


class AuthType(Enum):
    BASIC = "Basic"
    BEARER = "Bearer"
    X_API_KEY = "X-API-Key"


class _ClientConfigDescriptor:
    def __init__(self, name):
        self.name = name

    def __get__(self, obj, cls):
        return obj.__dict__[self.name]

    def __set__(self, obj, value) -> None:
        obj.__dict__[self.name] = value


class ClientConfig:
    remote_server_addr = _ClientConfigDescriptor("_remote_server_addr")
    """Gets and Sets Remote Server."""
    keep_alive = _ClientConfigDescriptor("_keep_alive")
    """Gets and Sets Keep Alive value."""
    proxy = _ClientConfigDescriptor("_proxy")
    """Gets and Sets the proxy used for communicating with the driver/server."""
    ignore_certificates = _ClientConfigDescriptor("_ignore_certificates")
    """Gets and Sets the ignore certificate check value."""
    init_args_for_pool_manager = _ClientConfigDescriptor("_init_args_for_pool_manager")
    """Gets and Sets the ignore certificate check."""
    timeout = _ClientConfigDescriptor("_timeout")
    """Gets and Sets the timeout (in seconds) used for communicating with the driver/server."""
    ca_certs = _ClientConfigDescriptor("_ca_certs")
    """Gets and Sets the path to bundle of CA certificates."""
    username = _ClientConfigDescriptor("_username")
    """Gets and Sets the username used for basic authentication to the remote."""
    password = _ClientConfigDescriptor("_password")
    """Gets and Sets the password used for basic authentication to the remote."""
    auth_type = _ClientConfigDescriptor("_auth_type")
    """Gets and Sets the type of authentication to the remote server."""
    token = _ClientConfigDescriptor("_token")
    """Gets and Sets the token used for authentication to the remote server."""
    user_agent = _ClientConfigDescriptor("_user_agent")
    """Gets and Sets user agent to be added to the request headers."""
    extra_headers = _ClientConfigDescriptor("_extra_headers")
    """Gets and Sets extra headers to be added to the request."""
    websocket_timeout = _ClientConfigDescriptor("_websocket_timeout")
    """Gets and Sets the WebSocket response wait timeout (in seconds) used for communicating with the browser."""
    websocket_interval = _ClientConfigDescriptor("_websocket_interval")
    """Gets and Sets the WebSocket response wait interval (in seconds) used for communicating with the browser."""

    def __init__(
        self,
        remote_server_addr: str,
        keep_alive: bool | None = True,
        proxy: Proxy | None = Proxy(raw={"proxyType": ProxyType.SYSTEM}),
        ignore_certificates: bool | None = False,
        init_args_for_pool_manager: dict | None = None,
        timeout: int | None = None,
        ca_certs: str | None = None,
        username: str | None = None,
        password: str | None = None,
        auth_type: AuthType | None = AuthType.BASIC,
        token: str | None = None,
        user_agent: str | None = None,
        extra_headers: dict | None = None,
        websocket_timeout: float | None = 30.0,
        websocket_interval: float | None = 0.1,
    ) -> None:
        self.remote_server_addr = remote_server_addr
        self.keep_alive = keep_alive
        self.proxy = proxy
        self.ignore_certificates = ignore_certificates
        self.init_args_for_pool_manager = init_args_for_pool_manager or {}
        self.timeout = socket.getdefaulttimeout() if timeout is None else timeout
        self.username = username
        self.password = password
        self.auth_type = auth_type
        self.token = token
        self.user_agent = user_agent
        self.extra_headers = extra_headers
        self.websocket_timeout = websocket_timeout
        self.websocket_interval = websocket_interval

        self.ca_certs = (
            (os.getenv("REQUESTS_CA_BUNDLE") if "REQUESTS_CA_BUNDLE" in os.environ else certifi.where())
            if ca_certs is None
            else ca_certs
        )

    def reset_timeout(self) -> None:
        """Resets the timeout to the default value of socket."""
        self._timeout = socket.getdefaulttimeout()

    def get_proxy_url(self) -> str | None:
        """Returns the proxy URL to use for the connection."""
        proxy_type = self.proxy.proxy_type
        remote_add = parse.urlparse(self.remote_server_addr)
        if proxy_type is ProxyType.DIRECT:
            return None
        if proxy_type is ProxyType.SYSTEM:
            _no_proxy = os.environ.get("no_proxy", os.environ.get("NO_PROXY"))
            if _no_proxy:
                for entry in map(str.strip, _no_proxy.split(",")):
                    if entry == "*":
                        return None
                    n_url = parse.urlparse(entry)
                    if n_url.netloc and remote_add.netloc == n_url.netloc:
                        return None
                    if n_url.path in remote_add.netloc:
                        return None
            return os.environ.get(
                "https_proxy" if self.remote_server_addr.startswith("https://") else "http_proxy",
                os.environ.get("HTTPS_PROXY" if self.remote_server_addr.startswith("https://") else "HTTP_PROXY"),
            )
        if proxy_type is ProxyType.MANUAL:
            return self.proxy.sslProxy if self.remote_server_addr.startswith("https://") else self.proxy.http_proxy
        return None

    def get_auth_header(self) -> dict | None:
        """Returns the authorization to add to the request headers."""
        if self.auth_type is AuthType.BASIC and self.username and self.password:
            credentials = f"{self.username}:{self.password}"
            encoded_credentials = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")
            return {"Authorization": f"{AuthType.BASIC.value} {encoded_credentials}"}
        if self.auth_type is AuthType.BEARER and self.token:
            return {"Authorization": f"{AuthType.BEARER.value} {self.token}"}
        if self.auth_type is AuthType.X_API_KEY and self.token:
            return {f"{AuthType.X_API_KEY.value}": f"{self.token}"}
        return None
