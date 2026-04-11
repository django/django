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
from typing import Dict, Generic, Tuple, TypeVar

K = TypeVar("K")
V = TypeVar("V")


class Map(Generic[K, V]):
    def __init__(self) -> None:
        self._entries: Dict[int, Tuple[K, V]] = {}

    def __contains__(self, item: K) -> bool:
        return id(item) in self._entries

    def __setitem__(self, idx: K, value: V) -> None:
        self._entries[id(idx)] = (idx, value)

    def __getitem__(self, obj: K) -> V:
        return self._entries[id(obj)][1]
