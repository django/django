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
from typing import TYPE_CHECKING, Union

from playwright._impl._artifact import Artifact
from playwright._impl._helper import Error

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl._page import Page


class Video:
    def __init__(self, page: "Page") -> None:
        self._loop = page._loop
        self._dispatcher_fiber = page._dispatcher_fiber
        self._page = page
        self._artifact_future = page._loop.create_future()
        if page.is_closed():
            self._page_closed()
        else:
            page.on("close", lambda page: self._page_closed())

    def __repr__(self) -> str:
        return f"<Video page={self._page}>"

    def _page_closed(self) -> None:
        if not self._artifact_future.done():
            self._artifact_future.set_exception(Error("Page closed"))

    def _artifact_ready(self, artifact: Artifact) -> None:
        if not self._artifact_future.done():
            self._artifact_future.set_result(artifact)

    async def path(self) -> pathlib.Path:
        if self._page._connection.is_remote:
            raise Error(
                "Path is not available when using browserType.connect(). Use save_as() to save a local copy."
            )
        artifact = await self._artifact_future
        if not artifact:
            raise Error("Page did not produce any video frames")
        return artifact.absolute_path

    async def save_as(self, path: Union[str, pathlib.Path]) -> None:
        if self._page._connection._is_sync and not self._page._is_closed:
            raise Error(
                "Page is not yet closed. Close the page prior to calling save_as"
            )
        artifact = await self._artifact_future
        if not artifact:
            raise Error("Page did not produce any video frames")
        await artifact.save_as(path)

    async def delete(self) -> None:
        artifact = await self._artifact_future
        if not artifact:
            raise Error("Page did not produce any video frames")
        await artifact.delete()
