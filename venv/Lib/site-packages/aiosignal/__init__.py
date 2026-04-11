import sys
from typing import Any, Awaitable, Callable, TypeVar

from frozenlist import FrozenList

if sys.version_info >= (3, 11):
    from typing import Unpack
else:
    from typing_extensions import Unpack

if sys.version_info >= (3, 13):
    from typing import TypeVarTuple
else:
    from typing_extensions import TypeVarTuple

_T = TypeVar("_T")
_Ts = TypeVarTuple("_Ts", default=Unpack[tuple[()]])

__version__ = "1.4.0"

__all__ = ("Signal",)


class Signal(FrozenList[Callable[[Unpack[_Ts]], Awaitable[object]]]):
    """Coroutine-based signal implementation.

    To connect a callback to a signal, use any list method.

    Signals are fired using the send() coroutine, which takes named
    arguments.
    """

    __slots__ = ("_owner",)

    def __init__(self, owner: object):
        super().__init__()
        self._owner = owner

    def __repr__(self) -> str:
        return "<Signal owner={}, frozen={}, {!r}>".format(
            self._owner, self.frozen, list(self)
        )

    async def send(self, *args: Unpack[_Ts], **kwargs: Any) -> None:
        """
        Sends data to all registered receivers.
        """
        if not self.frozen:
            raise RuntimeError("Cannot send non-frozen signal.")

        for receiver in self:
            await receiver(*args, **kwargs)

    def __call__(
        self, func: Callable[[Unpack[_Ts]], Awaitable[_T]]
    ) -> Callable[[Unpack[_Ts]], Awaitable[_T]]:
        """Decorator to add a function to this Signal."""
        self.append(func)
        return func
