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

import pathlib
from pathlib import Path
from typing import Dict, Optional, Union, cast

from playwright._impl._connection import ChannelOwner, from_channel
from playwright._impl._helper import Error, make_dirs_for_file, patch_error_message
from playwright._impl._stream import Stream


class Artifact(ChannelOwner):
    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self.absolute_path = initializer["absolutePath"]

    async def path_after_finished(self) -> pathlib.Path:
        if self._connection.is_remote:
            raise Error(
                "Path is not available when using browser_type.connect(). Use save_as() to save a local copy."
            )
        path = await self._channel.send(
            "pathAfterFinished",
            None,
        )
        return pathlib.Path(path)

    async def save_as(self, path: Union[str, Path]) -> None:
        stream = cast(
            Stream,
            from_channel(
                await self._channel.send(
                    "saveAsStream",
                    None,
                )
            ),
        )
        make_dirs_for_file(path)
        await stream.save_as(path)

    async def failure(self) -> Optional[str]:
        reason = await self._channel.send(
            "failure",
            None,
        )
        if reason is None:
            return None
        return patch_error_message(reason)

    async def delete(self) -> None:
        await self._channel.send(
            "delete",
            None,
        )

    async def read_info_buffer(self) -> bytes:
        stream = cast(
            Stream,
            from_channel(
                await self._channel.send(
                    "stream",
                    None,
                )
            ),
        )
        buffer = await stream.read_all()
        return buffer

    async def cancel(self) -> None:  # pyright: ignore[reportIncompatibleMethodOverride]
        await self._channel.send(
            "cancel",
            None,
        )
