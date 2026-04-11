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

import datetime
import math
from dataclasses import dataclass
from typing import Any

from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.bidi.common import command_builder
from selenium.webdriver.common.bidi.log import LogEntryAdded
from selenium.webdriver.common.bidi.session import Session


class ResultOwnership:
    """Represents the possible result ownership types."""

    NONE = "none"
    ROOT = "root"


class RealmType:
    """Represents the possible realm types."""

    WINDOW = "window"
    DEDICATED_WORKER = "dedicated-worker"
    SHARED_WORKER = "shared-worker"
    SERVICE_WORKER = "service-worker"
    WORKER = "worker"
    PAINT_WORKLET = "paint-worklet"
    AUDIO_WORKLET = "audio-worklet"
    WORKLET = "worklet"


@dataclass
class RealmInfo:
    """Represents information about a realm."""

    realm: str
    origin: str
    type: str
    context: str | None = None
    sandbox: str | None = None

    @classmethod
    def from_json(cls, json: dict[str, Any]) -> "RealmInfo":
        """Creates a RealmInfo instance from a dictionary.

        Args:
            json: A dictionary containing the realm information.

        Returns:
            RealmInfo: A new instance of RealmInfo.
        """
        if "realm" not in json:
            raise ValueError("Missing required field 'realm' in RealmInfo")
        if "origin" not in json:
            raise ValueError("Missing required field 'origin' in RealmInfo")
        if "type" not in json:
            raise ValueError("Missing required field 'type' in RealmInfo")

        return cls(
            realm=json["realm"],
            origin=json["origin"],
            type=json["type"],
            context=json.get("context"),
            sandbox=json.get("sandbox"),
        )


@dataclass
class Source:
    """Represents the source of a script message."""

    realm: str
    context: str | None = None

    @classmethod
    def from_json(cls, json: dict[str, Any]) -> "Source":
        """Creates a Source instance from a dictionary.

        Args:
            json: A dictionary containing the source information.

        Returns:
            Source: A new instance of Source.
        """
        if "realm" not in json:
            raise ValueError("Missing required field 'realm' in Source")

        return cls(
            realm=json["realm"],
            context=json.get("context"),
        )


@dataclass
class EvaluateResult:
    """Represents the result of script evaluation."""

    type: str
    realm: str
    result: dict | None = None
    exception_details: dict | None = None

    @classmethod
    def from_json(cls, json: dict[str, Any]) -> "EvaluateResult":
        """Creates an EvaluateResult instance from a dictionary.

        Args:
            json: A dictionary containing the evaluation result.

        Returns:
            EvaluateResult: A new instance of EvaluateResult.
        """
        if "realm" not in json:
            raise ValueError("Missing required field 'realm' in EvaluateResult")
        if "type" not in json:
            raise ValueError("Missing required field 'type' in EvaluateResult")

        return cls(
            type=json["type"],
            realm=json["realm"],
            result=json.get("result"),
            exception_details=json.get("exceptionDetails"),
        )


class ScriptMessage:
    """Represents a script message event."""

    event_class = "script.message"

    def __init__(self, channel: str, data: dict, source: Source):
        self.channel = channel
        self.data = data
        self.source = source

    @classmethod
    def from_json(cls, json: dict[str, Any]) -> "ScriptMessage":
        """Creates a ScriptMessage instance from a dictionary.

        Args:
            json: A dictionary containing the script message.

        Returns:
            ScriptMessage: A new instance of ScriptMessage.
        """
        if "channel" not in json:
            raise ValueError("Missing required field 'channel' in ScriptMessage")
        if "data" not in json:
            raise ValueError("Missing required field 'data' in ScriptMessage")
        if "source" not in json:
            raise ValueError("Missing required field 'source' in ScriptMessage")

        return cls(
            channel=json["channel"],
            data=json["data"],
            source=Source.from_json(json["source"]),
        )


class RealmCreated:
    """Represents a realm created event."""

    event_class = "script.realmCreated"

    def __init__(self, realm_info: RealmInfo):
        self.realm_info = realm_info

    @classmethod
    def from_json(cls, json: dict[str, Any]) -> "RealmCreated":
        """Creates a RealmCreated instance from a dictionary.

        Args:
            json: A dictionary containing the realm created event.

        Returns:
            RealmCreated: A new instance of RealmCreated.
        """
        return cls(realm_info=RealmInfo.from_json(json))


class RealmDestroyed:
    """Represents a realm destroyed event."""

    event_class = "script.realmDestroyed"

    def __init__(self, realm: str):
        self.realm = realm

    @classmethod
    def from_json(cls, json: dict[str, Any]) -> "RealmDestroyed":
        """Creates a RealmDestroyed instance from a dictionary.

        Args:
            json: A dictionary containing the realm destroyed event.

        Returns:
            RealmDestroyed: A new instance of RealmDestroyed.
        """
        if "realm" not in json:
            raise ValueError("Missing required field 'realm' in RealmDestroyed")

        return cls(realm=json["realm"])


class Script:
    """BiDi implementation of the script module."""

    EVENTS = {
        "message": "script.message",
        "realm_created": "script.realmCreated",
        "realm_destroyed": "script.realmDestroyed",
    }

    def __init__(self, conn, driver=None):
        self.conn = conn
        self.driver = driver
        self.log_entry_subscribed = False
        self.subscriptions = {}
        self.callbacks = {}

    # High-level APIs for SCRIPT module

    def add_console_message_handler(self, handler):
        self._subscribe_to_log_entries()
        return self.conn.add_callback(LogEntryAdded, self._handle_log_entry("console", handler))

    def add_javascript_error_handler(self, handler):
        self._subscribe_to_log_entries()
        return self.conn.add_callback(LogEntryAdded, self._handle_log_entry("javascript", handler))

    def remove_console_message_handler(self, id):
        self.conn.remove_callback(LogEntryAdded, id)
        self._unsubscribe_from_log_entries()

    remove_javascript_error_handler = remove_console_message_handler

    def pin(self, script: str) -> str:
        """Pins a script to the current browsing context.

        Args:
            script: The script to pin.

        Returns:
            str: The ID of the pinned script.
        """
        return self._add_preload_script(script)

    def unpin(self, script_id: str) -> None:
        """Unpins a script from the current browsing context.

        Args:
            script_id: The ID of the pinned script to unpin.
        """
        self._remove_preload_script(script_id)

    def execute(self, script: str, *args) -> dict:
        """Executes a script in the current browsing context.

        Args:
            script: The script function to execute.
            *args: Arguments to pass to the script function.

        Returns:
            dict: The result value from the script execution.

        Raises:
            WebDriverException: If the script execution fails.
        """
        if self.driver is None:
            raise WebDriverException("Driver reference is required for script execution")
        browsing_context_id = self.driver.current_window_handle

        # Convert arguments to the format expected by BiDi call_function (LocalValue Type)
        arguments = []
        for arg in args:
            arguments.append(self.__convert_to_local_value(arg))

        target = {"context": browsing_context_id}

        result = self._call_function(
            function_declaration=script, await_promise=True, target=target, arguments=arguments if arguments else None
        )

        if result.type == "success":
            return result.result if result.result is not None else {}
        else:
            error_message = "Error while executing script"
            if result.exception_details:
                if "text" in result.exception_details:
                    error_message += f": {result.exception_details['text']}"
                elif "message" in result.exception_details:
                    error_message += f": {result.exception_details['message']}"

            raise WebDriverException(error_message)

    def __convert_to_local_value(self, value) -> dict:
        """Converts a Python value to BiDi LocalValue format."""
        if value is None:
            return {"type": "null"}
        elif isinstance(value, bool):
            return {"type": "boolean", "value": value}
        elif isinstance(value, (int, float)):
            if isinstance(value, float):
                if math.isnan(value):
                    return {"type": "number", "value": "NaN"}
                elif math.isinf(value):
                    if value > 0:
                        return {"type": "number", "value": "Infinity"}
                    else:
                        return {"type": "number", "value": "-Infinity"}
                elif value == 0.0 and math.copysign(1.0, value) < 0:
                    return {"type": "number", "value": "-0"}

            JS_MAX_SAFE_INTEGER = 9007199254740991
            if isinstance(value, int) and (value > JS_MAX_SAFE_INTEGER or value < -JS_MAX_SAFE_INTEGER):
                return {"type": "bigint", "value": str(value)}

            return {"type": "number", "value": value}

        elif isinstance(value, str):
            return {"type": "string", "value": value}
        elif isinstance(value, datetime.datetime):
            # Convert Python datetime to JavaScript Date (ISO 8601 format)
            return {"type": "date", "value": value.isoformat() + "Z" if value.tzinfo is None else value.isoformat()}
        elif isinstance(value, datetime.date):
            # Convert Python date to JavaScript Date
            dt = datetime.datetime.combine(value, datetime.time.min).replace(tzinfo=datetime.timezone.utc)
            return {"type": "date", "value": dt.isoformat()}
        elif isinstance(value, set):
            return {"type": "set", "value": [self.__convert_to_local_value(item) for item in value]}
        elif isinstance(value, (list, tuple)):
            return {"type": "array", "value": [self.__convert_to_local_value(item) for item in value]}
        elif isinstance(value, dict):
            return {
                "type": "object",
                "value": [
                    [self.__convert_to_local_value(k), self.__convert_to_local_value(v)] for k, v in value.items()
                ],
            }
        else:
            # For other types, convert to string
            return {"type": "string", "value": str(value)}

    # low-level APIs for script module
    def _add_preload_script(
        self,
        function_declaration: str,
        arguments: list[dict[str, Any]] | None = None,
        contexts: list[str] | None = None,
        user_contexts: list[str] | None = None,
        sandbox: str | None = None,
    ) -> str:
        """Adds a preload script.

        Args:
            function_declaration: The function declaration to preload.
            arguments: The arguments to pass to the function.
            contexts: The browsing context IDs to apply the script to.
            user_contexts: The user context IDs to apply the script to.
            sandbox: The sandbox name to apply the script to.

        Returns:
            str: The preload script ID.

        Raises:
            ValueError: If both contexts and user_contexts are provided.
        """
        if contexts is not None and user_contexts is not None:
            raise ValueError("Cannot specify both contexts and user_contexts")

        params: dict[str, Any] = {"functionDeclaration": function_declaration}

        if arguments is not None:
            params["arguments"] = arguments
        if contexts is not None:
            params["contexts"] = contexts
        if user_contexts is not None:
            params["userContexts"] = user_contexts
        if sandbox is not None:
            params["sandbox"] = sandbox

        result = self.conn.execute(command_builder("script.addPreloadScript", params))
        return result["script"]

    def _remove_preload_script(self, script_id: str) -> None:
        """Removes a preload script.

        Args:
            script_id: The preload script ID to remove.
        """
        params = {"script": script_id}
        self.conn.execute(command_builder("script.removePreloadScript", params))

    def _disown(self, handles: list[str], target: dict) -> None:
        """Disowns the given handles.

        Args:
            handles: The handles to disown.
            target: The target realm or context.
        """
        params = {
            "handles": handles,
            "target": target,
        }
        self.conn.execute(command_builder("script.disown", params))

    def _call_function(
        self,
        function_declaration: str,
        await_promise: bool,
        target: dict,
        arguments: list[dict] | None = None,
        result_ownership: str | None = None,
        serialization_options: dict | None = None,
        this: dict | None = None,
        user_activation: bool = False,
    ) -> EvaluateResult:
        """Calls a provided function with given arguments in a given realm.

        Args:
            function_declaration: The function declaration to call.
            await_promise: Whether to await promise resolution.
            target: The target realm or context.
            arguments: The arguments to pass to the function.
            result_ownership: The result ownership type.
            serialization_options: The serialization options.
            this: The 'this' value for the function call.
            user_activation: Whether to trigger user activation.

        Returns:
            EvaluateResult: The result of the function call.
        """
        params = {
            "functionDeclaration": function_declaration,
            "awaitPromise": await_promise,
            "target": target,
            "userActivation": user_activation,
        }

        if arguments is not None:
            params["arguments"] = arguments
        if result_ownership is not None:
            params["resultOwnership"] = result_ownership
        if serialization_options is not None:
            params["serializationOptions"] = serialization_options
        if this is not None:
            params["this"] = this

        result = self.conn.execute(command_builder("script.callFunction", params))
        return EvaluateResult.from_json(result)

    def _evaluate(
        self,
        expression: str,
        target: dict,
        await_promise: bool,
        result_ownership: str | None = None,
        serialization_options: dict | None = None,
        user_activation: bool = False,
    ) -> EvaluateResult:
        """Evaluates a provided script in a given realm.

        Args:
            expression: The script expression to evaluate.
            target: The target realm or context.
            await_promise: Whether to await promise resolution.
            result_ownership: The result ownership type.
            serialization_options: The serialization options.
            user_activation: Whether to trigger user activation.

        Returns:
            EvaluateResult: The result of the script evaluation.
        """
        params = {
            "expression": expression,
            "target": target,
            "awaitPromise": await_promise,
            "userActivation": user_activation,
        }

        if result_ownership is not None:
            params["resultOwnership"] = result_ownership
        if serialization_options is not None:
            params["serializationOptions"] = serialization_options

        result = self.conn.execute(command_builder("script.evaluate", params))
        return EvaluateResult.from_json(result)

    def _get_realms(
        self,
        context: str | None = None,
        type: str | None = None,
    ) -> list[RealmInfo]:
        """Returns a list of all realms, optionally filtered.

        Args:
            context: The browsing context ID to filter by.
            type: The realm type to filter by.

        Returns:
            List[RealmInfo]: A list of realm information.
        """
        params = {}

        if context is not None:
            params["context"] = context
        if type is not None:
            params["type"] = type

        result = self.conn.execute(command_builder("script.getRealms", params))
        return [RealmInfo.from_json(realm) for realm in result["realms"]]

    def _subscribe_to_log_entries(self):
        if not self.log_entry_subscribed:
            session = Session(self.conn)
            self.conn.execute(session.subscribe(LogEntryAdded.event_class))
            self.log_entry_subscribed = True

    def _unsubscribe_from_log_entries(self):
        if self.log_entry_subscribed and LogEntryAdded.event_class not in self.conn.callbacks:
            session = Session(self.conn)
            self.conn.execute(session.unsubscribe(LogEntryAdded.event_class))
            self.log_entry_subscribed = False

    def _handle_log_entry(self, type, handler):
        def _handle_log_entry(log_entry):
            if log_entry.type_ == type:
                handler(log_entry)

        return _handle_log_entry
