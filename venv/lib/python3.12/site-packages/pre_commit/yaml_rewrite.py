from __future__ import annotations

from collections.abc import Generator
from collections.abc import Iterable
from typing import NamedTuple
from typing import Protocol

from yaml.nodes import MappingNode
from yaml.nodes import Node
from yaml.nodes import ScalarNode
from yaml.nodes import SequenceNode


class _Matcher(Protocol):
    def match(self, n: Node) -> Generator[Node]: ...


class MappingKey(NamedTuple):
    k: str

    def match(self, n: Node) -> Generator[Node]:
        if isinstance(n, MappingNode):
            for k, _ in n.value:
                if k.value == self.k:
                    yield k


class MappingValue(NamedTuple):
    k: str

    def match(self, n: Node) -> Generator[Node]:
        if isinstance(n, MappingNode):
            for k, v in n.value:
                if k.value == self.k:
                    yield v


class SequenceItem(NamedTuple):
    def match(self, n: Node) -> Generator[Node]:
        if isinstance(n, SequenceNode):
            yield from n.value


def _match(gen: Iterable[Node], m: _Matcher) -> Iterable[Node]:
    return (n for src in gen for n in m.match(src))


def match(n: Node, matcher: tuple[_Matcher, ...]) -> Generator[ScalarNode]:
    gen: Iterable[Node] = (n,)
    for m in matcher:
        gen = _match(gen, m)
    return (n for n in gen if isinstance(n, ScalarNode))
