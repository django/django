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

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from selenium.webdriver.common.bidi.common import command_builder
from selenium.webdriver.remote.websocket_connection import WebSocketConnection


class NetworkEvent:
    """Represents a network event."""

    def __init__(self, event_class: str, **kwargs: Any) -> None:
        self.event_class = event_class
        self.params = kwargs

    @classmethod
    def from_json(cls, json: dict[str, Any]) -> NetworkEvent:
        return cls(event_class=json.get("event_class", ""), **json)


class Network:
    EVENTS = {
        "before_request": "network.beforeRequestSent",
        "response_started": "network.responseStarted",
        "response_completed": "network.responseCompleted",
        "auth_required": "network.authRequired",
        "fetch_error": "network.fetchError",
        "continue_request": "network.continueRequest",
        "continue_auth": "network.continueWithAuth",
    }

    PHASES = {
        "before_request": "beforeRequestSent",
        "response_started": "responseStarted",
        "auth_required": "authRequired",
    }

    def __init__(self, conn: WebSocketConnection) -> None:
        self.conn = conn
        self.intercepts: list[str] = []
        self.callbacks: dict[str | int, Any] = {}
        self.subscriptions: dict[str, list[int]] = {}

    def _add_intercept(
        self,
        phases: list[str] | None = None,
        contexts: list[str] | None = None,
        url_patterns: list[Any] | None = None,
    ) -> dict[str, Any]:
        """Add an intercept to the network.

        Args:
            phases: A list of phases to intercept. Default is None (empty list).
            contexts: A list of contexts to intercept. Default is None.
            url_patterns: A list of URL patterns to intercept. Default is None.

        Returns:
            str: intercept id
        """
        if phases is None:
            phases = []
        params = {}
        if contexts is not None:
            params["contexts"] = contexts
        if url_patterns is not None:
            params["urlPatterns"] = url_patterns
        if len(phases) > 0:
            params["phases"] = phases
        else:
            params["phases"] = ["beforeRequestSent"]
        cmd = command_builder("network.addIntercept", params)

        result: dict[str, Any] = self.conn.execute(cmd)
        self.intercepts.append(result["intercept"])
        return result

    def _remove_intercept(self, intercept: str | None = None) -> None:
        """Remove a specific intercept, or all intercepts.

        Args:
            intercept: The intercept to remove. Default is None.

        Raises:
            ValueError: If intercept is not found.

        Note:
            If intercept is None, all intercepts will be removed.
        """
        if intercept is None:
            intercepts_to_remove = self.intercepts.copy()  # create a copy before iterating
            for intercept_id in intercepts_to_remove:  # remove all intercepts
                self.conn.execute(command_builder("network.removeIntercept", {"intercept": intercept_id}))
                self.intercepts.remove(intercept_id)
        else:
            try:
                self.conn.execute(command_builder("network.removeIntercept", {"intercept": intercept}))
                self.intercepts.remove(intercept)
            except Exception as e:
                raise Exception(f"Exception: {e}")

    def _on_request(self, event_name: str, callback: Callable[[Request], Any]) -> int:
        """Set a callback function to subscribe to a network event.

        Args:
            event_name: The event to subscribe to.
            callback: The callback function to execute on event.
                Takes Request object as argument.

        Returns:
            int: callback id
        """
        event = NetworkEvent(event_name)

        def _callback(event_data: NetworkEvent) -> None:
            request = Request(
                network=self,
                request_id=event_data.params["request"].get("request", None),
                body_size=event_data.params["request"].get("bodySize", None),
                cookies=event_data.params["request"].get("cookies", None),
                resource_type=event_data.params["request"].get("goog:resourceType", None),
                headers=event_data.params["request"].get("headers", None),
                headers_size=event_data.params["request"].get("headersSize", None),
                timings=event_data.params["request"].get("timings", None),
                url=event_data.params["request"].get("url", None),
            )
            callback(request)

        callback_id: int = self.conn.add_callback(event, _callback)

        if event_name in self.callbacks:
            self.callbacks[event_name].append(callback_id)
        else:
            self.callbacks[event_name] = [callback_id]

        return callback_id

    def add_request_handler(
        self,
        event: str,
        callback: Callable[[Request], Any],
        url_patterns: list[Any] | None = None,
        contexts: list[str] | None = None,
    ) -> int:
        """Add a request handler to the network.

        Args:
            event: The event to subscribe to.
            callback: The callback function to execute on request interception.
                Takes Request object as argument.
            url_patterns: A list of URL patterns to intercept. Default is None.
            contexts: A list of contexts to intercept. Default is None.

        Returns:
            int: callback id
        """
        try:
            event_name = self.EVENTS[event]
            phase_name = self.PHASES[event]
        except KeyError:
            raise Exception(f"Event {event} not found")

        result = self._add_intercept(phases=[phase_name], url_patterns=url_patterns, contexts=contexts)
        callback_id = self._on_request(event_name, callback)

        if event_name in self.subscriptions:
            self.subscriptions[event_name].append(callback_id)
        else:
            params: dict[str, Any] = {}
            params["events"] = [event_name]
            self.conn.execute(command_builder("session.subscribe", params))
            self.subscriptions[event_name] = [callback_id]

        self.callbacks[callback_id] = result["intercept"]
        return callback_id

    def remove_request_handler(self, event: str, callback_id: int) -> None:
        """Remove a request handler from the network.

        Args:
            event: The event to unsubscribe from.
            callback_id: The callback id to remove.
        """
        try:
            event_name = self.EVENTS[event]
        except KeyError:
            raise Exception(f"Event {event} not found")

        net_event = NetworkEvent(event_name)

        self.conn.remove_callback(net_event, callback_id)
        self._remove_intercept(self.callbacks[callback_id])
        del self.callbacks[callback_id]
        self.subscriptions[event_name].remove(callback_id)
        if len(self.subscriptions[event_name]) == 0:
            params: dict[str, Any] = {}
            params["events"] = [event_name]
            self.conn.execute(command_builder("session.unsubscribe", params))
            del self.subscriptions[event_name]

    def clear_request_handlers(self) -> None:
        """Clear all request handlers from the network."""
        for event_name in self.subscriptions:
            net_event = NetworkEvent(event_name)
            for callback_id in self.subscriptions[event_name]:
                self.conn.remove_callback(net_event, callback_id)
                self._remove_intercept(self.callbacks[callback_id])
                del self.callbacks[callback_id]
            params: dict[str, Any] = {}
            params["events"] = [event_name]
            self.conn.execute(command_builder("session.unsubscribe", params))
        self.subscriptions = {}

    def add_auth_handler(self, username: str, password: str) -> int:
        """Add an authentication handler to the network.

        Args:
            username: The username to authenticate with.
            password: The password to authenticate with.

        Returns:
            int: callback id
        """
        event = "auth_required"

        def _callback(request: Request) -> None:
            request._continue_with_auth(username, password)

        return self.add_request_handler(event, _callback)

    def remove_auth_handler(self, callback_id: int) -> None:
        """Remove an authentication handler from the network.

        Args:
            callback_id: The callback id to remove.
        """
        event = "auth_required"
        self.remove_request_handler(event, callback_id)


class Request:
    """Represents an intercepted network request."""

    def __init__(
        self,
        network: Network,
        request_id: Any,
        body_size: int | None = None,
        cookies: Any = None,
        resource_type: str | None = None,
        headers: Any = None,
        headers_size: int | None = None,
        method: str | None = None,
        timings: Any = None,
        url: str | None = None,
    ) -> None:
        self.network = network
        self.request_id = request_id
        self.body_size = body_size
        self.cookies = cookies
        self.resource_type = resource_type
        self.headers = headers
        self.headers_size = headers_size
        self.method = method
        self.timings = timings
        self.url = url

    def fail_request(self) -> None:
        """Fail this request."""
        if not self.request_id:
            raise ValueError("Request not found.")

        params: dict[str, Any] = {"request": self.request_id}
        self.network.conn.execute(command_builder("network.failRequest", params))

    def continue_request(
        self,
        body: Any = None,
        method: str | None = None,
        headers: Any = None,
        cookies: Any = None,
        url: str | None = None,
    ) -> None:
        """Continue after intercepting this request."""
        if not self.request_id:
            raise ValueError("Request not found.")

        params: dict[str, Any] = {"request": self.request_id}
        if body is not None:
            params["body"] = body
        if method is not None:
            params["method"] = method
        if headers is not None:
            params["headers"] = headers
        if cookies is not None:
            params["cookies"] = cookies
        if url is not None:
            params["url"] = url

        self.network.conn.execute(command_builder("network.continueRequest", params))

    def _continue_with_auth(self, username: str | None = None, password: str | None = None) -> None:
        """Continue with authentication.

        Args:
            username: The username to authenticate with.
            password: The password to authenticate with.

        Note:
            If username or password is None, it attempts auth with no credentials.
        """
        params: dict[str, Any] = {}
        params["request"] = self.request_id

        if not username or not password:  # no credentials is valid option
            params["action"] = "default"
        else:
            params["action"] = "provideCredentials"
            params["credentials"] = {"type": "password", "username": username, "password": password}

        self.network.conn.execute(command_builder("network.continueWithAuth", params))
