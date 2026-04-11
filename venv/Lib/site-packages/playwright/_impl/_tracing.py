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
from typing import Dict, Optional, Union, cast

from playwright._impl._api_structures import TracingGroupLocation
from playwright._impl._artifact import Artifact
from playwright._impl._connection import ChannelOwner, from_nullable_channel
from playwright._impl._helper import locals_to_params


class Tracing(ChannelOwner):
    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self._include_sources: bool = False
        self._stacks_id: Optional[str] = None
        self._is_tracing: bool = False
        self._traces_dir: Optional[str] = None

    async def start(
        self,
        name: str = None,
        title: str = None,
        snapshots: bool = None,
        screenshots: bool = None,
        sources: bool = None,
    ) -> None:
        params = locals_to_params(locals())
        self._include_sources = bool(sources)

        await self._channel.send("tracingStart", None, params)
        trace_name = await self._channel.send(
            "tracingStartChunk", None, {"title": title, "name": name}
        )
        await self._start_collecting_stacks(trace_name)

    async def start_chunk(self, title: str = None, name: str = None) -> None:
        params = locals_to_params(locals())
        trace_name = await self._channel.send("tracingStartChunk", None, params)
        await self._start_collecting_stacks(trace_name)

    async def _start_collecting_stacks(self, trace_name: str) -> None:
        if not self._is_tracing:
            self._is_tracing = True
            self._connection.set_is_tracing(True)
        self._stacks_id = await self._connection.local_utils.tracing_started(
            self._traces_dir, trace_name
        )

    async def stop_chunk(self, path: Union[pathlib.Path, str] = None) -> None:
        await self._do_stop_chunk(path)

    async def stop(self, path: Union[pathlib.Path, str] = None) -> None:
        await self._do_stop_chunk(path)
        await self._channel.send(
            "tracingStop",
            None,
        )

    async def _do_stop_chunk(self, file_path: Union[pathlib.Path, str] = None) -> None:
        self._reset_stack_counter()

        if not file_path:
            # Not interested in any artifacts
            await self._channel.send("tracingStopChunk", None, {"mode": "discard"})
            if self._stacks_id:
                await self._connection.local_utils.trace_discarded(self._stacks_id)
            return

        is_local = not self._connection.is_remote

        if is_local:
            result = await self._channel.send_return_as_dict(
                "tracingStopChunk", None, {"mode": "entries"}
            )
            await self._connection.local_utils.zip(
                {
                    "zipFile": str(file_path),
                    "entries": result["entries"],
                    "stacksId": self._stacks_id,
                    "mode": "write",
                    "includeSources": self._include_sources,
                }
            )
            return

        result = await self._channel.send_return_as_dict(
            "tracingStopChunk",
            None,
            {
                "mode": "archive",
            },
        )

        artifact = cast(
            Optional[Artifact],
            from_nullable_channel(result.get("artifact")),
        )

        # The artifact may be missing if the browser closed while stopping tracing.
        if not artifact:
            if self._stacks_id:
                await self._connection.local_utils.trace_discarded(self._stacks_id)
            return

        # Save trace to the final local file.
        await artifact.save_as(file_path)
        await artifact.delete()

        await self._connection.local_utils.zip(
            {
                "zipFile": str(file_path),
                "entries": [],
                "stacksId": self._stacks_id,
                "mode": "append",
                "includeSources": self._include_sources,
            }
        )

    def _reset_stack_counter(self) -> None:
        if self._is_tracing:
            self._is_tracing = False
            self._connection.set_is_tracing(False)

    async def group(self, name: str, location: TracingGroupLocation = None) -> None:
        await self._channel.send("tracingGroup", None, locals_to_params(locals()))

    async def group_end(self) -> None:
        await self._channel.send(
            "tracingGroupEnd",
            None,
        )
