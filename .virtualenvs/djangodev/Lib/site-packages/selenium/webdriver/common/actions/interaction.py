# Licensed to the Software Freedom Conservancy (SFC) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The SFC licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
from typing import Dict
from typing import Union

KEY = "key"
POINTER = "pointer"
NONE = "none"
WHEEL = "wheel"
SOURCE_TYPES = {KEY, POINTER, NONE}

POINTER_MOUSE = "mouse"
POINTER_TOUCH = "touch"
POINTER_PEN = "pen"

POINTER_KINDS = {POINTER_MOUSE, POINTER_TOUCH, POINTER_PEN}


class Interaction:
    PAUSE = "pause"

    def __init__(self, source: str) -> None:
        self.source = source


class Pause(Interaction):
    def __init__(self, source, duration: float = 0) -> None:
        super().__init__(source)
        self.duration = duration

    def encode(self) -> Dict[str, Union[str, int]]:
        return {"type": self.PAUSE, "duration": int(self.duration * 1000)}
