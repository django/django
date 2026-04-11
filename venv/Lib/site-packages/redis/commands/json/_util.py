from typing import List, Mapping, Union

JsonType = Union[
    str, int, float, bool, None, Mapping[str, "JsonType"], List["JsonType"]
]
