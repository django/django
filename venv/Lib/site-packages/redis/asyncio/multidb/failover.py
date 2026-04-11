import time
from abc import ABC, abstractmethod

from redis.asyncio.multidb.database import AsyncDatabase, Databases
from redis.data_structure import WeightedList
from redis.multidb.circuit import State as CBState
from redis.multidb.exception import (
    NoValidDatabaseException,
    TemporaryUnavailableException,
)

DEFAULT_FAILOVER_ATTEMPTS = 10
DEFAULT_FAILOVER_DELAY = 12


class AsyncFailoverStrategy(ABC):
    @abstractmethod
    async def database(self) -> AsyncDatabase:
        """Select the database according to the strategy."""
        pass

    @abstractmethod
    def set_databases(self, databases: Databases) -> None:
        """Set the database strategy operates on."""
        pass


class FailoverStrategyExecutor(ABC):
    @property
    @abstractmethod
    def failover_attempts(self) -> int:
        """The number of failover attempts."""
        pass

    @property
    @abstractmethod
    def failover_delay(self) -> float:
        """The delay between failover attempts."""
        pass

    @property
    @abstractmethod
    def strategy(self) -> AsyncFailoverStrategy:
        """The strategy to execute."""
        pass

    @abstractmethod
    async def execute(self) -> AsyncDatabase:
        """Execute the failover strategy."""
        pass


class WeightBasedFailoverStrategy(AsyncFailoverStrategy):
    """
    Failover strategy based on database weights.
    """

    def __init__(self):
        self._databases = WeightedList()

    async def database(self) -> AsyncDatabase:
        for database, _ in self._databases:
            if database.circuit.state == CBState.CLOSED:
                return database

        raise NoValidDatabaseException("No valid database available for communication")

    def set_databases(self, databases: Databases) -> None:
        self._databases = databases


class DefaultFailoverStrategyExecutor(FailoverStrategyExecutor):
    """
    Executes given failover strategy.
    """

    def __init__(
        self,
        strategy: AsyncFailoverStrategy,
        failover_attempts: int = DEFAULT_FAILOVER_ATTEMPTS,
        failover_delay: float = DEFAULT_FAILOVER_DELAY,
    ):
        self._strategy = strategy
        self._failover_attempts = failover_attempts
        self._failover_delay = failover_delay
        self._next_attempt_ts: int = 0
        self._failover_counter: int = 0

    @property
    def failover_attempts(self) -> int:
        return self._failover_attempts

    @property
    def failover_delay(self) -> float:
        return self._failover_delay

    @property
    def strategy(self) -> AsyncFailoverStrategy:
        return self._strategy

    async def execute(self) -> AsyncDatabase:
        try:
            database = await self._strategy.database()
            self._reset()
            return database
        except NoValidDatabaseException as e:
            if self._next_attempt_ts == 0:
                self._next_attempt_ts = time.time() + self._failover_delay
                self._failover_counter += 1
            elif time.time() >= self._next_attempt_ts:
                self._next_attempt_ts += self._failover_delay
                self._failover_counter += 1

            if self._failover_counter > self._failover_attempts:
                self._reset()
                raise e
            else:
                raise TemporaryUnavailableException(
                    "No database connections currently available. "
                    "This is a temporary condition - please retry the operation."
                )

    def _reset(self) -> None:
        self._next_attempt_ts = 0
        self._failover_counter = 0
