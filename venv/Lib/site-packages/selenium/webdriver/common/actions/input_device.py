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

import uuid
from typing import Any


class InputDevice:
    """Describes the input device being used for the action."""

    def __init__(self, name: str | None = None):
        self.name = name or uuid.uuid4()
        self.actions: list[Any] = []

    def add_action(self, action: Any) -> None:
        self.actions.append(action)

    def clear_actions(self) -> None:
        self.actions = []

    def create_pause(self, duration: float = 0) -> None:
        pass
