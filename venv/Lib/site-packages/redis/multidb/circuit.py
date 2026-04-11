from abc import ABC, abstractmethod
from enum import Enum
from typing import Callable

import pybreaker

DEFAULT_GRACE_PERIOD = 60


class State(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half-open"


class CircuitBreaker(ABC):
    @property
    @abstractmethod
    def grace_period(self) -> float:
        """The grace period in seconds when the circle should be kept open."""
        pass

    @grace_period.setter
    @abstractmethod
    def grace_period(self, grace_period: float):
        """Set the grace period in seconds."""

    @property
    @abstractmethod
    def state(self) -> State:
        """The current state of the circuit."""
        pass

    @state.setter
    @abstractmethod
    def state(self, state: State):
        """Set current state of the circuit."""
        pass

    @property
    @abstractmethod
    def database(self):
        """Database associated with this circuit."""
        pass

    @database.setter
    @abstractmethod
    def database(self, database):
        """Set database associated with this circuit."""
        pass

    @abstractmethod
    def on_state_changed(self, cb: Callable[["CircuitBreaker", State, State], None]):
        """Callback called when the state of the circuit changes."""
        pass


class BaseCircuitBreaker(CircuitBreaker):
    """
    Base implementation of Circuit Breaker interface.
    """

    def __init__(self, cb: pybreaker.CircuitBreaker):
        self._cb = cb
        self._state_pb_mapper = {
            State.CLOSED: self._cb.close,
            State.OPEN: self._cb.open,
            State.HALF_OPEN: self._cb.half_open,
        }
        self._database = None

    @property
    def grace_period(self) -> float:
        return self._cb.reset_timeout

    @grace_period.setter
    def grace_period(self, grace_period: float):
        self._cb.reset_timeout = grace_period

    @property
    def state(self) -> State:
        return State(value=self._cb.state.name)

    @state.setter
    def state(self, state: State):
        self._state_pb_mapper[state]()

    @property
    def database(self):
        return self._database

    @database.setter
    def database(self, database):
        self._database = database

    @abstractmethod
    def on_state_changed(self, cb: Callable[["CircuitBreaker", State, State], None]):
        """Callback called when the state of the circuit changes."""
        pass


class PBListener(pybreaker.CircuitBreakerListener):
    """Wrapper for callback to be compatible with pybreaker implementation."""

    def __init__(
        self,
        cb: Callable[[CircuitBreaker, State, State], None],
        database,
    ):
        """
        Initialize a PBListener instance.

        Args:
            cb: Callback function that will be called when the circuit breaker state changes.
            database: Database instance associated with this circuit breaker.
        """

        self._cb = cb
        self._database = database

    def state_change(self, cb, old_state, new_state):
        cb = PBCircuitBreakerAdapter(cb)
        cb.database = self._database
        old_state = State(value=old_state.name)
        new_state = State(value=new_state.name)
        self._cb(cb, old_state, new_state)


class PBCircuitBreakerAdapter(BaseCircuitBreaker):
    def __init__(self, cb: pybreaker.CircuitBreaker):
        """
        Initialize a PBCircuitBreakerAdapter instance.

        This adapter wraps pybreaker's CircuitBreaker implementation to make it compatible
        with our CircuitBreaker interface.

        Args:
            cb: A pybreaker CircuitBreaker instance to be adapted.
        """
        super().__init__(cb)

    def on_state_changed(self, cb: Callable[["CircuitBreaker", State, State], None]):
        listener = PBListener(cb, self.database)
        self._cb.add_listener(listener)
