from abc import abstractmethod
from typing import Optional, Union

from redis.asyncio import Redis, RedisCluster
from redis.data_structure import WeightedList
from redis.multidb.circuit import CircuitBreaker
from redis.multidb.database import AbstractDatabase, BaseDatabase
from redis.typing import Number


class AsyncDatabase(AbstractDatabase):
    """Database with an underlying asynchronous redis client."""

    @property
    @abstractmethod
    def client(self) -> Union[Redis, RedisCluster]:
        """The underlying redis client."""
        pass

    @client.setter
    @abstractmethod
    def client(self, client: Union[Redis, RedisCluster]):
        """Set the underlying redis client."""
        pass

    @property
    @abstractmethod
    def circuit(self) -> CircuitBreaker:
        """Circuit breaker for the current database."""
        pass

    @circuit.setter
    @abstractmethod
    def circuit(self, circuit: CircuitBreaker):
        """Set the circuit breaker for the current database."""
        pass


Databases = WeightedList[tuple[AsyncDatabase, Number]]


class Database(BaseDatabase, AsyncDatabase):
    def __init__(
        self,
        client: Union[Redis, RedisCluster],
        circuit: CircuitBreaker,
        weight: float,
        health_check_url: Optional[str] = None,
    ):
        self._client = client
        self._cb = circuit
        self._cb.database = self
        super().__init__(weight, health_check_url)

    @property
    def client(self) -> Union[Redis, RedisCluster]:
        return self._client

    @client.setter
    def client(self, client: Union[Redis, RedisCluster]):
        self._client = client

    @property
    def circuit(self) -> CircuitBreaker:
        return self._cb

    @circuit.setter
    def circuit(self, circuit: CircuitBreaker):
        self._cb = circuit

    def __repr__(self):
        return f"Database(client={self.client}, weight={self.weight})"
