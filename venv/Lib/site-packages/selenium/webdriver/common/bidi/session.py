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


from selenium.webdriver.common.bidi.common import command_builder


class UserPromptHandlerType:
    """Represents the behavior of the user prompt handler."""

    ACCEPT = "accept"
    DISMISS = "dismiss"
    IGNORE = "ignore"

    VALID_TYPES = {ACCEPT, DISMISS, IGNORE}


class UserPromptHandler:
    """Represents the configuration of the user prompt handler."""

    def __init__(
        self,
        alert: str | None = None,
        before_unload: str | None = None,
        confirm: str | None = None,
        default: str | None = None,
        file: str | None = None,
        prompt: str | None = None,
    ):
        """Initialize UserPromptHandler.

        Args:
            alert: Handler type for alert prompts.
            before_unload: Handler type for beforeUnload prompts.
            confirm: Handler type for confirm prompts.
            default: Default handler type for all prompts.
            file: Handler type for file picker prompts.
            prompt: Handler type for prompt dialogs.

        Raises:
            ValueError: If any handler type is not valid.
        """
        for field_name, value in [
            ("alert", alert),
            ("before_unload", before_unload),
            ("confirm", confirm),
            ("default", default),
            ("file", file),
            ("prompt", prompt),
        ]:
            if value is not None and value not in UserPromptHandlerType.VALID_TYPES:
                raise ValueError(
                    f"Invalid {field_name} handler type: {value}. Must be one of {UserPromptHandlerType.VALID_TYPES}"
                )

        self.alert = alert
        self.before_unload = before_unload
        self.confirm = confirm
        self.default = default
        self.file = file
        self.prompt = prompt

    def to_dict(self) -> dict[str, str]:
        """Convert the UserPromptHandler to a dictionary for BiDi protocol.

        Returns:
            Dictionary representation suitable for BiDi protocol.
        """
        field_mapping = {
            "alert": "alert",
            "before_unload": "beforeUnload",
            "confirm": "confirm",
            "default": "default",
            "file": "file",
            "prompt": "prompt",
        }

        result = {}
        for attr_name, dict_key in field_mapping.items():
            value = getattr(self, attr_name)
            if value is not None:
                result[dict_key] = value
        return result


class Session:
    def __init__(self, conn):
        self.conn = conn

    def subscribe(self, *events, browsing_contexts=None):
        params = {
            "events": events,
        }
        if browsing_contexts is None:
            browsing_contexts = []
        if browsing_contexts:
            params["browsingContexts"] = browsing_contexts
        return command_builder("session.subscribe", params)

    def unsubscribe(self, *events, browsing_contexts=None):
        params = {
            "events": events,
        }
        if browsing_contexts is None:
            browsing_contexts = []
        if browsing_contexts:
            params["browsingContexts"] = browsing_contexts
        return command_builder("session.unsubscribe", params)

    def status(self):
        """The session.status command returns information about the remote end's readiness.

        Returns information about the remote end's readiness to create new sessions
        and may include implementation-specific metadata.

        Returns:
            Dictionary containing the ready state (bool), message (str) and metadata.
        """
        cmd = command_builder("session.status", {})
        return self.conn.execute(cmd)
