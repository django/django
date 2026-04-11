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

import inspect
from typing import Any, Callable, Dict, List, Optional, Sequence, Union

from playwright._impl._errors import Error
from playwright._impl._map import Map

API_ATTR = "_pw_api_instance_"
IMPL_ATTR = "_pw_impl_instance_"


class ImplWrapper:
    def __init__(self, impl_obj: Any) -> None:
        self._impl_obj = impl_obj

    def __repr__(self) -> str:
        return self._impl_obj.__repr__()


class ImplToApiMapping:
    def __init__(self) -> None:
        self._mapping: Dict[type, type] = {}

    def register(self, impl_class: type, api_class: type) -> None:
        self._mapping[impl_class] = api_class

    def from_maybe_impl(
        self, obj: Any, visited: Optional[Map[Any, Union[List, Dict]]] = None
    ) -> Any:
        # Python does share default arguments between calls, so we need to
        # create a new map if it is not provided.
        if not visited:
            visited = Map()
        if not obj:
            return obj
        if isinstance(obj, dict):
            if obj in visited:
                return visited[obj]
            o: Dict = {}
            visited[obj] = o
            for name, value in obj.items():
                o[name] = self.from_maybe_impl(value, visited)
            return o
        if isinstance(obj, list):
            if obj in visited:
                return visited[obj]
            a: List = []
            visited[obj] = a
            for item in obj:
                a.append(self.from_maybe_impl(item, visited))
            return a
        api_class = self._mapping.get(type(obj))
        if api_class:
            api_instance = getattr(obj, API_ATTR, None)
            if not api_instance:
                api_instance = api_class(obj)
                setattr(obj, API_ATTR, api_instance)
            return api_instance
        else:
            return obj

    def from_impl(self, obj: Any) -> Any:
        assert obj
        result = self.from_maybe_impl(obj)
        assert result
        return result

    def from_impl_nullable(self, obj: Any = None) -> Optional[Any]:
        return self.from_impl(obj) if obj else None

    def from_impl_list(self, items: Sequence[Any]) -> List[Any]:
        return list(map(lambda a: self.from_impl(a), items))

    def from_impl_dict(self, map: Dict[str, Any]) -> Dict[str, Any]:
        return {name: self.from_impl(value) for name, value in map.items()}

    def to_impl(
        self, obj: Any, visited: Optional[Map[Any, Union[List, Dict]]] = None
    ) -> Any:
        if visited is None:
            visited = Map()
        try:
            if not obj:
                return obj
            if isinstance(obj, dict):
                if obj in visited:
                    return visited[obj]
                o: Dict = {}
                visited[obj] = o
                for name, value in obj.items():
                    o[name] = self.to_impl(value, visited)
                return o
            if isinstance(obj, list):
                if obj in visited:
                    return visited[obj]
                a: List = []
                visited[obj] = a
                for item in obj:
                    a.append(self.to_impl(item, visited))
                return a
            if isinstance(obj, ImplWrapper):
                return obj._impl_obj
            return obj
        except RecursionError:
            raise Error("Maximum argument depth exceeded")

    def wrap_handler(self, handler: Callable[..., Any]) -> Callable[..., None]:
        def wrapper_func(*args: Any) -> Any:
            arg_count = len(inspect.signature(handler).parameters)
            return handler(
                *list(map(lambda a: self.from_maybe_impl(a), args))[:arg_count]
            )

        if inspect.ismethod(handler):
            wrapper = getattr(handler.__self__, IMPL_ATTR + handler.__name__, None)
            if not wrapper:
                wrapper = wrapper_func
                setattr(
                    handler.__self__,
                    IMPL_ATTR + handler.__name__,
                    wrapper,
                )
            return wrapper

        wrapper = getattr(handler, IMPL_ATTR, None)
        if not wrapper:
            wrapper = wrapper_func
            setattr(handler, IMPL_ATTR, wrapper)
        return wrapper
