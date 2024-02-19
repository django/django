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
"""The ActionChains implementation."""
from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Union

from selenium.webdriver.remote.webelement import WebElement

from .actions.action_builder import ActionBuilder
from .actions.key_input import KeyInput
from .actions.pointer_input import PointerInput
from .actions.wheel_input import ScrollOrigin
from .actions.wheel_input import WheelInput
from .utils import keys_to_typing

if TYPE_CHECKING:
    from selenium.webdriver.remote.webdriver import WebDriver

AnyDevice = Union[PointerInput, KeyInput, WheelInput]


class ActionChains:
    """ActionChains are a way to automate low level interactions such as mouse
    movements, mouse button actions, key press, and context menu interactions.
    This is useful for doing more complex actions like hover over and drag and
    drop.

    Generate user actions.
       When you call methods for actions on the ActionChains object,
       the actions are stored in a queue in the ActionChains object.
       When you call perform(), the events are fired in the order they
       are queued up.

    ActionChains can be used in a chain pattern::

        menu = driver.find_element(By.CSS_SELECTOR, ".nav")
        hidden_submenu = driver.find_element(By.CSS_SELECTOR, ".nav #submenu1")

        ActionChains(driver).move_to_element(menu).click(hidden_submenu).perform()

    Or actions can be queued up one by one, then performed.::

        menu = driver.find_element(By.CSS_SELECTOR, ".nav")
        hidden_submenu = driver.find_element(By.CSS_SELECTOR, ".nav #submenu1")

        actions = ActionChains(driver)
        actions.move_to_element(menu)
        actions.click(hidden_submenu)
        actions.perform()

    Either way, the actions are performed in the order they are called, one after
    another.
    """

    def __init__(self, driver: WebDriver, duration: int = 250, devices: list[AnyDevice] | None = None) -> None:
        """Creates a new ActionChains.

        :Args:
         - driver: The WebDriver instance which performs user actions.
         - duration: override the default 250 msecs of DEFAULT_MOVE_DURATION in PointerInput
        """
        self._driver = driver
        mouse = None
        keyboard = None
        wheel = None
        if devices is not None and isinstance(devices, list):
            for device in devices:
                if isinstance(device, PointerInput):
                    mouse = device
                if isinstance(device, KeyInput):
                    keyboard = device
                if isinstance(device, WheelInput):
                    wheel = device
        self.w3c_actions = ActionBuilder(driver, mouse=mouse, keyboard=keyboard, wheel=wheel, duration=duration)

    def perform(self) -> None:
        """Performs all stored actions."""
        self.w3c_actions.perform()

    def reset_actions(self) -> None:
        """Clears actions that are already stored locally and on the remote
        end."""
        self.w3c_actions.clear_actions()
        for device in self.w3c_actions.devices:
            device.clear_actions()

    def click(self, on_element: WebElement | None = None) -> ActionChains:
        """Clicks an element.

        :Args:
         - on_element: The element to click.
           If None, clicks on current mouse position.
        """
        if on_element:
            self.move_to_element(on_element)

        self.w3c_actions.pointer_action.click()
        self.w3c_actions.key_action.pause()
        self.w3c_actions.key_action.pause()

        return self

    def click_and_hold(self, on_element: WebElement | None = None) -> ActionChains:
        """Holds down the left mouse button on an element.

        :Args:
         - on_element: The element to mouse down.
           If None, clicks on current mouse position.
        """
        if on_element:
            self.move_to_element(on_element)

        self.w3c_actions.pointer_action.click_and_hold()
        self.w3c_actions.key_action.pause()

        return self

    def context_click(self, on_element: WebElement | None = None) -> ActionChains:
        """Performs a context-click (right click) on an element.

        :Args:
         - on_element: The element to context-click.
           If None, clicks on current mouse position.
        """
        if on_element:
            self.move_to_element(on_element)

        self.w3c_actions.pointer_action.context_click()
        self.w3c_actions.key_action.pause()
        self.w3c_actions.key_action.pause()

        return self

    def double_click(self, on_element: WebElement | None = None) -> ActionChains:
        """Double-clicks an element.

        :Args:
         - on_element: The element to double-click.
           If None, clicks on current mouse position.
        """
        if on_element:
            self.move_to_element(on_element)

        self.w3c_actions.pointer_action.double_click()
        for _ in range(4):
            self.w3c_actions.key_action.pause()

        return self

    def drag_and_drop(self, source: WebElement, target: WebElement) -> ActionChains:
        """Holds down the left mouse button on the source element, then moves
        to the target element and releases the mouse button.

        :Args:
         - source: The element to mouse down.
         - target: The element to mouse up.
        """
        self.click_and_hold(source)
        self.release(target)
        return self

    def drag_and_drop_by_offset(self, source: WebElement, xoffset: int, yoffset: int) -> ActionChains:
        """Holds down the left mouse button on the source element, then moves
        to the target offset and releases the mouse button.

        :Args:
         - source: The element to mouse down.
         - xoffset: X offset to move to.
         - yoffset: Y offset to move to.
        """
        self.click_and_hold(source)
        self.move_by_offset(xoffset, yoffset)
        self.release()
        return self

    def key_down(self, value: str, element: WebElement | None = None) -> ActionChains:
        """Sends a key press only, without releasing it. Should only be used
        with modifier keys (Control, Alt and Shift).

        :Args:
         - value: The modifier key to send. Values are defined in `Keys` class.
         - element: The element to send keys.
           If None, sends a key to current focused element.

        Example, pressing ctrl+c::

            ActionChains(driver).key_down(Keys.CONTROL).send_keys('c').key_up(Keys.CONTROL).perform()
        """
        if element:
            self.click(element)

        self.w3c_actions.key_action.key_down(value)
        self.w3c_actions.pointer_action.pause()

        return self

    def key_up(self, value: str, element: WebElement | None = None) -> ActionChains:
        """Releases a modifier key.

        :Args:
         - value: The modifier key to send. Values are defined in Keys class.
         - element: The element to send keys.
           If None, sends a key to current focused element.

        Example, pressing ctrl+c::

            ActionChains(driver).key_down(Keys.CONTROL).send_keys('c').key_up(Keys.CONTROL).perform()
        """
        if element:
            self.click(element)

        self.w3c_actions.key_action.key_up(value)
        self.w3c_actions.pointer_action.pause()

        return self

    def move_by_offset(self, xoffset: int, yoffset: int) -> ActionChains:
        """Moving the mouse to an offset from current mouse position.

        :Args:
         - xoffset: X offset to move to, as a positive or negative integer.
         - yoffset: Y offset to move to, as a positive or negative integer.
        """

        self.w3c_actions.pointer_action.move_by(xoffset, yoffset)
        self.w3c_actions.key_action.pause()

        return self

    def move_to_element(self, to_element: WebElement) -> ActionChains:
        """Moving the mouse to the middle of an element.

        :Args:
         - to_element: The WebElement to move to.
        """

        self.w3c_actions.pointer_action.move_to(to_element)
        self.w3c_actions.key_action.pause()

        return self

    def move_to_element_with_offset(self, to_element: WebElement, xoffset: int, yoffset: int) -> ActionChains:
        """Move the mouse by an offset of the specified element. Offsets are
        relative to the in-view center point of the element.

        :Args:
         - to_element: The WebElement to move to.
         - xoffset: X offset to move to, as a positive or negative integer.
         - yoffset: Y offset to move to, as a positive or negative integer.
        """

        self.w3c_actions.pointer_action.move_to(to_element, int(xoffset), int(yoffset))
        self.w3c_actions.key_action.pause()

        return self

    def pause(self, seconds: float | int) -> ActionChains:
        """Pause all inputs for the specified duration in seconds."""

        self.w3c_actions.pointer_action.pause(seconds)
        self.w3c_actions.key_action.pause(seconds)

        return self

    def release(self, on_element: WebElement | None = None) -> ActionChains:
        """Releasing a held mouse button on an element.

        :Args:
         - on_element: The element to mouse up.
           If None, releases on current mouse position.
        """
        if on_element:
            self.move_to_element(on_element)

        self.w3c_actions.pointer_action.release()
        self.w3c_actions.key_action.pause()

        return self

    def send_keys(self, *keys_to_send: str) -> ActionChains:
        """Sends keys to current focused element.

        :Args:
         - keys_to_send: The keys to send.  Modifier keys constants can be found in the
           'Keys' class.
        """
        typing = keys_to_typing(keys_to_send)

        for key in typing:
            self.key_down(key)
            self.key_up(key)

        return self

    def send_keys_to_element(self, element: WebElement, *keys_to_send: str) -> ActionChains:
        """Sends keys to an element.

        :Args:
         - element: The element to send keys.
         - keys_to_send: The keys to send.  Modifier keys constants can be found in the
           'Keys' class.
        """
        self.click(element)
        self.send_keys(*keys_to_send)
        return self

    def scroll_to_element(self, element: WebElement) -> ActionChains:
        """If the element is outside the viewport, scrolls the bottom of the
        element to the bottom of the viewport.

        :Args:
         - element: Which element to scroll into the viewport.
        """

        self.w3c_actions.wheel_action.scroll(origin=element)
        return self

    def scroll_by_amount(self, delta_x: int, delta_y: int) -> ActionChains:
        """Scrolls by provided amounts with the origin in the top left corner
        of the viewport.

        :Args:
         - delta_x: Distance along X axis to scroll using the wheel. A negative value scrolls left.
         - delta_y: Distance along Y axis to scroll using the wheel. A negative value scrolls up.
        """

        self.w3c_actions.wheel_action.scroll(delta_x=delta_x, delta_y=delta_y)
        return self

    def scroll_from_origin(self, scroll_origin: ScrollOrigin, delta_x: int, delta_y: int) -> ActionChains:
        """Scrolls by provided amount based on a provided origin. The scroll
        origin is either the center of an element or the upper left of the
        viewport plus any offsets. If the origin is an element, and the element
        is not in the viewport, the bottom of the element will first be
        scrolled to the bottom of the viewport.

        :Args:
         - origin: Where scroll originates (viewport or element center) plus provided offsets.
         - delta_x: Distance along X axis to scroll using the wheel. A negative value scrolls left.
         - delta_y: Distance along Y axis to scroll using the wheel. A negative value scrolls up.

         :Raises: If the origin with offset is outside the viewport.
          - MoveTargetOutOfBoundsException - If the origin with offset is outside the viewport.
        """

        if not isinstance(scroll_origin, ScrollOrigin):
            raise TypeError(f"Expected object of type ScrollOrigin, got: {type(scroll_origin)}")

        self.w3c_actions.wheel_action.scroll(
            origin=scroll_origin.origin,
            x=scroll_origin.x_offset,
            y=scroll_origin.y_offset,
            delta_x=delta_x,
            delta_y=delta_y,
        )
        return self

    # Context manager so ActionChains can be used in a 'with .. as' statements.

    def __enter__(self) -> ActionChains:
        return self  # Return created instance of self.

    def __exit__(self, _type, _value, _traceback) -> None:
        pass  # Do nothing, does not require additional cleanup.
