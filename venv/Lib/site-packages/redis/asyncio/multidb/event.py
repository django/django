from typing import List

from redis.asyncio import Redis
from redis.asyncio.multidb.database import AsyncDatabase
from redis.asyncio.multidb.failure_detector import AsyncFailureDetector
from redis.event import AsyncEventListenerInterface, AsyncOnCommandsFailEvent


class AsyncActiveDatabaseChanged:
    """
    Event fired when an async active database has been changed.
    """

    def __init__(
        self,
        old_database: AsyncDatabase,
        new_database: AsyncDatabase,
        command_executor,
        **kwargs,
    ):
        self._old_database = old_database
        self._new_database = new_database
        self._command_executor = command_executor
        self._kwargs = kwargs

    @property
    def old_database(self) -> AsyncDatabase:
        return self._old_database

    @property
    def new_database(self) -> AsyncDatabase:
        return self._new_database

    @property
    def command_executor(self):
        return self._command_executor

    @property
    def kwargs(self):
        return self._kwargs


class ResubscribeOnActiveDatabaseChanged(AsyncEventListenerInterface):
    """
    Re-subscribe the currently active pub / sub to a new active database.
    """

    async def listen(self, event: AsyncActiveDatabaseChanged):
        old_pubsub = event.command_executor.active_pubsub

        if old_pubsub is not None:
            # Re-assign old channels and patterns so they will be automatically subscribed on connection.
            new_pubsub = event.new_database.client.pubsub(**event.kwargs)
            new_pubsub.channels = old_pubsub.channels
            new_pubsub.patterns = old_pubsub.patterns
            await new_pubsub.on_connect(None)
            event.command_executor.active_pubsub = new_pubsub
            await old_pubsub.aclose()


class CloseConnectionOnActiveDatabaseChanged(AsyncEventListenerInterface):
    """
    Close connection to the old active database.
    """

    async def listen(self, event: AsyncActiveDatabaseChanged):
        await event.old_database.client.aclose()

        if isinstance(event.old_database.client, Redis):
            await event.old_database.client.connection_pool.update_active_connections_for_reconnect()
            await event.old_database.client.connection_pool.disconnect()


class RegisterCommandFailure(AsyncEventListenerInterface):
    """
    Event listener that registers command failures and passing it to the failure detectors.
    """

    def __init__(self, failure_detectors: List[AsyncFailureDetector]):
        self._failure_detectors = failure_detectors

    async def listen(self, event: AsyncOnCommandsFailEvent) -> None:
        for failure_detector in self._failure_detectors:
            await failure_detector.register_failure(event.exception, event.commands)
