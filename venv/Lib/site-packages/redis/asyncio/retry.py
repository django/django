from asyncio import sleep
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Tuple, Type, TypeVar

from redis.exceptions import ConnectionError, RedisError, TimeoutError
from redis.retry import AbstractRetry

T = TypeVar("T")

if TYPE_CHECKING:
    from redis.backoff import AbstractBackoff


class Retry(AbstractRetry[RedisError]):
    __hash__ = AbstractRetry.__hash__

    def __init__(
        self,
        backoff: "AbstractBackoff",
        retries: int,
        supported_errors: Tuple[Type[RedisError], ...] = (
            ConnectionError,
            TimeoutError,
        ),
    ):
        super().__init__(backoff, retries, supported_errors)

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Retry):
            return NotImplemented

        return (
            self._backoff == other._backoff
            and self._retries == other._retries
            and set(self._supported_errors) == set(other._supported_errors)
        )

    async def call_with_retry(
        self, do: Callable[[], Awaitable[T]], fail: Callable[[RedisError], Any]
    ) -> T:
        """
        Execute an operation that might fail and returns its result, or
        raise the exception that was thrown depending on the `Backoff` object.
        `do`: the operation to call. Expects no argument.
        `fail`: the failure handler, expects the last error that was thrown
        """
        self._backoff.reset()
        failures = 0
        while True:
            try:
                return await do()
            except self._supported_errors as error:
                failures += 1
                await fail(error)
                if self._retries >= 0 and failures > self._retries:
                    raise error
                backoff = self._backoff.compute(failures)
                if backoff > 0:
                    await sleep(backoff)
