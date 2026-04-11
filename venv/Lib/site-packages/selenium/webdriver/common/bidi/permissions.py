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


class PermissionState:
    """Represents the possible permission states."""

    GRANTED = "granted"
    DENIED = "denied"
    PROMPT = "prompt"


class PermissionDescriptor:
    """Represents a permission descriptor."""

    def __init__(self, name: str):
        self.name = name

    def to_dict(self) -> dict:
        return {"name": self.name}


class Permissions:
    """BiDi implementation of the permissions module."""

    def __init__(self, conn):
        self.conn = conn

    def set_permission(
        self,
        descriptor: str | PermissionDescriptor,
        state: str,
        origin: str,
        user_context: str | None = None,
    ) -> None:
        """Sets a permission state for a given permission descriptor.

        Args:
            descriptor: The permission name (str) or PermissionDescriptor object.
              Examples: "geolocation", "camera", "microphone".
            state: The permission state (granted, denied, prompt).
            origin: The origin for which the permission is set.
            user_context: The user context id (optional).

        Raises:
            ValueError: If the permission state is invalid.
        """
        if state not in [PermissionState.GRANTED, PermissionState.DENIED, PermissionState.PROMPT]:
            valid_states = f"{PermissionState.GRANTED}, {PermissionState.DENIED}, {PermissionState.PROMPT}"
            raise ValueError(f"Invalid permission state. Must be one of: {valid_states}")

        if isinstance(descriptor, str):
            permission_descriptor = PermissionDescriptor(descriptor)
        else:
            permission_descriptor = descriptor

        params = {
            "descriptor": permission_descriptor.to_dict(),
            "state": state,
            "origin": origin,
        }

        if user_context is not None:
            params["userContext"] = user_context

        self.conn.execute(command_builder("permissions.setPermission", params))
