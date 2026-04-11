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


from typing import Any, Union

from selenium.webdriver.common.actions import interaction
from selenium.webdriver.common.actions.key_actions import KeyActions
from selenium.webdriver.common.actions.key_input import KeyInput
from selenium.webdriver.common.actions.pointer_actions import PointerActions
from selenium.webdriver.common.actions.pointer_input import PointerInput
from selenium.webdriver.common.actions.wheel_actions import WheelActions
from selenium.webdriver.common.actions.wheel_input import WheelInput
from selenium.webdriver.remote.command import Command


class ActionBuilder:
    def __init__(
        self,
        driver,
        mouse: PointerInput | None = None,
        wheel: WheelInput | None = None,
        keyboard: KeyInput | None = None,
        duration: int = 250,
    ) -> None:
        mouse = mouse or PointerInput(interaction.POINTER_MOUSE, "mouse")
        keyboard = keyboard or KeyInput(interaction.KEY)
        wheel = wheel or WheelInput(interaction.WHEEL)
        self.devices: list[PointerInput | KeyInput | WheelInput] = [mouse, keyboard, wheel]
        self._key_action = KeyActions(keyboard)
        self._pointer_action = PointerActions(mouse, duration=duration)
        self._wheel_action = WheelActions(wheel)
        self.driver = driver

    def get_device_with(self, name: str) -> Union["WheelInput", "PointerInput", "KeyInput"] | None:
        """Get the device with the given name.

        Args:
            name: The name of the device to get.

        Returns:
            The device with the given name, or None if not found.
        """
        return next(filter(lambda x: x == name, self.devices), None)

    @property
    def pointer_inputs(self) -> list[PointerInput]:
        return [device for device in self.devices if isinstance(device, PointerInput)]

    @property
    def key_inputs(self) -> list[KeyInput]:
        return [device for device in self.devices if isinstance(device, KeyInput)]

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
        """Add a new key input device to the action builder.

        Args:
            name: The name of the key input device.

        Returns:
            The newly created key input device.

        Example:
            >>> action_builder = ActionBuilder(driver)
            >>> action_builder.add_key_input(name="keyboard2")
        """
        new_input = KeyInput(name)
        self._add_input(new_input)
        return new_input

    def add_pointer_input(self, kind: str, name: str) -> PointerInput:
        """Add a new pointer input device to the action builder.

        Args:
            kind: The kind of pointer input device. Valid values are "mouse",
                "touch", or "pen".
            name: The name of the pointer input device.

        Returns:
            The newly created pointer input device.

        Example:
            >>> action_builder = ActionBuilder(driver)
            >>> action_builder.add_pointer_input(kind="mouse", name="mouse")
        """
        new_input = PointerInput(kind, name)
        self._add_input(new_input)
        return new_input

    def add_wheel_input(self, name: str) -> WheelInput:
        """Add a new wheel input device to the action builder.

        Args:
            name: The name of the wheel input device.

        Returns:
            The newly created wheel input device.

        Example:
            >>> action_builder = ActionBuilder(driver)
            >>> action_builder.add_wheel_input(name="wheel2")
        """
        new_input = WheelInput(name)
        self._add_input(new_input)
        return new_input

    def perform(self) -> None:
        """Performs all stored actions.

        Example:
            >>> action_builder = ActionBuilder(driver)
            >>> keyboard = action_builder.key_input
            >>> el = driver.find_element(id: "some_id")
            >>> action_builder.click(el).pause(keyboard).pause(keyboard).pause(keyboard).send_keys("keys").perform()
        """
        enc: dict[str, list[Any]] = {"actions": []}
        for device in self.devices:
            encoded = device.encode()
            if encoded["actions"]:
                enc["actions"].append(encoded)
                device.actions = []
        self.driver.execute(Command.W3C_ACTIONS, enc)

    def clear_actions(self) -> None:
        """Clears actions that are already stored on the remote end.

        Example:
            >>> action_builder = ActionBuilder(driver)
            >>> keyboard = action_builder.key_input
            >>> el = driver.find_element(By.ID, "some_id")
            >>> action_builder.click(el).pause(keyboard).pause(keyboard).pause(keyboard).send_keys("keys")
            >>> action_builder.clear_actions()
        """
        self.driver.execute(Command.W3C_CLEAR_ACTIONS)

    def _add_input(self, new_input: KeyInput | PointerInput | WheelInput) -> None:
        """Add a new input device to the action builder.

        Args:
            new_input: The new input device to add.
        """
        self.devices.append(new_input)
