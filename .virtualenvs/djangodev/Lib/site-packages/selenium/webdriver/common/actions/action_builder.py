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

from typing import List
from typing import Optional
from typing import Union

from selenium.webdriver.remote.command import Command

from . import interaction
from .key_actions import KeyActions
from .key_input import KeyInput
from .pointer_actions import PointerActions
from .pointer_input import PointerInput
from .wheel_actions import WheelActions
from .wheel_input import WheelInput


class ActionBuilder:
    def __init__(
        self,
        driver,
        mouse: Optional[PointerInput] = None,
        wheel: Optional[WheelInput] = None,
        keyboard: Optional[KeyInput] = None,
        duration: int = 250,
    ) -> None:
        mouse = mouse or PointerInput(interaction.POINTER_MOUSE, "mouse")
        keyboard = keyboard or KeyInput(interaction.KEY)
        wheel = wheel or WheelInput(interaction.WHEEL)
        self.devices = [mouse, keyboard, wheel]
        self._key_action = KeyActions(keyboard)
        self._pointer_action = PointerActions(mouse, duration=duration)
        self._wheel_action = WheelActions(wheel)
        self.driver = driver

    def get_device_with(self, name: str) -> Optional[Union["WheelInput", "PointerInput", "KeyInput"]]:
        return next(filter(lambda x: x == name, self.devices), None)

    @property
    def pointer_inputs(self) -> List[PointerInput]:
        return [device for device in self.devices if device.type == interaction.POINTER]

    @property
    def key_inputs(self) -> List[KeyInput]:
        return [device for device in self.devices if device.type == interaction.KEY]

    @property
    def key_action(self) -> KeyActions:
        return self._key_action

    @property
    def pointer_action(self) -> PointerActions:
        return self._pointer_action

    @property
    def wheel_action(self) -> WheelActions:
        return self._wheel_action

    def add_key_input(self, name: str) -> KeyInput:
        new_input = KeyInput(name)
        self._add_input(new_input)
        return new_input

    def add_pointer_input(self, kind: str, name: str) -> PointerInput:
        new_input = PointerInput(kind, name)
        self._add_input(new_input)
        return new_input

    def add_wheel_input(self, name: str) -> WheelInput:
        new_input = WheelInput(name)
        self._add_input(new_input)
        return new_input

    def perform(self) -> None:
        enc = {"actions": []}
        for device in self.devices:
            encoded = device.encode()
            if encoded["actions"]:
                enc["actions"].append(encoded)
                device.actions = []
        self.driver.execute(Command.W3C_ACTIONS, enc)

    def clear_actions(self) -> None:
        """Clears actions that are already stored on the remote end."""
        self.driver.execute(Command.W3C_CLEAR_ACTIONS)

    def _add_input(self, new_input: Union[KeyInput, PointerInput, WheelInput]) -> None:
        self.devices.append(new_input)
