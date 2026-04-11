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
import os
from typing import Tuple

import greenlet


def _greenlet_trace_callback(
    event: str, args: Tuple[greenlet.greenlet, greenlet.greenlet]
) -> None:
    if event in ("switch", "throw"):
        origin, target = args
        print(f"Transfer from {origin} to {target} with {event}")


if os.environ.get("INTERNAL_PW_GREENLET_DEBUG"):
    greenlet.settrace(_greenlet_trace_callback)


class MainGreenlet(greenlet.greenlet):
    def __str__(self) -> str:
        return "<MainGreenlet>"


class RouteGreenlet(greenlet.greenlet):
    def __str__(self) -> str:
        return "<RouteGreenlet>"


class LocatorHandlerGreenlet(greenlet.greenlet):
    def __str__(self) -> str:
        return "<LocatorHandlerGreenlet>"


class EventGreenlet(greenlet.greenlet):
    def __str__(self) -> str:
        return "<EventGreenlet>"
