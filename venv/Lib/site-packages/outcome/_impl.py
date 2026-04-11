from __future__ import annotations

import abc
from typing import (
    TYPE_CHECKING,
    AsyncGenerator,
    Awaitable,
    Callable,
    Generator,
    Generic,
    NoReturn,
    TypeVar,
    Union,
    overload,
)

import attr

from ._util import AlreadyUsedError, remove_tb_frames

if TYPE_CHECKING:
    from typing_extensions import ParamSpec, final
    ArgsT = ParamSpec("ArgsT")
else:

    def final(func):
        return func


__all__ = ['Error', 'Outcome', 'Maybe', 'Value', 'acapture', 'capture']

ValueT = TypeVar("ValueT", covariant=True)
ResultT = TypeVar("ResultT")


@overload
def capture(
        # NoReturn = raises exception, so we should get an error.
        sync_fn: Callable[ArgsT, NoReturn],
        *args: ArgsT.args,
        **kwargs: ArgsT.kwargs,
) -> Error:
    ...


@overload
def capture(
        sync_fn: Callable[ArgsT, ResultT],
        *args: ArgsT.args,
        **kwargs: ArgsT.kwargs,
) -> Value[ResultT] | Error:
    ...


def capture(
        sync_fn: Callable[ArgsT, ResultT],
        *args: ArgsT.args,
        **kwargs: ArgsT.kwargs,
) -> Value[ResultT] | Error:
    """Run ``sync_fn(*args, **kwargs)`` and capture the result.

    Returns:
      Either a :class:`Value` or :class:`Error` as appropriate.

    """
    try:
        return Value(sync_fn(*args, **kwargs))
    except BaseException as exc:
        exc = remove_tb_frames(exc, 1)
        return Error(exc)


@overload
async def acapture(
        async_fn: Callable[ArgsT, Awaitable[NoReturn]],
        *args: ArgsT.args,
        **kwargs: ArgsT.kwargs,
) -> Error:
    ...


@overload
async def acapture(
        async_fn: Callable[ArgsT, Awaitable[ResultT]],
        *args: ArgsT.args,
        **kwargs: ArgsT.kwargs,
) -> Value[ResultT] | Error:
    ...


async def acapture(
        async_fn: Callable[ArgsT, Awaitable[ResultT]],
        *args: ArgsT.args,
        **kwargs: ArgsT.kwargs,
) -> Value[ResultT] | Error:
    """Run ``await async_fn(*args, **kwargs)`` and capture the result.

    Returns:
      Either a :class:`Value` or :class:`Error` as appropriate.

    """
    try:
        return Value(await async_fn(*args, **kwargs))
    except BaseException as exc:
        exc = remove_tb_frames(exc, 1)
        return Error(exc)


@attr.s(repr=False, init=False, slots=True)
class Outcome(abc.ABC, Generic[ValueT]):
    """An abstract class representing the result of a Python computation.

    This class has two concrete subclasses: :class:`Value` representing a
    value, and :class:`Error` representing an exception.

    In addition to the methods described below, comparison operators on
    :class:`Value` and :class:`Error` objects (``==``, ``<``, etc.) check that
    the other object is also a :class:`Value` or :class:`Error` object
    respectively, and then compare the contained objects.

    :class:`Outcome` objects are hashable if the contained objects are
    hashable.

    """
    _unwrapped: bool = attr.ib(default=False, eq=False, init=False)

    def _set_unwrapped(self) -> None:
        if self._unwrapped:
            raise AlreadyUsedError
        object.__setattr__(self, '_unwrapped', True)

    @abc.abstractmethod
    def unwrap(self) -> ValueT:
        """Return or raise the contained value or exception.

        These two lines of code are equivalent::

           x = fn(*args)
           x = outcome.capture(fn, *args).unwrap()

        """

    @abc.abstractmethod
    def send(self, gen: Generator[ResultT, ValueT, object]) -> ResultT:
        """Send or throw the contained value or exception into the given
        generator object.

        Args:
          gen: A generator object supporting ``.send()`` and ``.throw()``
              methods.

        """

    @abc.abstractmethod
    async def asend(self, agen: AsyncGenerator[ResultT, ValueT]) -> ResultT:
        """Send or throw the contained value or exception into the given async
        generator object.

        Args:
          agen: An async generator object supporting ``.asend()`` and
              ``.athrow()`` methods.

        """


@final
@attr.s(frozen=True, repr=False, slots=True)
class Value(Outcome[ValueT], Generic[ValueT]):
    """Concrete :class:`Outcome` subclass representing a regular value.

    """

    value: ValueT = attr.ib()
    """The contained value."""

    def __repr__(self) -> str:
        return f'Value({self.value!r})'

    def unwrap(self) -> ValueT:
        self._set_unwrapped()
        return self.value

    def send(self, gen: Generator[ResultT, ValueT, object]) -> ResultT:
        self._set_unwrapped()
        return gen.send(self.value)

    async def asend(self, agen: AsyncGenerator[ResultT, ValueT]) -> ResultT:
        self._set_unwrapped()
        return await agen.asend(self.value)


@final
@attr.s(frozen=True, repr=False, slots=True)
class Error(Outcome[NoReturn]):
    """Concrete :class:`Outcome` subclass representing a raised exception.

    """

    error: BaseException = attr.ib(
        validator=attr.validators.instance_of(BaseException)
    )
    """The contained exception object."""

    def __repr__(self) -> str:
        return f'Error({self.error!r})'

    def unwrap(self) -> NoReturn:
        self._set_unwrapped()
        # Tracebacks show the 'raise' line below out of context, so let's give
        # this variable a name that makes sense out of context.
        captured_error = self.error
        try:
            raise captured_error
        finally:
            # We want to avoid creating a reference cycle here. Python does
            # collect cycles just fine, so it wouldn't be the end of the world
            # if we did create a cycle, but the cyclic garbage collector adds
            # latency to Python programs, and the more cycles you create, the
            # more often it runs, so it's nicer to avoid creating them in the
            # first place. For more details see:
            #
            #    https://github.com/python-trio/trio/issues/1770
            #
            # In particuar, by deleting this local variables from the 'unwrap'
            # methods frame, we avoid the 'captured_error' object's
            # __traceback__ from indirectly referencing 'captured_error'.
            del captured_error, self

    def send(self, gen: Generator[ResultT, NoReturn, object]) -> ResultT:
        self._set_unwrapped()
        return gen.throw(self.error)

    async def asend(self, agen: AsyncGenerator[ResultT, NoReturn]) -> ResultT:
        self._set_unwrapped()
        return await agen.athrow(self.error)


# A convenience alias to a union of both results, allowing exhaustiveness checking.
Maybe = Union[Value[ValueT], Error]
