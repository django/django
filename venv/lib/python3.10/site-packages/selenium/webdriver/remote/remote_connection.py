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

import logging
import os
import platform
import socket
import string
from base64 import b64encode
from urllib import parse

import certifi
import urllib3

from selenium import __version__

from . import utils
from .command import Command
from .errorhandler import ErrorCode

LOGGER = logging.getLogger(__name__)

remote_commands = {
    Command.NEW_SESSION: ("POST", "/session"),
    Command.QUIT: ("DELETE", "/session/$sessionId"),
    Command.W3C_GET_CURRENT_WINDOW_HANDLE: ("GET", "/session/$sessionId/window"),
    Command.W3C_GET_WINDOW_HANDLES: ("GET", "/session/$sessionId/window/handles"),
    Command.GET: ("POST", "/session/$sessionId/url"),
    Command.GO_FORWARD: ("POST", "/session/$sessionId/forward"),
    Command.GO_BACK: ("POST", "/session/$sessionId/back"),
    Command.REFRESH: ("POST", "/session/$sessionId/refresh"),
    Command.W3C_EXECUTE_SCRIPT: ("POST", "/session/$sessionId/execute/sync"),
    Command.W3C_EXECUTE_SCRIPT_ASYNC: ("POST", "/session/$sessionId/execute/async"),
    Command.GET_CURRENT_URL: ("GET", "/session/$sessionId/url"),
    Command.GET_TITLE: ("GET", "/session/$sessionId/title"),
    Command.GET_PAGE_SOURCE: ("GET", "/session/$sessionId/source"),
    Command.SCREENSHOT: ("GET", "/session/$sessionId/screenshot"),
    Command.ELEMENT_SCREENSHOT: ("GET", "/session/$sessionId/element/$id/screenshot"),
    Command.FIND_ELEMENT: ("POST", "/session/$sessionId/element"),
    Command.FIND_ELEMENTS: ("POST", "/session/$sessionId/elements"),
    Command.W3C_GET_ACTIVE_ELEMENT: ("GET", "/session/$sessionId/element/active"),
    Command.FIND_CHILD_ELEMENT: ("POST", "/session/$sessionId/element/$id/element"),
    Command.FIND_CHILD_ELEMENTS: ("POST", "/session/$sessionId/element/$id/elements"),
    Command.CLICK_ELEMENT: ("POST", "/session/$sessionId/element/$id/click"),
    Command.CLEAR_ELEMENT: ("POST", "/session/$sessionId/element/$id/clear"),
    Command.GET_ELEMENT_TEXT: ("GET", "/session/$sessionId/element/$id/text"),
    Command.SEND_KEYS_TO_ELEMENT: ("POST", "/session/$sessionId/element/$id/value"),
    Command.UPLOAD_FILE: ("POST", "/session/$sessionId/se/file"),
    Command.GET_ELEMENT_TAG_NAME: ("GET", "/session/$sessionId/element/$id/name"),
    Command.IS_ELEMENT_SELECTED: ("GET", "/session/$sessionId/element/$id/selected"),
    Command.IS_ELEMENT_ENABLED: ("GET", "/session/$sessionId/element/$id/enabled"),
    Command.GET_ELEMENT_RECT: ("GET", "/session/$sessionId/element/$id/rect"),
    Command.GET_ELEMENT_ATTRIBUTE: ("GET", "/session/$sessionId/element/$id/attribute/$name"),
    Command.GET_ELEMENT_PROPERTY: ("GET", "/session/$sessionId/element/$id/property/$name"),
    Command.GET_ELEMENT_ARIA_ROLE: ("GET", "/session/$sessionId/element/$id/computedrole"),
    Command.GET_ELEMENT_ARIA_LABEL: ("GET", "/session/$sessionId/element/$id/computedlabel"),
    Command.GET_SHADOW_ROOT: ("GET", "/session/$sessionId/element/$id/shadow"),
    Command.FIND_ELEMENT_FROM_SHADOW_ROOT: ("POST", "/session/$sessionId/shadow/$shadowId/element"),
    Command.FIND_ELEMENTS_FROM_SHADOW_ROOT: ("POST", "/session/$sessionId/shadow/$shadowId/elements"),
    Command.GET_ALL_COOKIES: ("GET", "/session/$sessionId/cookie"),
    Command.ADD_COOKIE: ("POST", "/session/$sessionId/cookie"),
    Command.GET_COOKIE: ("GET", "/session/$sessionId/cookie/$name"),
    Command.DELETE_ALL_COOKIES: ("DELETE", "/session/$sessionId/cookie"),
    Command.DELETE_COOKIE: ("DELETE", "/session/$sessionId/cookie/$name"),
    Command.SWITCH_TO_FRAME: ("POST", "/session/$sessionId/frame"),
    Command.SWITCH_TO_PARENT_FRAME: ("POST", "/session/$sessionId/frame/parent"),
    Command.SWITCH_TO_WINDOW: ("POST", "/session/$sessionId/window"),
    Command.NEW_WINDOW: ("POST", "/session/$sessionId/window/new"),
    Command.CLOSE: ("DELETE", "/session/$sessionId/window"),
    Command.GET_ELEMENT_VALUE_OF_CSS_PROPERTY: ("GET", "/session/$sessionId/element/$id/css/$propertyName"),
    Command.EXECUTE_ASYNC_SCRIPT: ("POST", "/session/$sessionId/execute_async"),
    Command.SET_TIMEOUTS: ("POST", "/session/$sessionId/timeouts"),
    Command.GET_TIMEOUTS: ("GET", "/session/$sessionId/timeouts"),
    Command.W3C_DISMISS_ALERT: ("POST", "/session/$sessionId/alert/dismiss"),
    Command.W3C_ACCEPT_ALERT: ("POST", "/session/$sessionId/alert/accept"),
    Command.W3C_SET_ALERT_VALUE: ("POST", "/session/$sessionId/alert/text"),
    Command.W3C_GET_ALERT_TEXT: ("GET", "/session/$sessionId/alert/text"),
    Command.W3C_ACTIONS: ("POST", "/session/$sessionId/actions"),
    Command.W3C_CLEAR_ACTIONS: ("DELETE", "/session/$sessionId/actions"),
    Command.SET_WINDOW_RECT: ("POST", "/session/$sessionId/window/rect"),
    Command.GET_WINDOW_RECT: ("GET", "/session/$sessionId/window/rect"),
    Command.W3C_MAXIMIZE_WINDOW: ("POST", "/session/$sessionId/window/maximize"),
    Command.SET_SCREEN_ORIENTATION: ("POST", "/session/$sessionId/orientation"),
    Command.GET_SCREEN_ORIENTATION: ("GET", "/session/$sessionId/orientation"),
    Command.GET_NETWORK_CONNECTION: ("GET", "/session/$sessionId/network_connection"),
    Command.SET_NETWORK_CONNECTION: ("POST", "/session/$sessionId/network_connection"),
    Command.GET_LOG: ("POST", "/session/$sessionId/se/log"),
    Command.GET_AVAILABLE_LOG_TYPES: ("GET", "/session/$sessionId/se/log/types"),
    Command.CURRENT_CONTEXT_HANDLE: ("GET", "/session/$sessionId/context"),
    Command.CONTEXT_HANDLES: ("GET", "/session/$sessionId/contexts"),
    Command.SWITCH_TO_CONTEXT: ("POST", "/session/$sessionId/context"),
    Command.FULLSCREEN_WINDOW: ("POST", "/session/$sessionId/window/fullscreen"),
    Command.MINIMIZE_WINDOW: ("POST", "/session/$sessionId/window/minimize"),
    Command.PRINT_PAGE: ("POST", "/session/$sessionId/print"),
    Command.ADD_VIRTUAL_AUTHENTICATOR: ("POST", "/session/$sessionId/webauthn/authenticator"),
    Command.REMOVE_VIRTUAL_AUTHENTICATOR: (
        "DELETE",
        "/session/$sessionId/webauthn/authenticator/$authenticatorId",
    ),
    Command.ADD_CREDENTIAL: ("POST", "/session/$sessionId/webauthn/authenticator/$authenticatorId/credential"),
    Command.GET_CREDENTIALS: ("GET", "/session/$sessionId/webauthn/authenticator/$authenticatorId/credentials"),
    Command.REMOVE_CREDENTIAL: (
        "DELETE",
        "/session/$sessionId/webauthn/authenticator/$authenticatorId/credentials/$credentialId",
    ),
    Command.REMOVE_ALL_CREDENTIALS: (
        "DELETE",
        "/session/$sessionId/webauthn/authenticator/$authenticatorId/credentials",
    ),
    Command.SET_USER_VERIFIED: ("POST", "/session/$sessionId/webauthn/authenticator/$authenticatorId/uv"),
}


class RemoteConnection:
    """A connection with the Remote WebDriver server.

    Communicates with the server using the WebDriver wire protocol:
    https://github.com/SeleniumHQ/selenium/wiki/JsonWireProtocol
    """

    browser_name = None
    _timeout = socket._GLOBAL_DEFAULT_TIMEOUT
    _ca_certs = os.getenv("REQUESTS_CA_BUNDLE") if "REQUESTS_CA_BUNDLE" in os.environ else certifi.where()

    @classmethod
    def get_timeout(cls):
        """:Returns:

        Timeout value in seconds for all http requests made to the
        Remote Connection
        """
        return None if cls._timeout == socket._GLOBAL_DEFAULT_TIMEOUT else cls._timeout

    @classmethod
    def set_timeout(cls, timeout):
        """Override the default timeout.

        :Args:
            - timeout - timeout value for http requests in seconds
        """
        cls._timeout = timeout

    @classmethod
    def reset_timeout(cls):
        """Reset the http request timeout to socket._GLOBAL_DEFAULT_TIMEOUT."""
        cls._timeout = socket._GLOBAL_DEFAULT_TIMEOUT

    @classmethod
    def get_certificate_bundle_path(cls):
        """:Returns:

        Paths of the .pem encoded certificate to verify connection to
        command executor. Defaults to certifi.where() or
        REQUESTS_CA_BUNDLE env variable if set.
        """
        return cls._ca_certs

    @classmethod
    def set_certificate_bundle_path(cls, path):
        """Set the path to the certificate bundle to verify connection to
        command executor. Can also be set to None to disable certificate
        validation.

        :Args:
            - path - path of a .pem encoded certificate chain.
        """
        cls._ca_certs = path

    @classmethod
    def get_remote_connection_headers(cls, parsed_url, keep_alive=False):
        """Get headers for remote request.

        :Args:
         - parsed_url - The parsed url
         - keep_alive (Boolean) - Is this a keep-alive connection (default: False)
        """

        system = platform.system().lower()
        if system == "darwin":
            system = "mac"

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json;charset=UTF-8",
            "User-Agent": f"selenium/{__version__} (python {system})",
        }

        if parsed_url.username:
            base64string = b64encode(f"{parsed_url.username}:{parsed_url.password}".encode())
            headers.update({"Authorization": f"Basic {base64string.decode()}"})

        if keep_alive:
            headers.update({"Connection": "keep-alive"})

        return headers

    def _get_proxy_url(self):
        if self._url.startswith("https://"):
            return os.environ.get("https_proxy", os.environ.get("HTTPS_PROXY"))
        if self._url.startswith("http://"):
            return os.environ.get("http_proxy", os.environ.get("HTTP_PROXY"))

    def _identify_http_proxy_auth(self):
        url = self._proxy_url
        url = url[url.find(":") + 3 :]
        return "@" in url and len(url[: url.find("@")]) > 0

    def _separate_http_proxy_auth(self):
        url = self._proxy_url
        protocol = url[: url.find(":") + 3]
        no_protocol = url[len(protocol) :]
        auth = no_protocol[: no_protocol.find("@")]
        proxy_without_auth = protocol + no_protocol[len(auth) + 1 :]
        return proxy_without_auth, auth

    def _get_connection_manager(self):
        pool_manager_init_args = {"timeout": self.get_timeout()}
        if self._ca_certs:
            pool_manager_init_args["cert_reqs"] = "CERT_REQUIRED"
            pool_manager_init_args["ca_certs"] = self._ca_certs

        if self._proxy_url:
            if self._proxy_url.lower().startswith("sock"):
                from urllib3.contrib.socks import SOCKSProxyManager

                return SOCKSProxyManager(self._proxy_url, **pool_manager_init_args)
            if self._identify_http_proxy_auth():
                self._proxy_url, self._basic_proxy_auth = self._separate_http_proxy_auth()
                pool_manager_init_args["proxy_headers"] = urllib3.make_headers(proxy_basic_auth=self._basic_proxy_auth)
            return urllib3.ProxyManager(self._proxy_url, **pool_manager_init_args)

        return urllib3.PoolManager(**pool_manager_init_args)

    def __init__(self, remote_server_addr: str, keep_alive: bool = False, ignore_proxy: bool = False):
        self.keep_alive = keep_alive
        self._url = remote_server_addr

        # Env var NO_PROXY will override this part of the code
        _no_proxy = os.environ.get("no_proxy", os.environ.get("NO_PROXY"))
        if _no_proxy:
            for npu in _no_proxy.split(","):
                npu = npu.strip()
                if npu == "*":
                    ignore_proxy = True
                    break
                n_url = parse.urlparse(npu)
                remote_add = parse.urlparse(self._url)
                if n_url.netloc:
                    if remote_add.netloc == n_url.netloc:
                        ignore_proxy = True
                        break
                else:
                    if n_url.path in remote_add.netloc:
                        ignore_proxy = True
                        break

        self._proxy_url = self._get_proxy_url() if not ignore_proxy else None
        if keep_alive:
            self._conn = self._get_connection_manager()
        self._commands = remote_commands

    def execute(self, command, params):
        """Send a command to the remote server.

        Any path substitutions required for the URL mapped to the command should be
        included in the command parameters.

        :Args:
         - command - A string specifying the command to execute.
         - params - A dictionary of named parameters to send with the command as
           its JSON payload.
        """
        command_info = self._commands[command]
        assert command_info is not None, f"Unrecognised command {command}"
        path = string.Template(command_info[1]).substitute(params)
        if isinstance(params, dict) and "sessionId" in params:
            del params["sessionId"]
        data = utils.dump_json(params)
        url = f"{self._url}{path}"
        return self._request(command_info[0], url, body=data)

    def _request(self, method, url, body=None):
        """Send an HTTP request to the remote server.

        :Args:
         - method - A string for the HTTP method to send the request with.
         - url - A string for the URL to send the request to.
         - body - A string for request body. Ignored unless method is POST or PUT.

        :Returns:
          A dictionary with the server's parsed JSON response.
        """
        LOGGER.debug(f"{method} {url} {body}")
        parsed_url = parse.urlparse(url)
        headers = self.get_remote_connection_headers(parsed_url, self.keep_alive)
        response = None
        if body and method not in ("POST", "PUT"):
            body = None

        if self.keep_alive:
            response = self._conn.request(method, url, body=body, headers=headers)
            statuscode = response.status
        else:
            conn = self._get_connection_manager()
            with conn as http:
                response = http.request(method, url, body=body, headers=headers)
            statuscode = response.status
        data = response.data.decode("UTF-8")
        LOGGER.debug(f"Remote response: status={response.status} | data={data} | headers={response.headers}")
        try:
            if 300 <= statuscode < 304:
                return self._request("GET", response.headers.get("location", None))
            if 399 < statuscode <= 500:
                return {"status": statuscode, "value": data}
            content_type = []
            if response.headers.get("Content-Type", None):
                content_type = response.headers.get("Content-Type", None).split(";")
            if not any([x.startswith("image/png") for x in content_type]):
                try:
                    data = utils.load_json(data.strip())
                except ValueError:
                    if 199 < statuscode < 300:
                        status = ErrorCode.SUCCESS
                    else:
                        status = ErrorCode.UNKNOWN_ERROR
                    return {"status": status, "value": data.strip()}

                # Some drivers incorrectly return a response
                # with no 'value' field when they should return null.
                if "value" not in data:
                    data["value"] = None
                return data
            data = {"status": 0, "value": data}
            return data
        finally:
            LOGGER.debug("Finished Request")
            response.close()

    def close(self):
        """Clean up resources when finished with the remote_connection."""
        if hasattr(self, "_conn"):
            self._conn.clear()
