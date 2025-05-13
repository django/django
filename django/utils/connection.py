from abc import ABC, abstractmethod
import asyncio

from asgiref.local import Local

from django.conf import settings as django_settings
from django.utils.functional import cached_property


class ConnectionProxy:
    """Proxy for accessing a connection object's attributes."""

    def __init__(self, connections, alias):
        self.__dict__["_connections"] = connections
        self.__dict__["_alias"] = alias

    def __getattr__(self, item):
        return getattr(self._connections[self._alias], item)

    def __setattr__(self, name, value):
        return setattr(self._connections[self._alias], name, value)

    def __delattr__(self, name):
        return delattr(self._connections[self._alias], name)

    def __contains__(self, key):
        return key in self._connections[self._alias]

    def __eq__(self, other):
        return self._connections[self._alias] == other


class ConnectionDoesNotExist(Exception):
    pass


class StackLocal:
    def __init__(self):
        self._store = Local()

    def _stack_for(self, key):
        try:
            return getattr(self._store, key)
        except AttributeError:
            stack = []
            setattr(self._store, key, stack)
            return stack

    def __getattr__(self, key):
        stack = self._stack_for(key)

        if stack:
            return stack[-1]

        raise AttributeError(
            f"'{self.__class__.__name__}' object has no attribute '{key}'"
        )

    def __setattr__(self, key, value):
        if key == "_store":
            return super().__setattr__(key, value)

        setattr(self._store, key, self._stack_for(key) + [value])

    def __delattr__(self, key):
        stack = self._stack_for(key)

        if not stack:
            raise AttributeError(
                f"'{self.__class__.__name__}' object has no attribute '{key}'"
            )

        setattr(self._store, key, stack[:-1])


class AbstractConnectionHandler(ABC):
    settings_name = None
    exception_class = ConnectionDoesNotExist

    def __init__(self, settings=None):
        self._settings = settings
        self._connections = self.create_local_storage()

    @abstractmethod
    def create_local_storage(self):
        pass

    @cached_property
    def settings(self):
        self._settings = self.configure_settings(self._settings)
        return self._settings

    def configure_settings(self, settings):
        if settings is None:
            settings = getattr(django_settings, self.settings_name)
        return settings

    @abstractmethod
    def create_connection(self, alias):
        raise NotImplementedError("Subclasses must implement create_connection().")

    def __getitem__(self, alias):
        try:
            return getattr(self._connections, alias)
        except AttributeError:
            if alias not in self.settings:
                raise self.exception_class(f"The connection '{alias}' doesn't exist.")
        conn = self.create_connection(alias)
        setattr(self._connections, alias, conn)
        return conn

    def __setitem__(self, key, value):
        setattr(self._connections, key, value)

    def __delitem__(self, key):
        delattr(self._connections, key)

    def __iter__(self):
        return iter(self.settings)

    def all(self, initialized_only=False):
        return [
            self[alias]
            for alias in self
            # If initialized_only is True, return only initialized connections.
            if not initialized_only or hasattr(self._connections, alias)
        ]


class BaseConnectionHandler(AbstractConnectionHandler):
    thread_critical = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        for conn in self.all(initialized_only=True):
            conn.close_if_unusable_or_obsolete()

    def create_local_storage(self):
        return Local(thread_critical=self.thread_critical)

    def close_all(self):
        for conn in self.all(initialized_only=True):
            conn.close()


class BaseAsyncConnectionHandler(AbstractConnectionHandler):

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await asyncio.gather(*[
            conn.close_if_unusable_or_obsolete()
            for conn in self.all(initialized_only=True)
        ])

    def create_local_storage(self):
        return StackLocal()

    async def close_all(self):
        await asyncio.gather(*[
            conn.close()
            for conn in self.all(initialized_only=True)
        ])
