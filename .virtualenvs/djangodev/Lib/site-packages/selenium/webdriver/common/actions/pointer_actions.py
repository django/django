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
from typing import Optional

from selenium.webdriver.remote.webelement import WebElement

from . import interaction
from .interaction import Interaction
from .mouse_button import MouseButton
from .pointer_input import PointerInput


class PointerActions(Interaction):
    def __init__(self, source: Optional[PointerInput] = None, duration: int = 250):
        """
        Args:
        - source: PointerInput instance
        - duration: override the default 250 msecs of DEFAULT_MOVE_DURATION in source
        """
        if not source:
            source = PointerInput(interaction.POINTER_MOUSE, "mouse")
        self.source = source
        self._duration = duration
        super().__init__(source)

    def pointer_down(
        self,
        button=MouseButton.LEFT,
        width=None,
        height=None,
        pressure=None,
        tangential_pressure=None,
        tilt_x=None,
        tilt_y=None,
        twist=None,
        altitude_angle=None,
        azimuth_angle=None,
    ):
        self._button_action(
            "create_pointer_down",
            button=button,
            width=width,
            height=height,
            pressure=pressure,
            tangential_pressure=tangential_pressure,
            tilt_x=tilt_x,
            tilt_y=tilt_y,
            twist=twist,
            altitude_angle=altitude_angle,
            azimuth_angle=azimuth_angle,
        )
        return self

    def pointer_up(self, button=MouseButton.LEFT):
        self._button_action("create_pointer_up", button=button)
        return self

    def move_to(
        self,
        element,
        x=0,
        y=0,
        width=None,
        height=None,
        pressure=None,
        tangential_pressure=None,
        tilt_x=None,
        tilt_y=None,
        twist=None,
        altitude_angle=None,
        azimuth_angle=None,
    ):
        if not isinstance(element, WebElement):
            raise AttributeError("move_to requires a WebElement")

        self.source.create_pointer_move(
            origin=element,
            duration=self._duration,
            x=int(x),
            y=int(y),
            width=width,
            height=height,
            pressure=pressure,
            tangential_pressure=tangential_pressure,
            tilt_x=tilt_x,
            tilt_y=tilt_y,
            twist=twist,
            altitude_angle=altitude_angle,
            azimuth_angle=azimuth_angle,
        )
        return self

    def move_by(
        self,
        x,
        y,
        width=None,
        height=None,
        pressure=None,
        tangential_pressure=None,
        tilt_x=None,
        tilt_y=None,
        twist=None,
        altitude_angle=None,
        azimuth_angle=None,
    ):
        self.source.create_pointer_move(
            origin=interaction.POINTER,
            duration=self._duration,
            x=int(x),
            y=int(y),
            width=width,
            height=height,
            pressure=pressure,
            tangential_pressure=tangential_pressure,
            tilt_x=tilt_x,
            tilt_y=tilt_y,
            twist=twist,
            altitude_angle=altitude_angle,
            azimuth_angle=azimuth_angle,
        )
        return self

    def move_to_location(
        self,
        x,
        y,
        width=None,
        height=None,
        pressure=None,
        tangential_pressure=None,
        tilt_x=None,
        tilt_y=None,
        twist=None,
        altitude_angle=None,
        azimuth_angle=None,
    ):
        self.source.create_pointer_move(
            origin="viewport",
            duration=self._duration,
            x=int(x),
            y=int(y),
            width=width,
            height=height,
            pressure=pressure,
            tangential_pressure=tangential_pressure,
            tilt_x=tilt_x,
            tilt_y=tilt_y,
            twist=twist,
            altitude_angle=altitude_angle,
            azimuth_angle=azimuth_angle,
        )
        return self

    def click(self, element: Optional[WebElement] = None, button=MouseButton.LEFT):
        if element:
            self.move_to(element)
        self.pointer_down(button)
        self.pointer_up(button)
        return self

    def context_click(self, element: Optional[WebElement] = None):
        return self.click(element=element, button=MouseButton.RIGHT)

    def click_and_hold(self, element: Optional[WebElement] = None, button=MouseButton.LEFT):
        if element:
            self.move_to(element)
        self.pointer_down(button=button)
        return self

    def release(self, button=MouseButton.LEFT):
        self.pointer_up(button=button)
        return self

    def double_click(self, element: Optional[WebElement] = None):
        if element:
            self.move_to(element)
        self.pointer_down(MouseButton.LEFT)
        self.pointer_up(MouseButton.LEFT)
        self.pointer_down(MouseButton.LEFT)
        self.pointer_up(MouseButton.LEFT)
        return self

    def pause(self, duration: float = 0):
        self.source.create_pause(duration)
        return self

    def _button_action(self, action, **kwargs):
        meth = getattr(self.source, action)
        meth(**kwargs)
        return self
