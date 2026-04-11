import asyncio
import logging
from typing import Any, Awaitable, Callable, List, Optional, Union

from redis.asyncio.client import PubSubHandler
from redis.asyncio.multidb.command_executor import DefaultCommandExecutor
from redis.asyncio.multidb.config import (
    DEFAULT_GRACE_PERIOD,
    DatabaseConfig,
    InitialHealthCheck,
    MultiDbConfig,
)
from redis.asyncio.multidb.database import AsyncDatabase, Database, Databases
from redis.asyncio.multidb.failure_detector import AsyncFailureDetector
from redis.asyncio.multidb.healthcheck import HealthCheck, HealthCheckPolicy
from redis.asyncio.retry import Retry
from redis.background import BackgroundScheduler
from redis.backoff import NoBackoff
from redis.commands import AsyncCoreCommands, AsyncRedisModuleCommands
from redis.multidb.circuit import CircuitBreaker
from redis.multidb.circuit import State as CBState
from redis.multidb.exception import (
    InitialHealthCheckFailedError,
    NoValidDatabaseException,
    UnhealthyDatabaseException,
)
from redis.typing import ChannelT, EncodableT, KeyT
from redis.utils import experimental

logger = logging.getLogger(__name__)


@experimental
class MultiDBClient(AsyncRedisModuleCommands, AsyncCoreCommands):
    """
    Client that operates on multiple logical Redis databases.
    Should be used in Client-side geographic failover database setups.
    """

    def __init__(self, config: MultiDbConfig):
        self._databases = config.databases()
        self._health_checks = (
            config.default_health_checks()
            if not config.health_checks
            else config.health_checks
        )

        self._health_check_interval = config.health_check_interval
        self._health_check_policy: HealthCheckPolicy = config.health_check_policy.value(
            config.health_check_probes, config.health_check_delay
        )
        self._failure_detectors = (
            config.default_failure_detectors()
            if not config.failure_detectors
            else config.failure_detectors
        )

        self._failover_strategy = (
            config.default_failover_strategy()
            if config.failover_strategy is None
            else config.failover_strategy
        )
        self._failover_strategy.set_databases(self._databases)
        self._auto_fallback_interval = config.auto_fallback_interval
        self._event_dispatcher = config.event_dispatcher
        self._command_retry = config.command_retry
        self._command_retry.update_supported_errors([ConnectionRefusedError])
        self.command_executor = DefaultCommandExecutor(
            failure_detectors=self._failure_detectors,
            databases=self._databases,
            command_retry=self._command_retry,
            failover_strategy=self._failover_strategy,
            failover_attempts=config.failover_attempts,
            failover_delay=config.failover_delay,
            event_dispatcher=self._event_dispatcher,
            auto_fallback_interval=self._auto_fallback_interval,
        )
        self.initialized = False
        self._hc_lock = asyncio.Lock()
        self._bg_scheduler = BackgroundScheduler()
        self._config = config
        self._recurring_hc_task = None
        self._hc_tasks = []
        self._half_open_state_task = None

    async def __aenter__(self: "MultiDBClient") -> "MultiDBClient":
        if not self.initialized:
            await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        if self._recurring_hc_task:
            self._recurring_hc_task.cancel()
        if self._half_open_state_task:
            self._half_open_state_task.cancel()
        for hc_task in self._hc_tasks:
            hc_task.cancel()

    async def initialize(self):
        """
        Perform initialization of databases to define their initial state.
        """

        # Initial databases check to define initial state
        await self._perform_initial_health_check()

        # Starts recurring health checks on the background.
        self._recurring_hc_task = asyncio.create_task(
            self._bg_scheduler.run_recurring_async(
                self._health_check_interval,
                self._check_databases_health,
            )
        )

        is_active_db_found = False

        for database, weight in self._databases:
            # Set on state changed callback for each circuit.
            database.circuit.on_state_changed(self._on_circuit_state_change_callback)

            # Set states according to a weights and circuit state
            if database.circuit.state == CBState.CLOSED and not is_active_db_found:
                # Directly set the active database during initialization
                # without recording a geo failover metric
                self.command_executor._active_database = database
                is_active_db_found = True

        if not is_active_db_found:
            raise NoValidDatabaseException(
                "Initial connection failed - no active database found"
            )

        self.initialized = True

    def get_databases(self) -> Databases:
        """
        Returns a sorted (by weight) list of all databases.
        """
        return self._databases

    async def set_active_database(self, database: AsyncDatabase) -> None:
        """
        Promote one of the existing databases to become an active.
        """
        exists = None

        for existing_db, _ in self._databases:
            if existing_db == database:
                exists = True
                break

        if not exists:
            raise ValueError("Given database is not a member of database list")

        await self._check_db_health(database)

        if database.circuit.state == CBState.CLOSED:
            highest_weighted_db, _ = self._databases.get_top_n(1)[0]
            await self.command_executor.set_active_database(database)
            return

        raise NoValidDatabaseException(
            "Cannot set active database, database is unhealthy"
        )

    async def add_database(
        self, config: DatabaseConfig, skip_initial_health_check: bool = True
    ):
        """
        Adds a new database to the database list.

        Args:
            config: DatabaseConfig object that contains the database configuration.
            skip_initial_health_check: If True, adds the database even if it is unhealthy.
        """
        # The retry object is not used in the lower level clients, so we can safely remove it.
        # We rely on command_retry in terms of global retries.
        config.client_kwargs.update({"retry": Retry(retries=0, backoff=NoBackoff())})

        if config.from_url:
            client = self._config.client_class.from_url(
                config.from_url, **config.client_kwargs
            )
        elif config.from_pool:
            config.from_pool.set_retry(Retry(retries=0, backoff=NoBackoff()))
            client = self._config.client_class.from_pool(
                connection_pool=config.from_pool
            )
        else:
            client = self._config.client_class(**config.client_kwargs)

        circuit = (
            config.default_circuit_breaker()
            if config.circuit is None
            else config.circuit
        )

        database = Database(
            client=client,
            circuit=circuit,
            weight=config.weight,
            health_check_url=config.health_check_url,
        )

        try:
            await self._check_db_health(database)
        except UnhealthyDatabaseException:
            if not skip_initial_health_check:
                raise

        highest_weighted_db, highest_weight = self._databases.get_top_n(1)[0]
        self._databases.add(database, database.weight)
        await self._change_active_database(database, highest_weighted_db)

    async def _change_active_database(
        self, new_database: AsyncDatabase, highest_weight_database: AsyncDatabase
    ):
        if (
            new_database.weight > highest_weight_database.weight
            and new_database.circuit.state == CBState.CLOSED
        ):
            await self.command_executor.set_active_database(new_database)

    async def remove_database(self, database: AsyncDatabase):
        """
        Removes a database from the database list.
        """
        weight = self._databases.remove(database)
        highest_weighted_db, highest_weight = self._databases.get_top_n(1)[0]

        if (
            highest_weight <= weight
            and highest_weighted_db.circuit.state == CBState.CLOSED
        ):
            await self.command_executor.set_active_database(highest_weighted_db)

    async def update_database_weight(self, database: AsyncDatabase, weight: float):
        """
        Updates a database from the database list.
        """
        exists = None

        for existing_db, _ in self._databases:
            if existing_db == database:
                exists = True
                break

        if not exists:
            raise ValueError("Given database is not a member of database list")

        highest_weighted_db, highest_weight = self._databases.get_top_n(1)[0]
        self._databases.update_weight(database, weight)
        database.weight = weight
        await self._change_active_database(database, highest_weighted_db)

    def add_failure_detector(self, failure_detector: AsyncFailureDetector):
        """
        Adds a new failure detector to the database.
        """
        self._failure_detectors.append(failure_detector)

    async def add_health_check(self, healthcheck: HealthCheck):
        """
        Adds a new health check to the database.
        """
        async with self._hc_lock:
            self._health_checks.append(healthcheck)

    async def execute_command(self, *args, **options):
        """
        Executes a single command and return its result.
        """
        if not self.initialized:
            await self.initialize()

        return await self.command_executor.execute_command(*args, **options)

    def pipeline(self):
        """
        Enters into pipeline mode of the client.
        """
        return Pipeline(self)

    async def transaction(
        self,
        func: Callable[["Pipeline"], Union[Any, Awaitable[Any]]],
        *watches: KeyT,
        shard_hint: Optional[str] = None,
        value_from_callable: bool = False,
        watch_delay: Optional[float] = None,
    ):
        """
        Executes callable as transaction.
        """
        if not self.initialized:
            await self.initialize()

        return await self.command_executor.execute_transaction(
            func,
            *watches,
            shard_hint=shard_hint,
            value_from_callable=value_from_callable,
            watch_delay=watch_delay,
        )

    async def pubsub(self, **kwargs):
        """
        Return a Publish/Subscribe object. With this object, you can
        subscribe to channels and listen for messages that get published to
        them.
        """
        if not self.initialized:
            await self.initialize()

        return PubSub(self, **kwargs)

    async def _check_databases_health(self) -> dict[Database, bool]:
        """
        Runs health checks as a recurring task.
        Runs health checks against all databases.
        """
        try:
            task_to_db: dict[asyncio.Task, Database] = {}

            self._hc_tasks = []
            for database, _ in self._databases:
                task = asyncio.create_task(self._check_db_health(database))
                task_to_db[task] = database
                self._hc_tasks.append(task)

            results = await asyncio.wait_for(
                asyncio.gather(*self._hc_tasks, return_exceptions=True),
                timeout=self._health_check_interval,
            )
        except asyncio.TimeoutError:
            raise asyncio.TimeoutError(
                "Health check execution exceeds health_check_interval"
            )

        # Map end results to databases
        db_results = {
            task_to_db[task]: result for task, result in zip(self._hc_tasks, results)
        }

        for database, result in db_results.items():
            if isinstance(result, UnhealthyDatabaseException):
                unhealthy_db = result.database
                unhealthy_db.circuit.state = CBState.OPEN

                logger.debug(
                    "Health check failed, due to exception",
                    exc_info=result.original_exception,
                )

                db_results[unhealthy_db] = False
            elif isinstance(result, Exception):
                db_results[database] = False

        return db_results

    async def _perform_initial_health_check(self):
        """
        Runs initial health check and evaluate healthiness based on initial_health_check_policy.
        """
        results = await self._check_databases_health()
        is_healthy = True

        if self._config.initial_health_check_policy == InitialHealthCheck.ALL_AVAILABLE:
            is_healthy = False not in results.values()
        elif (
            self._config.initial_health_check_policy
            == InitialHealthCheck.MAJORITY_AVAILABLE
        ):
            is_healthy = sum(results.values()) > len(results) / 2
        elif (
            self._config.initial_health_check_policy == InitialHealthCheck.ONE_AVAILABLE
        ):
            is_healthy = True in results.values()

        if not is_healthy:
            raise InitialHealthCheckFailedError(
                f"Initial health check failed. Initial health check policy: {self._config.initial_health_check_policy}"
            )

    async def _check_db_health(self, database: AsyncDatabase) -> bool:
        """
        Runs health checks on the given database until first failure.
        """
        # Health check will setup circuit state
        is_healthy = await self._health_check_policy.execute(
            self._health_checks, database
        )

        if not is_healthy:
            if database.circuit.state != CBState.OPEN:
                database.circuit.state = CBState.OPEN
            return is_healthy
        elif is_healthy and database.circuit.state != CBState.CLOSED:
            database.circuit.state = CBState.CLOSED

        return is_healthy

    def _on_circuit_state_change_callback(
        self, circuit: CircuitBreaker, old_state: CBState, new_state: CBState
    ):
        loop = asyncio.get_running_loop()

        if new_state == CBState.HALF_OPEN:
            self._half_open_state_task = asyncio.create_task(
                self._check_db_health(circuit.database)
            )
            return

        if old_state == CBState.CLOSED and new_state == CBState.OPEN:
            logger.warning(
                f"Database {circuit.database} is unreachable. Failover has been initiated."
            )
            loop.call_later(DEFAULT_GRACE_PERIOD, _half_open_circuit, circuit)

        if old_state != CBState.CLOSED and new_state == CBState.CLOSED:
            logger.info(f"Database {circuit.database} is reachable again.")

    async def aclose(self):
        if self.command_executor.active_database:
            await self.command_executor.active_database.client.aclose()


def _half_open_circuit(circuit: CircuitBreaker):
    circuit.state = CBState.HALF_OPEN


class Pipeline(AsyncRedisModuleCommands, AsyncCoreCommands):
    """
    Pipeline implementation for multiple logical Redis databases.
    """

    def __init__(self, client: MultiDBClient):
        self._command_stack = []
        self._client = client

    async def __aenter__(self: "Pipeline") -> "Pipeline":
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.reset()
        await self._client.__aexit__(exc_type, exc_value, traceback)

    def __await__(self):
        return self._async_self().__await__()

    async def _async_self(self):
        return self

    def __len__(self) -> int:
        return len(self._command_stack)

    def __bool__(self) -> bool:
        """Pipeline instances should always evaluate to True"""
        return True

    async def reset(self) -> None:
        self._command_stack = []

    async def aclose(self) -> None:
        """Close the pipeline"""
        await self.reset()

    def pipeline_execute_command(self, *args, **options) -> "Pipeline":
        """
        Stage a command to be executed when execute() is next called

        Returns the current Pipeline object back so commands can be
        chained together, such as:

        pipe = pipe.set('foo', 'bar').incr('baz').decr('bang')

        At some other point, you can then run: pipe.execute(),
        which will execute all commands queued in the pipe.
        """
        self._command_stack.append((args, options))
        return self

    def execute_command(self, *args, **kwargs):
        """Adds a command to the stack"""
        return self.pipeline_execute_command(*args, **kwargs)

    async def execute(self) -> List[Any]:
        """Execute all the commands in the current pipeline"""
        if not self._client.initialized:
            await self._client.initialize()

        try:
            return await self._client.command_executor.execute_pipeline(
                tuple(self._command_stack)
            )
        finally:
            await self.reset()


class PubSub:
    """
    PubSub object for multi database client.
    """

    def __init__(self, client: MultiDBClient, **kwargs):
        """Initialize the PubSub object for a multi-database client.

        Args:
            client: MultiDBClient instance to use for pub/sub operations
            **kwargs: Additional keyword arguments to pass to the underlying pubsub implementation
        """

        self._client = client
        self._client.command_executor.pubsub(**kwargs)

    async def __aenter__(self) -> "PubSub":
        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        await self.aclose()

    async def aclose(self):
        return await self._client.command_executor.execute_pubsub_method("aclose")

    @property
    def subscribed(self) -> bool:
        return self._client.command_executor.active_pubsub.subscribed

    async def execute_command(self, *args: EncodableT):
        return await self._client.command_executor.execute_pubsub_method(
            "execute_command", *args
        )

    async def psubscribe(self, *args: ChannelT, **kwargs: PubSubHandler):
        """
        Subscribe to channel patterns. Patterns supplied as keyword arguments
        expect a pattern name as the key and a callable as the value. A
        pattern's callable will be invoked automatically when a message is
        received on that pattern rather than producing a message via
        ``listen()``.
        """
        return await self._client.command_executor.execute_pubsub_method(
            "psubscribe", *args, **kwargs
        )

    async def punsubscribe(self, *args: ChannelT):
        """
        Unsubscribe from the supplied patterns. If empty, unsubscribe from
        all patterns.
        """
        return await self._client.command_executor.execute_pubsub_method(
            "punsubscribe", *args
        )

    async def subscribe(self, *args: ChannelT, **kwargs: Callable):
        """
        Subscribe to channels. Channels supplied as keyword arguments expect
        a channel name as the key and a callable as the value. A channel's
        callable will be invoked automatically when a message is received on
        that channel rather than producing a message via ``listen()`` or
        ``get_message()``.
        """
        return await self._client.command_executor.execute_pubsub_method(
            "subscribe", *args, **kwargs
        )

    async def unsubscribe(self, *args):
        """
        Unsubscribe from the supplied channels. If empty, unsubscribe from
        all channels
        """
        return await self._client.command_executor.execute_pubsub_method(
            "unsubscribe", *args
        )

    async def get_message(
        self, ignore_subscribe_messages: bool = False, timeout: Optional[float] = 0.0
    ):
        """
        Get the next message if one is available, otherwise None.

        If timeout is specified, the system will wait for `timeout` seconds
        before returning. Timeout should be specified as a floating point
        number or None to wait indefinitely.
        """
        return await self._client.command_executor.execute_pubsub_method(
            "get_message",
            ignore_subscribe_messages=ignore_subscribe_messages,
            timeout=timeout,
        )

    async def run(
        self,
        *,
        exception_handler=None,
        poll_timeout: float = 1.0,
    ) -> None:
        """Process pub/sub messages using registered callbacks.

        This is the equivalent of :py:meth:`redis.PubSub.run_in_thread` in
        redis-py, but it is a coroutine. To launch it as a separate task, use
        ``asyncio.create_task``:

            >>> task = asyncio.create_task(pubsub.run())

        To shut it down, use asyncio cancellation:

            >>> task.cancel()
            >>> await task
        """
        return await self._client.command_executor.execute_pubsub_run(
            sleep_time=poll_timeout, exception_handler=exception_handler, pubsub=self
        )
