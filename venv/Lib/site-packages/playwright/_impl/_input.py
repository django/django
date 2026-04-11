# Copyright (c) Microsoft Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from playwright._impl._connection import Channel
from playwright._impl._helper import MouseButton, locals_to_params


class Keyboard:
    def __init__(self, channel: Channel) -> None:
        self._channel = channel
        self._loop = channel._connection._loop
        self._dispatcher_fiber = channel._connection._dispatcher_fiber

    async def down(self, key: str) -> None:
        await self._channel.send("keyboardDown", None, locals_to_params(locals()))

    async def up(self, key: str) -> None:
        await self._channel.send("keyboardUp", None, locals_to_params(locals()))

    async def insert_text(self, text: str) -> None:
        await self._channel.send("keyboardInsertText", None, locals_to_params(locals()))

    async def type(self, text: str, delay: float = None) -> None:
        await self._channel.send("keyboardType", None, locals_to_params(locals()))

    async def press(self, key: str, delay: float = None) -> None:
        await self._channel.send("keyboardPress", None, locals_to_params(locals()))


class Mouse:
    def __init__(self, channel: Channel) -> None:
        self._channel = channel
        self._loop = channel._connection._loop
        self._dispatcher_fiber = channel._connection._dispatcher_fiber

    async def move(self, x: float, y: float, steps: int = None) -> None:
        await self._channel.send("mouseMove", None, locals_to_params(locals()))

    async def down(
        self,
        button: MouseButton = None,
        clickCount: int = None,
    ) -> None:
        await self._channel.send("mouseDown", None, locals_to_params(locals()))

    async def up(
        self,
        button: MouseButton = None,
        clickCount: int = None,
    ) -> None:
        await self._channel.send("mouseUp", None, locals_to_params(locals()))

    async def _click(
        self,
        x: float,
        y: float,
        delay: float = None,
        button: MouseButton = None,
        clickCount: int = None,
        title: str = None,
    ) -> None:
        await self._channel.send(
            "mouseClick", None, locals_to_params(locals()), title=title
        )

    async def click(
        self,
        x: float,
        y: float,
        delay: float = None,
        button: MouseButton = None,
        clickCount: int = None,
    ) -> None:
        params = locals()
        del params["self"]
        await self._click(**params)

    async def dblclick(
        self,
        x: float,
        y: float,
        delay: float = None,
        button: MouseButton = None,
    ) -> None:
        await self._click(
            x, y, delay=delay, button=button, clickCount=2, title="Double click"
        )

    async def wheel(self, deltaX: float, deltaY: float) -> None:
        await self._channel.send("mouseWheel", None, locals_to_params(locals()))


class Touchscreen:
    def __init__(self, channel: Channel) -> None:
        self._channel = channel
        self._loop = channel._connection._loop
        self._dispatcher_fiber = channel._connection._dispatcher_fiber

    async def tap(self, x: float, y: float) -> None:
        await self._channel.send("touchscreenTap", None, locals_to_params(locals()))
