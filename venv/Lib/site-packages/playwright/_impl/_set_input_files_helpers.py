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
import collections.abc
import os
import stat
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Dict,
    List,
    Optional,
    Sequence,
    Tuple,
    TypedDict,
    Union,
    cast,
)

from playwright._impl._connection import Channel, from_channel
from playwright._impl._helper import Error
from playwright._impl._writable_stream import WritableStream

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl._browser_context import BrowserContext

from playwright._impl._api_structures import FilePayload

SIZE_LIMIT_IN_BYTES = 50 * 1024 * 1024


class InputFilesList(TypedDict, total=False):
    streams: Optional[List[Channel]]
    directoryStream: Optional[Channel]
    localDirectory: Optional[str]
    localPaths: Optional[List[str]]
    payloads: Optional[List[Dict[str, Union[str, bytes]]]]


def _list_files(directory: str) -> List[str]:
    files = []
    for root, _, filenames in os.walk(directory):
        for filename in filenames:
            files.append(os.path.join(root, filename))
    return files


async def convert_input_files(
    files: Union[
        str, Path, FilePayload, Sequence[Union[str, Path]], Sequence[FilePayload]
    ],
    context: "BrowserContext",
) -> InputFilesList:
    items = (
        files
        if isinstance(files, collections.abc.Sequence) and not isinstance(files, str)
        else [files]
    )

    if any([isinstance(item, (str, Path)) for item in items]):
        if not all([isinstance(item, (str, Path)) for item in items]):
            raise Error("File paths cannot be mixed with buffers")

        (local_paths, local_directory) = resolve_paths_and_directory_for_input_files(
            cast(Sequence[Union[str, Path]], items)
        )

        if context._channel._connection.is_remote:
            files_to_stream = cast(
                List[str],
                (_list_files(local_directory) if local_directory else local_paths),
            )
            streams = []
            result = await context._connection.wrap_api_call(
                lambda: context._channel.send_return_as_dict(
                    "createTempFiles",
                    None,
                    {
                        "rootDirName": (
                            os.path.basename(local_directory)
                            if local_directory
                            else None
                        ),
                        "items": list(
                            map(
                                lambda file: dict(
                                    name=(
                                        os.path.relpath(file, local_directory)
                                        if local_directory
                                        else os.path.basename(file)
                                    ),
                                    lastModifiedMs=int(os.path.getmtime(file) * 1000),
                                ),
                                files_to_stream,
                            )
                        ),
                    },
                )
            )
            for i, file in enumerate(result["writableStreams"]):
                stream: WritableStream = from_channel(file)
                await stream.copy(files_to_stream[i])
                streams.append(stream._channel)
            return InputFilesList(
                streams=None if local_directory else streams,
                directoryStream=result.get("rootDir"),
            )
        return InputFilesList(localPaths=local_paths, localDirectory=local_directory)

    file_payload_exceeds_size_limit = (
        sum([len(f.get("buffer", "")) for f in items if not isinstance(f, (str, Path))])
        > SIZE_LIMIT_IN_BYTES
    )
    if file_payload_exceeds_size_limit:
        raise Error(
            "Cannot set buffer larger than 50Mb, please write it to a file and pass its path instead."
        )

    return InputFilesList(
        payloads=[
            {
                "name": item["name"],
                "mimeType": item["mimeType"],
                "buffer": base64.b64encode(item["buffer"]).decode(),
            }
            for item in cast(List[FilePayload], items)
        ]
    )


def resolve_paths_and_directory_for_input_files(
    items: Sequence[Union[str, Path]],
) -> Tuple[Optional[List[str]], Optional[str]]:
    local_paths: Optional[List[str]] = None
    local_directory: Optional[str] = None
    for item in items:
        item_stat = os.stat(item)  # Raises FileNotFoundError if doesn't exist
        if stat.S_ISDIR(item_stat.st_mode):
            if local_directory:
                raise Error("Multiple directories are not supported")
            local_directory = str(Path(item).resolve())
        else:
            local_paths = local_paths or []
            local_paths.append(str(Path(item).resolve()))
    if local_paths and local_directory:
        raise Error("File paths must be all files or a single directory")
    return (local_paths, local_directory)
