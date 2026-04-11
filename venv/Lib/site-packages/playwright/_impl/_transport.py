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
import io
import json
import os
import subprocess
import sys
from abc import ABC, abstractmethod
from typing import Callable, Dict, Optional, Union

from playwright._impl._driver import compute_driver_executable, get_driver_env
from playwright._impl._helper import ParsedMessagePayload


# Sourced from: https://github.com/pytest-dev/pytest/blob/da01ee0a4bb0af780167ecd228ab3ad249511302/src/_pytest/faulthandler.py#L69-L77
def _get_stderr_fileno() -> Optional[int]:
    try:
        # when using pythonw, sys.stderr is None.
        # when Pyinstaller is used, there is no closed attribute because Pyinstaller monkey-patches it with a NullWriter class
        if sys.stderr is None or not hasattr(sys.stderr, "closed"):
            return None
        if sys.stderr.closed:
            return None

        return sys.stderr.fileno()
    except (NotImplementedError, AttributeError, io.UnsupportedOperation):
        # pytest-xdist monkeypatches sys.stderr with an object that is not an actual file.
        # https://docs.python.org/3/library/faulthandler.html#issue-with-file-descriptors
        # This is potentially dangerous, but the best we can do.
        if not hasattr(sys, "__stderr__") or not sys.__stderr__:
            return None
        return sys.__stderr__.fileno()


class Transport(ABC):
    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop
        self.on_message: Callable[[ParsedMessagePayload], None] = lambda _: None
        self.on_error_future: asyncio.Future = loop.create_future()

    @abstractmethod
    def request_stop(self) -> None:
        pass

    def dispose(self) -> None:
        pass

    @abstractmethod
    async def wait_until_stopped(self) -> None:
        pass

    @abstractmethod
    async def connect(self) -> None:
        pass

    @abstractmethod
    async def run(self) -> None:
        pass

    @abstractmethod
    def send(self, message: Dict) -> None:
        pass

    def serialize_message(self, message: Dict) -> bytes:
        msg = json.dumps(message)
        if "DEBUGP" in os.environ:  # pragma: no cover
            print("\x1b[32mSEND>\x1b[0m", json.dumps(message, indent=2))
        return msg.encode()

    def deserialize_message(self, data: Union[str, bytes]) -> ParsedMessagePayload:
        obj = json.loads(data)

        if "DEBUGP" in os.environ:  # pragma: no cover
            print("\x1b[33mRECV>\x1b[0m", json.dumps(obj, indent=2))
        return obj


class PipeTransport(Transport):
    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        super().__init__(loop)
        self._stopped = False

    def request_stop(self) -> None:
        assert self._output
        self._stopped = True
        self._output.close()

    async def wait_until_stopped(self) -> None:
        await self._stopped_future

    async def connect(self) -> None:
        self._stopped_future: asyncio.Future = asyncio.Future()

        try:
            # For pyinstaller and Nuitka
            env = get_driver_env()
            if getattr(sys, "frozen", False) or globals().get("__compiled__"):
                env.setdefault("PLAYWRIGHT_BROWSERS_PATH", "0")

            startupinfo = None
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE

            executable_path, entrypoint_path = compute_driver_executable()
            self._proc = await asyncio.create_subprocess_exec(
                executable_path,
                entrypoint_path,
                "run-driver",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=_get_stderr_fileno(),
                limit=32768,
                env=env,
                startupinfo=startupinfo,
            )
        except Exception as exc:
            self.on_error_future.set_exception(exc)
            raise exc

        self._output = self._proc.stdin

    async def run(self) -> None:
        assert self._proc.stdout
        assert self._proc.stdin
        while not self._stopped:
            try:
                buffer = await self._proc.stdout.readexactly(4)
                if self._stopped:
                    break
                length = int.from_bytes(buffer, byteorder="little", signed=False)
                buffer = bytes(0)
                while length:
                    to_read = min(length, 32768)
                    data = await self._proc.stdout.readexactly(to_read)
                    if self._stopped:
                        break
                    length -= to_read
                    if len(buffer):
                        buffer = buffer + data
                    else:
                        buffer = data
                if self._stopped:
                    break

                obj = self.deserialize_message(buffer)
                self.on_message(obj)
            except asyncio.IncompleteReadError:
                if not self._stopped:
                    self.on_error_future.set_exception(
                        Exception("Connection closed while reading from the driver")
                    )
                break
            await asyncio.sleep(0)

        await self._proc.communicate()
        self._stopped_future.set_result(None)

    def send(self, message: Dict) -> None:
        assert self._output
        data = self.serialize_message(message)
        self._output.write(
            len(data).to_bytes(4, byteorder="little", signed=False) + data
        )
