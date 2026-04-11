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

import datetime
from typing import TYPE_CHECKING, Dict, Union

if TYPE_CHECKING:
    from playwright._impl._browser_context import BrowserContext


class Clock:
    def __init__(self, browser_context: "BrowserContext") -> None:
        self._browser_context = browser_context
        self._loop = browser_context._loop
        self._dispatcher_fiber = browser_context._dispatcher_fiber

    async def install(self, time: Union[float, str, datetime.datetime] = None) -> None:
        await self._browser_context._channel.send(
            "clockInstall",
            None,
            parse_time(time) if time is not None else {},
        )

    async def fast_forward(
        self,
        ticks: Union[int, str],
    ) -> None:
        await self._browser_context._channel.send(
            "clockFastForward",
            None,
            parse_ticks(ticks),
        )

    async def pause_at(
        self,
        time: Union[float, str, datetime.datetime],
    ) -> None:
        await self._browser_context._channel.send(
            "clockPauseAt",
            None,
            parse_time(time),
        )

    async def resume(
        self,
    ) -> None:
        await self._browser_context._channel.send("clockResume", None)

    async def run_for(
        self,
        ticks: Union[int, str],
    ) -> None:
        await self._browser_context._channel.send(
            "clockRunFor",
            None,
            parse_ticks(ticks),
        )

    async def set_fixed_time(
        self,
        time: Union[float, str, datetime.datetime],
    ) -> None:
        await self._browser_context._channel.send(
            "clockSetFixedTime",
            None,
            parse_time(time),
        )

    async def set_system_time(
        self,
        time: Union[float, str, datetime.datetime],
    ) -> None:
        await self._browser_context._channel.send(
            "clockSetSystemTime",
            None,
            parse_time(time),
        )


def parse_time(
    time: Union[float, str, datetime.datetime],
) -> Dict[str, Union[int, str]]:
    if isinstance(time, (float, int)):
        return {"timeNumber": int(time * 1_000)}
    if isinstance(time, str):
        return {"timeString": time}
    return {"timeNumber": int(time.timestamp() * 1_000)}


def parse_ticks(ticks: Union[int, str]) -> Dict[str, Union[int, str]]:
    if isinstance(ticks, int):
        return {"ticksNumber": ticks}
    return {"ticksString": ticks}
