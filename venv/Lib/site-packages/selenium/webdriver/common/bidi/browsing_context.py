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

import threading
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from typing_extensions import Sentinel

from selenium.webdriver.common.bidi.common import command_builder
from selenium.webdriver.common.bidi.session import Session

UNDEFINED = Sentinel("UNDEFINED")


class ReadinessState:
    """Represents the stage of document loading at which a navigation command will return."""

    NONE = "none"
    INTERACTIVE = "interactive"
    COMPLETE = "complete"


class UserPromptType:
    """Represents the possible user prompt types."""

    ALERT = "alert"
    BEFORE_UNLOAD = "beforeunload"
    CONFIRM = "confirm"
    PROMPT = "prompt"


class NavigationInfo:
    """Provides details of an ongoing navigation."""

    def __init__(
        self,
        context: str,
        navigation: str | None,
        timestamp: int,
        url: str,
    ):
        self.context = context
        self.navigation = navigation
        self.timestamp = timestamp
        self.url = url

    @classmethod
    def from_json(cls, json: dict) -> "NavigationInfo":
        """Creates a NavigationInfo instance from a dictionary.

        Args:
            json: A dictionary containing the navigation information.

        Returns:
            A new instance of NavigationInfo.
        """
        context = json.get("context")
        if context is None or not isinstance(context, str):
            raise ValueError("context is required and must be a string")

        navigation = json.get("navigation")
        if navigation is not None and not isinstance(navigation, str):
            raise ValueError("navigation must be a string")

        timestamp = json.get("timestamp")
        if timestamp is None or not isinstance(timestamp, int) or timestamp < 0:
            raise ValueError("timestamp is required and must be a non-negative integer")

        url = json.get("url")
        if url is None or not isinstance(url, str):
            raise ValueError("url is required and must be a string")

        return cls(context, navigation, timestamp, url)


class BrowsingContextInfo:
    """Represents the properties of a navigable."""

    def __init__(
        self,
        context: str,
        url: str,
        children: list["BrowsingContextInfo"] | None,
        client_window: str,
        user_context: str,
        parent: str | None = None,
        original_opener: str | None = None,
    ):
        self.context = context
        self.url = url
        self.children = children
        self.parent = parent
        self.user_context = user_context
        self.original_opener = original_opener
        self.client_window = client_window

    @classmethod
    def from_json(cls, json: dict) -> "BrowsingContextInfo":
        """Creates a BrowsingContextInfo instance from a dictionary.

        Args:
            json: A dictionary containing the browsing context information.

        Returns:
            A new instance of BrowsingContextInfo.
        """
        children = None
        raw_children = json.get("children")
        if raw_children is not None:
            if not isinstance(raw_children, list):
                raise ValueError("children must be a list if provided")

            children = []
            for child in raw_children:
                if not isinstance(child, dict):
                    raise ValueError(f"Each child must be a dictionary, got {type(child)}")
                children.append(BrowsingContextInfo.from_json(child))

        context = json.get("context")
        if context is None or not isinstance(context, str):
            raise ValueError("context is required and must be a string")

        url = json.get("url")
        if url is None or not isinstance(url, str):
            raise ValueError("url is required and must be a string")

        parent = json.get("parent")
        if parent is not None and not isinstance(parent, str):
            raise ValueError("parent must be a string if provided")

        user_context = json.get("userContext")
        if user_context is None or not isinstance(user_context, str):
            raise ValueError("userContext is required and must be a string")

        original_opener = json.get("originalOpener")
        if original_opener is not None and not isinstance(original_opener, str):
            raise ValueError("originalOpener must be a string if provided")

        client_window = json.get("clientWindow")
        if client_window is None or not isinstance(client_window, str):
            raise ValueError("clientWindow is required and must be a string")

        return cls(
            context=context,
            url=url,
            children=children,
            client_window=client_window,
            user_context=user_context,
            parent=parent,
            original_opener=original_opener,
        )


class DownloadWillBeginParams(NavigationInfo):
    """Parameters for the downloadWillBegin event."""

    def __init__(
        self,
        context: str,
        navigation: str | None,
        timestamp: int,
        url: str,
        suggested_filename: str,
    ):
        super().__init__(context, navigation, timestamp, url)
        self.suggested_filename = suggested_filename

    @classmethod
    def from_json(cls, json: dict) -> "DownloadWillBeginParams":
        nav_info = NavigationInfo.from_json(json)

        suggested_filename = json.get("suggestedFilename")
        if suggested_filename is None or not isinstance(suggested_filename, str):
            raise ValueError("suggestedFilename is required and must be a string")

        return cls(
            context=nav_info.context,
            navigation=nav_info.navigation,
            timestamp=nav_info.timestamp,
            url=nav_info.url,
            suggested_filename=suggested_filename,
        )


class UserPromptOpenedParams:
    """Parameters for the userPromptOpened event."""

    def __init__(
        self,
        context: str,
        handler: str,
        message: str,
        type: str,
        default_value: str | None = None,
    ):
        self.context = context
        self.handler = handler
        self.message = message
        self.type = type
        self.default_value = default_value

    @classmethod
    def from_json(cls, json: dict) -> "UserPromptOpenedParams":
        """Creates a UserPromptOpenedParams instance from a dictionary.

        Args:
            json: A dictionary containing the user prompt parameters.

        Returns:
            A new instance of UserPromptOpenedParams.
        """
        context = json.get("context")
        if context is None or not isinstance(context, str):
            raise ValueError("context is required and must be a string")

        handler = json.get("handler")
        if handler is None or not isinstance(handler, str):
            raise ValueError("handler is required and must be a string")

        message = json.get("message")
        if message is None or not isinstance(message, str):
            raise ValueError("message is required and must be a string")

        type_value = json.get("type")
        if type_value is None or not isinstance(type_value, str):
            raise ValueError("type is required and must be a string")

        default_value = json.get("defaultValue")
        if default_value is not None and not isinstance(default_value, str):
            raise ValueError("defaultValue must be a string if provided")

        return cls(
            context=context,
            handler=handler,
            message=message,
            type=type_value,
            default_value=default_value,
        )


class UserPromptClosedParams:
    """Parameters for the userPromptClosed event."""

    def __init__(
        self,
        context: str,
        accepted: bool,
        type: str,
        user_text: str | None = None,
    ):
        self.context = context
        self.accepted = accepted
        self.type = type
        self.user_text = user_text

    @classmethod
    def from_json(cls, json: dict) -> "UserPromptClosedParams":
        """Creates a UserPromptClosedParams instance from a dictionary.

        Args:
            json: A dictionary containing the user prompt closed parameters.

        Returns:
            A new instance of UserPromptClosedParams.
        """
        context = json.get("context")
        if context is None or not isinstance(context, str):
            raise ValueError("context is required and must be a string")

        accepted = json.get("accepted")
        if accepted is None or not isinstance(accepted, bool):
            raise ValueError("accepted is required and must be a boolean")

        type_value = json.get("type")
        if type_value is None or not isinstance(type_value, str):
            raise ValueError("type is required and must be a string")

        user_text = json.get("userText")
        if user_text is not None and not isinstance(user_text, str):
            raise ValueError("userText must be a string if provided")

        return cls(
            context=context,
            accepted=accepted,
            type=type_value,
            user_text=user_text,
        )


class HistoryUpdatedParams:
    """Parameters for the historyUpdated event."""

    def __init__(
        self,
        context: str,
        timestamp: int,
        url: str,
    ):
        self.context = context
        self.timestamp = timestamp
        self.url = url

    @classmethod
    def from_json(cls, json: dict) -> "HistoryUpdatedParams":
        """Creates a HistoryUpdatedParams instance from a dictionary.

        Args:
            json: A dictionary containing the history updated parameters.

        Returns:
            A new instance of HistoryUpdatedParams.
        """
        context = json.get("context")
        if context is None or not isinstance(context, str):
            raise ValueError("context is required and must be a string")

        timestamp = json.get("timestamp")
        if timestamp is None or not isinstance(timestamp, int) or timestamp < 0:
            raise ValueError("timestamp is required and must be a non-negative integer")

        url = json.get("url")
        if url is None or not isinstance(url, str):
            raise ValueError("url is required and must be a string")

        return cls(
            context=context,
            timestamp=timestamp,
            url=url,
        )


class DownloadCanceledParams(NavigationInfo):
    def __init__(
        self,
        context: str,
        navigation: str | None,
        timestamp: int,
        url: str,
        status: str = "canceled",
    ):
        super().__init__(context, navigation, timestamp, url)
        self.status = status

    @classmethod
    def from_json(cls, json: dict) -> "DownloadCanceledParams":
        nav_info = NavigationInfo.from_json(json)

        status = json.get("status")
        if status is None or status != "canceled":
            raise ValueError("status is required and must be 'canceled'")

        return cls(
            context=nav_info.context,
            navigation=nav_info.navigation,
            timestamp=nav_info.timestamp,
            url=nav_info.url,
            status=status,
        )


class DownloadCompleteParams(NavigationInfo):
    def __init__(
        self,
        context: str,
        navigation: str | None,
        timestamp: int,
        url: str,
        status: str = "complete",
        filepath: str | None = None,
    ):
        super().__init__(context, navigation, timestamp, url)
        self.status = status
        self.filepath = filepath

    @classmethod
    def from_json(cls, json: dict) -> "DownloadCompleteParams":
        nav_info = NavigationInfo.from_json(json)

        status = json.get("status")
        if status is None or status != "complete":
            raise ValueError("status is required and must be 'complete'")

        filepath = json.get("filepath")
        if filepath is not None and not isinstance(filepath, str):
            raise ValueError("filepath must be a string if provided")

        return cls(
            context=nav_info.context,
            navigation=nav_info.navigation,
            timestamp=nav_info.timestamp,
            url=nav_info.url,
            status=status,
            filepath=filepath,
        )


class DownloadEndParams:
    """Parameters for the downloadEnd event."""

    def __init__(
        self,
        download_params: DownloadCanceledParams | DownloadCompleteParams,
    ):
        self.download_params = download_params

    @classmethod
    def from_json(cls, json: dict) -> "DownloadEndParams":
        status = json.get("status")
        if status == "canceled":
            return cls(DownloadCanceledParams.from_json(json))
        elif status == "complete":
            return cls(DownloadCompleteParams.from_json(json))
        else:
            raise ValueError("status must be either 'canceled' or 'complete'")


class ContextCreated:
    """Event class for browsingContext.contextCreated event."""

    event_class = "browsingContext.contextCreated"

    @classmethod
    def from_json(cls, json: dict):
        if isinstance(json, BrowsingContextInfo):
            return json
        return BrowsingContextInfo.from_json(json)


class ContextDestroyed:
    """Event class for browsingContext.contextDestroyed event."""

    event_class = "browsingContext.contextDestroyed"

    @classmethod
    def from_json(cls, json: dict):
        if isinstance(json, BrowsingContextInfo):
            return json
        return BrowsingContextInfo.from_json(json)


class NavigationStarted:
    """Event class for browsingContext.navigationStarted event."""

    event_class = "browsingContext.navigationStarted"

    @classmethod
    def from_json(cls, json: dict):
        if isinstance(json, NavigationInfo):
            return json
        return NavigationInfo.from_json(json)


class NavigationCommitted:
    """Event class for browsingContext.navigationCommitted event."""

    event_class = "browsingContext.navigationCommitted"

    @classmethod
    def from_json(cls, json: dict):
        if isinstance(json, NavigationInfo):
            return json
        return NavigationInfo.from_json(json)


class NavigationFailed:
    """Event class for browsingContext.navigationFailed event."""

    event_class = "browsingContext.navigationFailed"

    @classmethod
    def from_json(cls, json: dict):
        if isinstance(json, NavigationInfo):
            return json
        return NavigationInfo.from_json(json)


class NavigationAborted:
    """Event class for browsingContext.navigationAborted event."""

    event_class = "browsingContext.navigationAborted"

    @classmethod
    def from_json(cls, json: dict):
        if isinstance(json, NavigationInfo):
            return json
        return NavigationInfo.from_json(json)


class DomContentLoaded:
    """Event class for browsingContext.domContentLoaded event."""

    event_class = "browsingContext.domContentLoaded"

    @classmethod
    def from_json(cls, json: dict):
        if isinstance(json, NavigationInfo):
            return json
        return NavigationInfo.from_json(json)


class Load:
    """Event class for browsingContext.load event."""

    event_class = "browsingContext.load"

    @classmethod
    def from_json(cls, json: dict):
        if isinstance(json, NavigationInfo):
            return json
        return NavigationInfo.from_json(json)


class FragmentNavigated:
    """Event class for browsingContext.fragmentNavigated event."""

    event_class = "browsingContext.fragmentNavigated"

    @classmethod
    def from_json(cls, json: dict):
        if isinstance(json, NavigationInfo):
            return json
        return NavigationInfo.from_json(json)


class DownloadWillBegin:
    """Event class for browsingContext.downloadWillBegin event."""

    event_class = "browsingContext.downloadWillBegin"

    @classmethod
    def from_json(cls, json: dict):
        return DownloadWillBeginParams.from_json(json)


class UserPromptOpened:
    """Event class for browsingContext.userPromptOpened event."""

    event_class = "browsingContext.userPromptOpened"

    @classmethod
    def from_json(cls, json: dict):
        return UserPromptOpenedParams.from_json(json)


class UserPromptClosed:
    """Event class for browsingContext.userPromptClosed event."""

    event_class = "browsingContext.userPromptClosed"

    @classmethod
    def from_json(cls, json: dict):
        return UserPromptClosedParams.from_json(json)


class HistoryUpdated:
    """Event class for browsingContext.historyUpdated event."""

    event_class = "browsingContext.historyUpdated"

    @classmethod
    def from_json(cls, json: dict):
        return HistoryUpdatedParams.from_json(json)


class DownloadEnd:
    """Event class for browsingContext.downloadEnd event."""

    event_class = "browsingContext.downloadEnd"

    @classmethod
    def from_json(cls, json: dict):
        return DownloadEndParams.from_json(json)


@dataclass
class EventConfig:
    event_key: str
    bidi_event: str
    event_class: type


class _EventManager:
    """Class to manage event subscriptions and callbacks for BrowsingContext."""

    def __init__(self, conn, event_configs: dict[str, EventConfig]):
        self.conn = conn
        self.event_configs = event_configs
        self.subscriptions: dict = {}
        self._bidi_to_class = {config.bidi_event: config.event_class for config in event_configs.values()}
        self._available_events = ", ".join(sorted(event_configs.keys()))
        # Thread safety lock for subscription operations
        self._subscription_lock = threading.Lock()

    def validate_event(self, event: str) -> EventConfig:
        event_config = self.event_configs.get(event)
        if not event_config:
            raise ValueError(f"Event '{event}' not found. Available events: {self._available_events}")
        return event_config

    def subscribe_to_event(self, bidi_event: str, contexts: list[str] | None = None) -> None:
        """Subscribe to a BiDi event if not already subscribed.

        Args:
            bidi_event: The BiDi event name.
            contexts: Optional browsing context IDs to subscribe to.
        """
        with self._subscription_lock:
            if bidi_event not in self.subscriptions:
                session = Session(self.conn)
                self.conn.execute(session.subscribe(bidi_event, browsing_contexts=contexts))
                self.subscriptions[bidi_event] = []

    def unsubscribe_from_event(self, bidi_event: str) -> None:
        """Unsubscribe from a BiDi event if no more callbacks exist.

        Args:
            bidi_event: The BiDi event name.
        """
        with self._subscription_lock:
            callback_list = self.subscriptions.get(bidi_event)
            if callback_list is not None and not callback_list:
                session = Session(self.conn)
                self.conn.execute(session.unsubscribe(bidi_event))
                del self.subscriptions[bidi_event]

    def add_callback_to_tracking(self, bidi_event: str, callback_id: int) -> None:
        with self._subscription_lock:
            self.subscriptions[bidi_event].append(callback_id)

    def remove_callback_from_tracking(self, bidi_event: str, callback_id: int) -> None:
        with self._subscription_lock:
            callback_list = self.subscriptions.get(bidi_event)
            if callback_list and callback_id in callback_list:
                callback_list.remove(callback_id)

    def add_event_handler(self, event: str, callback: Callable, contexts: list[str] | None = None) -> int:
        event_config = self.validate_event(event)

        callback_id = self.conn.add_callback(event_config.event_class, callback)

        # Subscribe to the event if needed
        self.subscribe_to_event(event_config.bidi_event, contexts)

        # Track the callback
        self.add_callback_to_tracking(event_config.bidi_event, callback_id)

        return callback_id

    def remove_event_handler(self, event: str, callback_id: int) -> None:
        event_config = self.validate_event(event)

        # Remove the callback from the connection
        self.conn.remove_callback(event_config.event_class, callback_id)

        # Remove from tracking collections
        self.remove_callback_from_tracking(event_config.bidi_event, callback_id)

        # Unsubscribe if no more callbacks exist
        self.unsubscribe_from_event(event_config.bidi_event)

    def clear_event_handlers(self) -> None:
        """Clear all event handlers from the browsing context."""
        with self._subscription_lock:
            if not self.subscriptions:
                return

            session = Session(self.conn)

            for bidi_event, callback_ids in list(self.subscriptions.items()):
                event_class = self._bidi_to_class.get(bidi_event)
                if event_class:
                    # Remove all callbacks for this event
                    for callback_id in callback_ids:
                        self.conn.remove_callback(event_class, callback_id)

                    self.conn.execute(session.unsubscribe(bidi_event))

            self.subscriptions.clear()


class BrowsingContext:
    """BiDi implementation of the browsingContext module."""

    EVENT_CONFIGS = {
        "context_created": EventConfig("context_created", "browsingContext.contextCreated", ContextCreated),
        "context_destroyed": EventConfig("context_destroyed", "browsingContext.contextDestroyed", ContextDestroyed),
        "dom_content_loaded": EventConfig("dom_content_loaded", "browsingContext.domContentLoaded", DomContentLoaded),
        "download_end": EventConfig("download_end", "browsingContext.downloadEnd", DownloadEnd),
        "download_will_begin": EventConfig(
            "download_will_begin", "browsingContext.downloadWillBegin", DownloadWillBegin
        ),
        "fragment_navigated": EventConfig("fragment_navigated", "browsingContext.fragmentNavigated", FragmentNavigated),
        "history_updated": EventConfig("history_updated", "browsingContext.historyUpdated", HistoryUpdated),
        "load": EventConfig("load", "browsingContext.load", Load),
        "navigation_aborted": EventConfig("navigation_aborted", "browsingContext.navigationAborted", NavigationAborted),
        "navigation_committed": EventConfig(
            "navigation_committed", "browsingContext.navigationCommitted", NavigationCommitted
        ),
        "navigation_failed": EventConfig("navigation_failed", "browsingContext.navigationFailed", NavigationFailed),
        "navigation_started": EventConfig("navigation_started", "browsingContext.navigationStarted", NavigationStarted),
        "user_prompt_closed": EventConfig("user_prompt_closed", "browsingContext.userPromptClosed", UserPromptClosed),
        "user_prompt_opened": EventConfig("user_prompt_opened", "browsingContext.userPromptOpened", UserPromptOpened),
    }

    def __init__(self, conn):
        self.conn = conn
        self._event_manager = _EventManager(conn, self.EVENT_CONFIGS)

    @classmethod
    def get_event_names(cls) -> list[str]:
        """Get a list of all available event names.

        Returns:
            A list of event names that can be used with event handlers.
        """
        return list(cls.EVENT_CONFIGS.keys())

    def activate(self, context: str) -> None:
        """Activates and focuses the given top-level traversable.

        Args:
            context: The browsing context ID to activate.

        Raises:
            Exception: If the browsing context is not a top-level traversable.
        """
        params = {"context": context}
        self.conn.execute(command_builder("browsingContext.activate", params))

    def capture_screenshot(
        self,
        context: str,
        origin: str = "viewport",
        format: dict | None = None,
        clip: dict | None = None,
    ) -> str:
        """Captures an image of the given navigable, and returns it as a Base64-encoded string.

        Args:
            context: The browsing context ID to capture.
            origin: The origin of the screenshot, either "viewport" or "document".
            format: The format of the screenshot.
            clip: The clip rectangle of the screenshot.

        Returns:
            The Base64-encoded screenshot.
        """
        params: dict[str, Any] = {"context": context, "origin": origin}
        if format is not None:
            params["format"] = format
        if clip is not None:
            params["clip"] = clip

        result = self.conn.execute(command_builder("browsingContext.captureScreenshot", params))
        return result["data"]

    def close(self, context: str, prompt_unload: bool = False) -> None:
        """Closes a top-level traversable.

        Args:
            context: The browsing context ID to close.
            prompt_unload: Whether to prompt to unload.

        Raises:
            Exception: If the browsing context is not a top-level traversable.
        """
        params = {"context": context, "promptUnload": prompt_unload}
        self.conn.execute(command_builder("browsingContext.close", params))

    def create(
        self,
        type: str,
        reference_context: str | None = None,
        background: bool = False,
        user_context: str | None = None,
    ) -> str:
        """Creates a new navigable, either in a new tab or in a new window, and returns its navigable id.

        Args:
            type: The type of the new navigable, either "tab" or "window".
            reference_context: The reference browsing context ID.
            background: Whether to create the new navigable in the background.
            user_context: The user context ID.

        Returns:
            The browsing context ID of the created navigable.
        """
        params: dict[str, Any] = {"type": type}
        if reference_context is not None:
            params["referenceContext"] = reference_context
        if background is not None:
            params["background"] = background
        if user_context is not None:
            params["userContext"] = user_context

        result = self.conn.execute(command_builder("browsingContext.create", params))
        return result["context"]

    def get_tree(
        self,
        max_depth: int | None = None,
        root: str | None = None,
    ) -> list[BrowsingContextInfo]:
        """Get a tree of all descendent navigables including the given parent itself.

        Returns a tree of all descendent navigables including the given parent itself, or all top-level contexts
        when no parent is provided.

        Args:
            max_depth: The maximum depth of the tree.
            root: The root browsing context ID.

        Returns:
            A list of browsing context information.
        """
        params: dict[str, Any] = {}
        if max_depth is not None:
            params["maxDepth"] = max_depth
        if root is not None:
            params["root"] = root

        result = self.conn.execute(command_builder("browsingContext.getTree", params))
        return [BrowsingContextInfo.from_json(context) for context in result["contexts"]]

    def handle_user_prompt(
        self,
        context: str,
        accept: bool | None = None,
        user_text: str | None = None,
    ) -> None:
        """Allows closing an open prompt.

        Args:
            context: The browsing context ID.
            accept: Whether to accept the prompt.
            user_text: The text to enter in the prompt.
        """
        params: dict[str, Any] = {"context": context}
        if accept is not None:
            params["accept"] = accept
        if user_text is not None:
            params["userText"] = user_text

        self.conn.execute(command_builder("browsingContext.handleUserPrompt", params))

    def locate_nodes(
        self,
        context: str,
        locator: dict,
        max_node_count: int | None = None,
        serialization_options: dict | None = None,
        start_nodes: list[dict] | None = None,
    ) -> list[dict]:
        """Returns a list of all nodes matching the specified locator.

        Args:
            context: The browsing context ID.
            locator: The locator to use.
            max_node_count: The maximum number of nodes to return.
            serialization_options: The serialization options.
            start_nodes: The start nodes.

        Returns:
            A list of nodes.
        """
        params: dict[str, Any] = {"context": context, "locator": locator}
        if max_node_count is not None:
            params["maxNodeCount"] = max_node_count
        if serialization_options is not None:
            params["serializationOptions"] = serialization_options
        if start_nodes is not None:
            params["startNodes"] = start_nodes

        result = self.conn.execute(command_builder("browsingContext.locateNodes", params))
        return result["nodes"]

    def navigate(
        self,
        context: str,
        url: str,
        wait: str | None = None,
    ) -> dict:
        """Navigates a navigable to the given URL.

        Args:
            context: The browsing context ID.
            url: The URL to navigate to.
            wait: The readiness state to wait for.

        Returns:
            A dictionary containing the navigation result.
        """
        params = {"context": context, "url": url}
        if wait is not None:
            params["wait"] = wait

        result = self.conn.execute(command_builder("browsingContext.navigate", params))
        return result

    def print(
        self,
        context: str,
        background: bool = False,
        margin: dict | None = None,
        orientation: str = "portrait",
        page: dict | None = None,
        page_ranges: list[int | str] | None = None,
        scale: float = 1.0,
        shrink_to_fit: bool = True,
    ) -> str:
        """Create a paginated PDF representation of the document as a Base64-encoded string.

        Args:
            context: The browsing context ID.
            background: Whether to include the background.
            margin: The margin parameters.
            orientation: The orientation, either "portrait" or "landscape".
            page: The page parameters.
            page_ranges: The page ranges.
            scale: The scale.
            shrink_to_fit: Whether to shrink to fit.

        Returns:
            The Base64-encoded PDF document.
        """
        params = {
            "context": context,
            "background": background,
            "orientation": orientation,
            "scale": scale,
            "shrinkToFit": shrink_to_fit,
        }
        if margin is not None:
            params["margin"] = margin
        if page is not None:
            params["page"] = page
        if page_ranges is not None:
            params["pageRanges"] = page_ranges

        result = self.conn.execute(command_builder("browsingContext.print", params))
        return result["data"]

    def reload(
        self,
        context: str,
        ignore_cache: bool | None = None,
        wait: str | None = None,
    ) -> dict:
        """Reloads a navigable.

        Args:
            context: The browsing context ID.
            ignore_cache: Whether to ignore the cache.
            wait: The readiness state to wait for.

        Returns:
            A dictionary containing the navigation result.
        """
        params: dict[str, Any] = {"context": context}
        if ignore_cache is not None:
            params["ignoreCache"] = ignore_cache
        if wait is not None:
            params["wait"] = wait

        result = self.conn.execute(command_builder("browsingContext.reload", params))
        return result

    def set_viewport(
        self,
        context: str | None = None,
        viewport: dict | None | Sentinel = UNDEFINED,
        device_pixel_ratio: float | None | Sentinel = UNDEFINED,
        user_contexts: list[str] | None = None,
    ) -> None:
        """Modifies specific viewport characteristics on the given top-level traversable.

        Args:
            context: The browsing context ID.
            viewport: The viewport parameters - {"width": <int>, "height": <int>} (`None` resets to default).
            device_pixel_ratio: The device pixel ratio (`None` resets to default).
            user_contexts: The user context IDs.

        Raises:
            Exception: If the browsing context is not a top-level traversable
            ValueError: If neither `context` nor `user_contexts` is provided
            ValueError: If both `context` and `user_contexts` are provided
        """
        if context is not None and user_contexts is not None:
            raise ValueError("Cannot specify both context and user_contexts")

        if context is None and user_contexts is None:
            raise ValueError("Must specify either context or user_contexts")

        params: dict[str, Any] = {}
        if context is not None:
            params["context"] = context
        elif user_contexts is not None:
            params["userContexts"] = user_contexts
        if viewport is not UNDEFINED:
            params["viewport"] = viewport
        if device_pixel_ratio is not UNDEFINED:
            params["devicePixelRatio"] = device_pixel_ratio

        self.conn.execute(command_builder("browsingContext.setViewport", params))

    def traverse_history(self, context: str, delta: int) -> dict:
        """Traverses the history of a given navigable by a delta.

        Args:
            context: The browsing context ID.
            delta: The delta to traverse by.

        Returns:
            A dictionary containing the traverse history result.
        """
        params = {"context": context, "delta": delta}
        result = self.conn.execute(command_builder("browsingContext.traverseHistory", params))
        return result

    def add_event_handler(self, event: str, callback: Callable, contexts: list[str] | None = None) -> int:
        """Add an event handler to the browsing context.

        Args:
            event: The event to subscribe to.
            callback: The callback function to execute on event.
            contexts: The browsing context IDs to subscribe to.

        Returns:
            Callback id.
        """
        return self._event_manager.add_event_handler(event, callback, contexts)

    def remove_event_handler(self, event: str, callback_id: int) -> None:
        """Remove an event handler from the browsing context.

        Args:
            event: The event to unsubscribe from.
            callback_id: The callback id to remove.
        """
        self._event_manager.remove_event_handler(event, callback_id)

    def clear_event_handlers(self) -> None:
        """Clear all event handlers from the browsing context."""
        self._event_manager.clear_event_handlers()
