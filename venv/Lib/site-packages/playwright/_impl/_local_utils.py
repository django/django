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
from typing import Dict, List, Optional, cast

from playwright._impl._api_structures import HeadersArray
from playwright._impl._connection import ChannelOwner, StackFrame
from playwright._impl._helper import HarLookupResult, locals_to_params


class LocalUtils(ChannelOwner):
    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self.devices = {
            device["name"]: parse_device_descriptor(device["descriptor"])
            for device in initializer["deviceDescriptors"]
        }

    async def zip(self, params: Dict) -> None:
        await self._channel.send("zip", None, params)

    async def har_open(self, file: str) -> None:
        params = locals_to_params(locals())
        await self._channel.send("harOpen", None, params)

    async def har_lookup(
        self,
        harId: str,
        url: str,
        method: str,
        headers: HeadersArray,
        isNavigationRequest: bool,
        postData: Optional[bytes] = None,
    ) -> HarLookupResult:
        params = locals_to_params(locals())
        if "postData" in params:
            params["postData"] = base64.b64encode(params["postData"]).decode()
        return cast(
            HarLookupResult,
            await self._channel.send_return_as_dict("harLookup", None, params),
        )

    async def har_close(self, harId: str) -> None:
        params = locals_to_params(locals())
        await self._channel.send("harClose", None, params)

    async def har_unzip(self, zipFile: str, harFile: str) -> None:
        params = locals_to_params(locals())
        await self._channel.send("harUnzip", None, params)

    async def tracing_started(self, tracesDir: Optional[str], traceName: str) -> str:
        params = locals_to_params(locals())
        return await self._channel.send("tracingStarted", None, params)

    async def trace_discarded(self, stacks_id: str) -> None:
        return await self._channel.send("traceDiscarded", None, {"stacksId": stacks_id})

    def add_stack_to_tracing_no_reply(self, id: int, frames: List[StackFrame]) -> None:
        self._channel.send_no_reply(
            "addStackToTracingNoReply",
            None,
            {
                "callData": {
                    "stack": frames,
                    "id": id,
                }
            },
        )


def parse_device_descriptor(dict: Dict) -> Dict:
    return {
        "user_agent": dict["userAgent"],
        "viewport": dict["viewport"],
        "device_scale_factor": dict["deviceScaleFactor"],
        "is_mobile": dict["isMobile"],
        "has_touch": dict["hasTouch"],
        "default_browser_type": dict["defaultBrowserType"],
    }
