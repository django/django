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

import base64
from pathlib import Path
from typing import Dict, Union

from playwright._impl._connection import ChannelOwner


class Stream(ChannelOwner):
    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)

    async def save_as(self, path: Union[str, Path]) -> None:
        file = await self._loop.run_in_executor(None, lambda: open(path, "wb"))
        while True:
            binary = await self._channel.send("read", None, {"size": 1024 * 1024})
            if not binary:
                break
            await self._loop.run_in_executor(
                None, lambda: file.write(base64.b64decode(binary))
            )
        await self._loop.run_in_executor(None, lambda: file.close())

    async def read_all(self) -> bytes:
        binary = b""
        while True:
            chunk = await self._channel.send("read", None, {"size": 1024 * 1024})
            if not chunk:
                break
            binary += base64.b64decode(chunk)
        return binary
