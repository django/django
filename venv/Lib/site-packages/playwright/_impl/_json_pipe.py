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

import asyncio
from typing import Dict, Optional, cast

from pyee.asyncio import AsyncIOEventEmitter

from playwright._impl._connection import Channel
from playwright._impl._errors import TargetClosedError
from playwright._impl._helper import Error, ParsedMessagePayload
from playwright._impl._transport import Transport


class JsonPipeTransport(AsyncIOEventEmitter, Transport):
    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        pipe_channel: Channel,
    ) -> None:
        super().__init__(loop)
        Transport.__init__(self, loop)
        self._stop_requested = False
        self._pipe_channel = pipe_channel

    def request_stop(self) -> None:
        self._stop_requested = True
        self._pipe_channel.send_no_reply("close", None, {})

    def dispose(self) -> None:
        self.on_error_future.cancel()
        self._stopped_future.cancel()

    async def wait_until_stopped(self) -> None:
        await self._stopped_future

    async def connect(self) -> None:
        self._stopped_future: asyncio.Future = asyncio.Future()

        def handle_message(message: Dict) -> None:
            if self._stop_requested:
                return
            self.on_message(cast(ParsedMessagePayload, message))

        def handle_closed(reason: Optional[str]) -> None:
            self.emit("close", reason)
            if reason:
                self.on_error_future.set_exception(TargetClosedError(reason))
            self._stopped_future.set_result(None)

        self._pipe_channel.on(
            "message",
            lambda params: handle_message(params["message"]),
        )
        self._pipe_channel.on(
            "closed",
            lambda params: handle_closed(params.get("reason")),
        )

    async def run(self) -> None:
        await self._stopped_future

    def send(self, message: Dict) -> None:
        if self._stop_requested:
            raise Error("Playwright connection closed")
        self._pipe_channel.send_no_reply("send", None, {"message": message})
