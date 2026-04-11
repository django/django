from abc import abstractmethod
from asyncio import iscoroutinefunction
from datetime import datetime
from typing import Any, Awaitable, Callable, List, Optional, Union

from redis.asyncio import RedisCluster
from redis.asyncio.client import Pipeline, PubSub
from redis.asyncio.multidb.database import AsyncDatabase, Database, Databases
from redis.asyncio.multidb.event import (
    AsyncActiveDatabaseChanged,
    CloseConnectionOnActiveDatabaseChanged,
    RegisterCommandFailure,
    ResubscribeOnActiveDatabaseChanged,
)
from redis.asyncio.multidb.failover import (
    DEFAULT_FAILOVER_ATTEMPTS,
    DEFAULT_FAILOVER_DELAY,
    AsyncFailoverStrategy,
    DefaultFailoverStrategyExecutor,
    FailoverStrategyExecutor,
)
from redis.asyncio.multidb.failure_detector import AsyncFailureDetector
from redis.asyncio.retry import Retry
from redis.event import AsyncOnCommandsFailEvent, EventDispatcherInterface
from redis.multidb.circuit import State as CBState
from redis.multidb.command_executor import BaseCommandExecutor, CommandExecutor
from redis.multidb.config import DEFAULT_AUTO_FALLBACK_INTERVAL
from redis.typing import KeyT


class AsyncCommandExecutor(CommandExecutor):
    @property
    @abstractmethod
    def databases(self) -> Databases:
        """Returns a list of databases."""
        pass

    @property
    @abstractmethod
    def failure_detectors(self) -> List[AsyncFailureDetector]:
        """Returns a list of failure detectors."""
        pass

    @abstractmethod
    def add_failure_detector(self, failure_detector: AsyncFailureDetector) -> None:
        """Adds a new failure detector to the list of failure detectors."""
        pass

    @property
    @abstractmethod
    def active_database(self) -> Optional[AsyncDatabase]:
        """Returns currently active database."""
        pass

    @abstractmethod
    async def set_active_database(self, database: AsyncDatabase) -> None:
        """Sets the currently active database.

        Args:
            database: The new active database.
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
    async def pubsub(self, **kwargs):
        """Initializes a PubSub object on a currently active database"""
        pass

    @abstractmethod
    async def execute_command(self, *args, **options):
        """Executes a command and returns the result."""
        pass

    @abstractmethod
    async def execute_pipeline(self, command_stack: tuple):
        """Executes a stack of commands in pipeline."""
        pass

    @abstractmethod
    async def execute_transaction(
        self, transaction: Callable[[Pipeline], None], *watches, **options
    ):
        """Executes a transaction block wrapped in callback."""
        pass

    @abstractmethod
    async def execute_pubsub_method(self, method_name: str, *args, **kwargs):
        """Executes a given method on active pub/sub."""
        pass

    @abstractmethod
    async def execute_pubsub_run(self, sleep_time: float, **kwargs) -> Any:
        """Executes pub/sub run in a thread."""
        pass


class DefaultCommandExecutor(BaseCommandExecutor, AsyncCommandExecutor):
    def __init__(
        self,
        failure_detectors: List[AsyncFailureDetector],
        databases: Databases,
        command_retry: Retry,
        failover_strategy: AsyncFailoverStrategy,
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
    def failure_detectors(self) -> List[AsyncFailureDetector]:
        return self._failure_detectors

    def add_failure_detector(self, failure_detector: AsyncFailureDetector) -> None:
        self._failure_detectors.append(failure_detector)

    @property
    def active_database(self) -> Optional[AsyncDatabase]:
        return self._active_database

    async def set_active_database(self, database: AsyncDatabase) -> None:
        old_active = self._active_database
        self._active_database = database

        if old_active is not None and old_active is not database:
            await self._event_dispatcher.dispatch_async(
                AsyncActiveDatabaseChanged(
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

    @property
    def command_retry(self) -> Retry:
        return self._command_retry

    def pubsub(self, **kwargs):
        if self._active_pubsub is None:
            if isinstance(self._active_database.client, RedisCluster):
                raise ValueError("PubSub is not supported for RedisCluster")

            self._active_pubsub = self._active_database.client.pubsub(**kwargs)
            self._active_pubsub_kwargs = kwargs

    async def execute_command(self, *args, **options):
        async def callback():
            response = await self._active_database.client.execute_command(
                *args, **options
            )
            await self._register_command_execution(args)
            return response

        return await self._execute_with_failure_detection(callback, args)

    async def execute_pipeline(self, command_stack: tuple):
        async def callback():
            async with self._active_database.client.pipeline() as pipe:
                for command, options in command_stack:
                    pipe.execute_command(*command, **options)

                response = await pipe.execute()
                await self._register_command_execution(command_stack)
                return response

        return await self._execute_with_failure_detection(callback, command_stack)

    async def execute_transaction(
        self,
        func: Callable[["Pipeline"], Union[Any, Awaitable[Any]]],
        *watches: KeyT,
        shard_hint: Optional[str] = None,
        value_from_callable: bool = False,
        watch_delay: Optional[float] = None,
    ):
        async def callback():
            response = await self._active_database.client.transaction(
                func,
                *watches,
                shard_hint=shard_hint,
                value_from_callable=value_from_callable,
                watch_delay=watch_delay,
            )
            await self._register_command_execution(())
            return response

        return await self._execute_with_failure_detection(callback)

    async def execute_pubsub_method(self, method_name: str, *args, **kwargs):
        async def callback():
            method = getattr(self.active_pubsub, method_name)
            if iscoroutinefunction(method):
                response = await method(*args, **kwargs)
            else:
                response = method(*args, **kwargs)

            await self._register_command_execution(args)
            return response

        return await self._execute_with_failure_detection(callback, *args)

    async def execute_pubsub_run(
        self, sleep_time: float, exception_handler=None, pubsub=None
    ) -> Any:
        async def callback():
            return await self._active_pubsub.run(
                poll_timeout=sleep_time,
                exception_handler=exception_handler,
                pubsub=pubsub,
            )

        return await self._execute_with_failure_detection(callback)

    async def _execute_with_failure_detection(
        self, callback: Callable, cmds: tuple = ()
    ):
        """
        Execute a commands execution callback with failure detection.
        """

        async def wrapper():
            # On each retry we need to check active database as it might change.
            await self._check_active_database()
            return await callback()

        return await self._command_retry.call_with_retry(
            lambda: wrapper(),
            lambda error: self._on_command_fail(error, *cmds),
        )

    async def _check_active_database(self):
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
            await self.set_active_database(
                await self._failover_strategy_executor.execute()
            )
            self._schedule_next_fallback()

    async def _on_command_fail(self, error, *args):
        await self._event_dispatcher.dispatch_async(
            AsyncOnCommandsFailEvent(args, error)
        )

    async def _register_command_execution(self, cmd: tuple):
        for detector in self._failure_detectors:
            await detector.register_command_execution(cmd)

    def _setup_event_dispatcher(self):
        """
        Registers necessary listeners.
        """
        failure_listener = RegisterCommandFailure(self._failure_detectors)
        resubscribe_listener = ResubscribeOnActiveDatabaseChanged()
        close_connection_listener = CloseConnectionOnActiveDatabaseChanged()
        self._event_dispatcher.register_listeners(
            {
                AsyncOnCommandsFailEvent: [failure_listener],
                AsyncActiveDatabaseChanged: [
                    close_connection_listener,
                    resubscribe_listener,
                ],
            }
        )
