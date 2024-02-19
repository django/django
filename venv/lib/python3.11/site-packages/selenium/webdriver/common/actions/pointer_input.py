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
import typing

from selenium.common.exceptions import InvalidArgumentException
from selenium.webdriver.remote.webelement import WebElement

from .input_device import InputDevice
from .interaction import POINTER
from .interaction import POINTER_KINDS


class PointerInput(InputDevice):
    DEFAULT_MOVE_DURATION = 250

    def __init__(self, kind, name):
        super().__init__()
        if kind not in POINTER_KINDS:
            raise InvalidArgumentException(f"Invalid PointerInput kind '{kind}'")
        self.type = POINTER
        self.kind = kind
        self.name = name

    def create_pointer_move(
        self,
        duration=DEFAULT_MOVE_DURATION,
        x: float = 0,
        y: float = 0,
        origin: typing.Optional[WebElement] = None,
        **kwargs,
    ):
        action = {"type": "pointerMove", "duration": duration, "x": x, "y": y, **kwargs}
        if isinstance(origin, WebElement):
            action["origin"] = {"element-6066-11e4-a52e-4f735466cecf": origin.id}
        elif origin is not None:
            action["origin"] = origin
        self.add_action(self._convert_keys(action))

    def create_pointer_down(self, **kwargs):
        data = {"type": "pointerDown", "duration": 0, **kwargs}
        self.add_action(self._convert_keys(data))

    def create_pointer_up(self, button):
        self.add_action({"type": "pointerUp", "duration": 0, "button": button})

    def create_pointer_cancel(self):
        self.add_action({"type": "pointerCancel"})

    def create_pause(self, pause_duration: float) -> None:
        self.add_action({"type": "pause", "duration": int(pause_duration * 1000)})

    def encode(self):
        return {"type": self.type, "parameters": {"pointerType": self.kind}, "id": self.name, "actions": self.actions}

    def _convert_keys(self, actions: typing.Dict[str, typing.Any]):
        out = {}
        for k, v in actions.items():
            if v is None:
                continue
            if k in ("x", "y"):
                out[k] = int(v)
                continue
            splits = k.split("_")
            new_key = splits[0] + "".join(v.title() for v in splits[1:])
            out[new_key] = v
        return out
