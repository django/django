import abc
import socket
from time import sleep
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Generic,
    Iterable,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
)

from redis.exceptions import ConnectionError, TimeoutError

T = TypeVar("T")
E = TypeVar("E", bound=Exception, covariant=True)

if TYPE_CHECKING:
    from redis.backoff import AbstractBackoff


class AbstractRetry(Generic[E], abc.ABC):
    """Retry a specific number of times after a failure"""

    _supported_errors: Tuple[Type[E], ...]

    def __init__(
        self,
        backoff: "AbstractBackoff",
        retries: int,
        supported_errors: Tuple[Type[E], ...],
    ):
        """
        Initialize a `Retry` object with a `Backoff` object
        that retries a maximum of `retries` times.
        `retries` can be negative to retry forever.
        You can specify the types of supported errors which trigger
        a retry with the `supported_errors` parameter.
        """
        self._backoff = backoff
        self._retries = retries
        self._supported_errors = supported_errors

    @abc.abstractmethod
    def __eq__(self, other: Any) -> bool:
        return NotImplemented

    def __hash__(self) -> int:
        return hash((self._backoff, self._retries, frozenset(self._supported_errors)))

    def update_supported_errors(self, specified_errors: Iterable[Type[E]]) -> None:
        """
        Updates the supported errors with the specified error types
        """
        self._supported_errors = tuple(
            set(self._supported_errors + tuple(specified_errors))
        )

    def get_retries(self) -> int:
        """
        Get the number of retries.
        """
        return self._retries

    def update_retries(self, value: int) -> None:
        """
        Set the number of retries.
        """
        self._retries = value


class Retry(AbstractRetry[Exception]):
    __hash__ = AbstractRetry.__hash__

    def __init__(
        self,
        backoff: "AbstractBackoff",
        retries: int,
        supported_errors: Tuple[Type[Exception], ...] = (
            ConnectionError,
            TimeoutError,
            socket.timeout,
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

    def call_with_retry(
        self,
        do: Callable[[], T],
        fail: Union[Callable[[Exception], Any], Callable[[Exception, int], Any]],
        is_retryable: Optional[Callable[[Exception], bool]] = None,
        with_failure_count: bool = False,
    ) -> T:
        """
        Execute an operation that might fail and returns its result, or
        raise the exception that was thrown depending on the `Backoff` object.
        `do`: the operation to call. Expects no argument.
        `fail`: the failure handler, expects the last error that was thrown
        ``is_retryable``: optional function to determine if an error is retryable
        ``with_failure_count``: if True, the failure count is passed to the failure handler
        """
        self._backoff.reset()
        failures = 0
        while True:
            try:
                return do()
            except self._supported_errors as error:
                if is_retryable and not is_retryable(error):
                    raise
                failures += 1

                if with_failure_count:
                    fail(error, failures)
                else:
                    fail(error)

                if self._retries >= 0 and failures > self._retries:
                    raise error
                backoff = self._backoff.compute(failures)
                if backoff > 0:
                    sleep(backoff)
