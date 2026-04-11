from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, Callable, List, Optional, Tuple

from redis.client import Pipeline, PubSub, PubSubWorkerThread
from redis.event import EventDispatcherInterface, OnCommandsFailEvent
from redis.multidb.circuit import State as CBState
from redis.multidb.config import DEFAULT_AUTO_FALLBACK_INTERVAL
from redis.multidb.database import Database, Databases, SyncDatabase
from redis.multidb.event import (
    ActiveDatabaseChanged,
    CloseConnectionOnActiveDatabaseChanged,
    RegisterCommandFailure,
    ResubscribeOnActiveDatabaseChanged,
)
from redis.multidb.failover import (
    DEFAULT_FAILOVER_ATTEMPTS,
    DEFAULT_FAILOVER_DELAY,
    DefaultFailoverStrategyExecutor,
    FailoverStrategy,
    FailoverStrategyExecutor,
)
from redis.multidb.failure_detector import FailureDetector
from redis.observability.attributes import GeoFailoverReason
from redis.observability.recorder import record_geo_failover
from redis.retry import Retry


class CommandExecutor(ABC):
    @property
    @abstractmethod
    def auto_fallback_interval(self) -> float:
        """Returns auto-fallback interval."""
        pass

    @auto_fallback_interval.setter
    @abstractmethod
    def auto_fallback_interval(self, auto_fallback_interval: float) -> None:
        """Sets auto-fallback interval."""
        pass


class BaseCommandExecutor(CommandExecutor):
    def __init__(
        self,
        auto_fallback_interval: float = DEFAULT_AUTO_FALLBACK_INTERVAL,
    ):
        self._auto_fallback_interval = auto_fallback_interval
        self._next_fallback_attempt: datetime

    @property
    def auto_fallback_interval(self) -> float:
        return self._auto_fallback_interval

    @auto_fallback_interval.setter
    def auto_fallback_interval(self, auto_fallback_interval: int) -> None:
        self._auto_fallback_interval = auto_fallback_interval

    def _schedule_next_fallback(self) -> None:
        if self._auto_fallback_interval < 0:
            return

        self._next_fallback_attempt = datetime.now() + timedelta(
            seconds=self._auto_fallback_interval
        )


class SyncCommandExecutor(CommandExecutor):
    @property
    @abstractmethod
    def databases(self) -> Databases:
        """Returns a list of databases."""
        pass

    @property
    @abstractmethod
    def failure_detectors(self) -> List[FailureDetector]:
        """Returns a list of failure detectors."""
        pass

    @abstractmethod
    def add_failure_detector(self, failure_detector: FailureDetector) -> None:
        """Adds a new failure detector to the list of failure detectors."""
        pass

    @property
    @abstractmethod
    def active_database(self) -> Optional[Database]:
        """Returns currently active database."""
        pass

    @active_database.setter
    @abstractmethod
    def active_database(self, value: Tuple[SyncDatabase, GeoFailoverReason]) -> None:
        """Sets the currently active database.

        Args:
            value: A tuple of (database, reason) where database is the new active
                   database and reason is the GeoFailoverReason for the change.
        """
        pass

    @property
    @abstractmethod
    def active_pubsub(self) -> Optional[PubSub]:
        """Returns currently active pubsub."""
        pass

    @active_pubsub.setter
    @abstractmethod
    def active_pubsub(self, pubsub: PubSub) -> None:
        """Sets currently active pubsub."""
        pass

    @property
    @abstractmethod
    def failover_strategy_executor(self) -> FailoverStrategyExecutor:
        """Returns failover strategy executor."""
        pass

    @property
    @abstractmethod
    def command_retry(self) -> Retry:
        """Returns command retry object."""
        pass

    @abstractmethod
    def pubsub(self, **kwargs):
        """Initializes a PubSub object on a currently active database"""
        pass

    @abstractmethod
    def execute_command(self, *args, **options):
        """Executes a command and returns the result."""
        pass

    @abstractmethod
    def execute_pipeline(self, command_stack: tuple):
        """Executes a stack of commands in pipeline."""
        pass

    @abstractmethod
    def execute_transaction(
        self, transaction: Callable[[Pipeline], None], *watches, **options
    ):
        """Executes a transaction block wrapped in callback."""
        pass

    @abstractmethod
    def execute_pubsub_method(self, method_name: str, *args, **kwargs):
        """Executes a given method on active pub/sub."""
        pass

    @abstractmethod
    def execute_pubsub_run(self, sleep_time: float, **kwargs) -> Any:
        """Executes pub/sub run in a thread."""
        pass


class DefaultCommandExecutor(SyncCommandExecutor, BaseCommandExecutor):
    def __init__(
        self,
        failure_detectors: List[FailureDetector],
        databases: Databases,
        command_retry: Retry,
        failover_strategy: FailoverStrategy,
        event_dispatcher: EventDispatcherInterface,
        failover_attempts: int = DEFAULT_FAILOVER_ATTEMPTS,
        failover_delay: float = DEFAULT_FAILOVER_DELAY,
        auto_fallback_interval: float = DEFAULT_AUTO_FALLBACK_INTERVAL,
    ):
        """
        Initialize the DefaultCommandExecutor instance.

        Args:
            failure_detectors: List of failure detector instances to monitor database health
            databases: Collection of available databases to execute commands on
            command_retry: Retry policy for failed command execution
            failover_strategy: Strategy for handling database failover
            event_dispatcher: Interface for dispatching events
            failover_attempts: Number of failover attempts
            failover_delay: Delay between failover attempts
            auto_fallback_interval: Time interval in seconds between attempts to fall back to a primary database
        """
        super().__init__(auto_fallback_interval)

        for fd in failure_detectors:
            fd.set_command_executor(command_executor=self)

        self._databases = databases
        self._failure_detectors = failure_detectors
        self._command_retry = command_retry
        self._failover_strategy_executor = DefaultFailoverStrategyExecutor(
            failover_strategy, failover_attempts, failover_delay
        )
        self._event_dispatcher = event_dispatcher
        self._active_database: Optional[Database] = None
        self._active_pubsub: Optional[PubSub] = None
        self._active_pubsub_kwargs = {}
        self._setup_event_dispatcher()
        self._schedule_next_fallback()

    @property
    def databases(self) -> Databases:
        return self._databases

    @property
    def failure_detectors(self) -> List[FailureDetector]:
        return self._failure_detectors

    def add_failure_detector(self, failure_detector: FailureDetector) -> None:
        self._failure_detectors.append(failure_detector)

    @property
    def command_retry(self) -> Retry:
        return self._command_retry

    @property
    def active_database(self) -> Optional[SyncDatabase]:
        return self._active_database

    @active_database.setter
    def active_database(self, value: Tuple[SyncDatabase, GeoFailoverReason]) -> None:
        database, reason = value
        old_active = self._active_database
        self._active_database = database

        if old_active is not None and old_active is not database:
            record_geo_failover(
                fail_from=old_active,
                fail_to=database,
                reason=reason,
            )
            self._event_dispatcher.dispatch(
                ActiveDatabaseChanged(
                    old_active,
                    self._active_database,
                    self,
                    **self._active_pubsub_kwargs,
                )
            )

    @property
    def active_pubsub(self) -> Optional[PubSub]:
        return self._active_pubsub

    @active_pubsub.setter
    def active_pubsub(self, pubsub: PubSub) -> None:
        self._active_pubsub = pubsub

    @property
    def failover_strategy_executor(self) -> FailoverStrategyExecutor:
        return self._failover_strategy_executor

    def execute_command(self, *args, **options):
        def callback():
            response = self._active_database.client.execute_command(*args, **options)
            self._register_command_execution(args)
            return response

        return self._execute_with_failure_detection(callback, args)

    def execute_pipeline(self, command_stack: tuple):
        def callback():
            with self._active_database.client.pipeline() as pipe:
                for command, options in command_stack:
                    pipe.execute_command(*command, **options)

                response = pipe.execute()
                self._register_command_execution(command_stack)
                return response

        return self._execute_with_failure_detection(callback, command_stack)

    def execute_transaction(
        self, transaction: Callable[[Pipeline], None], *watches, **options
    ):
        def callback():
            response = self._active_database.client.transaction(
                transaction, *watches, **options
            )
            self._register_command_execution(())
            return response

        return self._execute_with_failure_detection(callback)

    def pubsub(self, **kwargs):
        def callback():
            if self._active_pubsub is None:
                self._active_pubsub = self._active_database.client.pubsub(**kwargs)
                self._active_pubsub_kwargs = kwargs
            return None

        return self._execute_with_failure_detection(callback)

    def execute_pubsub_method(self, method_name: str, *args, **kwargs):
        def callback():
            method = getattr(self.active_pubsub, method_name)
            response = method(*args, **kwargs)
            self._register_command_execution(args)
            return response

        return self._execute_with_failure_detection(callback, *args)

    def execute_pubsub_run(self, sleep_time, **kwargs) -> "PubSubWorkerThread":
        def callback():
            return self._active_pubsub.run_in_thread(sleep_time, **kwargs)

        return self._execute_with_failure_detection(callback)

    def _execute_with_failure_detection(self, callback: Callable, cmds: tuple = ()):
        """
        Execute a commands execution callback with failure detection.
        """

        def wrapper():
            # On each retry we need to check active database as it might change.
            self._check_active_database()
            return callback()

        return self._command_retry.call_with_retry(
            lambda: wrapper(),
            lambda error: self._on_command_fail(error, *cmds),
        )

    def _on_command_fail(self, error, *args):
        self._event_dispatcher.dispatch(OnCommandsFailEvent(args, error))

    def _check_active_database(self):
        """
        Checks if active a database needs to be updated.
        """
        if (
            self._active_database is None
            or self._active_database.circuit.state != CBState.CLOSED
            or (
                self._auto_fallback_interval > 0
                and self._next_fallback_attempt <= datetime.now()
            )
        ):
            self.active_database = (
                self._failover_strategy_executor.execute(),
                GeoFailoverReason.AUTOMATIC,
            )
            self._schedule_next_fallback()

    def _register_command_execution(self, cmd: tuple):
        for detector in self._failure_detectors:
            detector.register_command_execution(cmd)

    def _setup_event_dispatcher(self):
        """
        Registers necessary listeners.
        """
        failure_listener = RegisterCommandFailure(self._failure_detectors)
        resubscribe_listener = ResubscribeOnActiveDatabaseChanged()
        close_connection_listener = CloseConnectionOnActiveDatabaseChanged()
        self._event_dispatcher.register_listeners(
            {
                OnCommandsFailEvent: [failure_listener],
                ActiveDatabaseChanged: [
                    close_connection_listener,
                    resubscribe_listener,
                ],
            }
        )
