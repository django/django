import os

from django.core import signals
from django.db.utils import (
    DEFAULT_DB_ALIAS,
    DJANGO_VERSION_PICKLE_KEY,
    ConnectionHandler,
    ConnectionRouter,
    DatabaseError,
    DataError,
    Error,
    IntegrityError,
    InterfaceError,
    InternalError,
    NotSupportedError,
    OperationalError,
    ProgrammingError,
)
from django.utils.connection import ConnectionProxy

__all__ = [
    "close_old_connections",
    "connection",
    "connections",
    "reset_queries",
    "router",
    "DatabaseError",
    "IntegrityError",
    "InternalError",
    "ProgrammingError",
    "DataError",
    "NotSupportedError",
    "Error",
    "InterfaceError",
    "OperationalError",
    "DEFAULT_DB_ALIAS",
    "DJANGO_VERSION_PICKLE_KEY",
]

connections = ConnectionHandler()

router = ConnectionRouter()

# For backwards compatibility. Prefer connections['default'] instead.
connection = ConnectionProxy(connections, DEFAULT_DB_ALIAS)


# Register an event to reset saved queries when a Django request is started.
def reset_queries(**kwargs):
    for conn in connections.all(initialized_only=True):
        conn.queries_log.clear()


signals.request_started.connect(reset_queries)


# Register an event to reset transaction state and close connections past
# their lifetime.
def close_old_connections(**kwargs):
    for conn in connections.all(initialized_only=True):
        conn.close_if_unusable_or_obsolete()


signals.request_started.connect(close_old_connections)
signals.request_finished.connect(close_old_connections)


# After fork, the child inherits the parent's DB connection objects. The
# underlying sockets/FDs are shared with the parent, so using them from both
# processes corrupts the communication.
def _reset_connections_after_fork():
    for conn in connections.all(initialized_only=True):
        pool_dict = getattr(type(conn), "_connection_pools", None)
        if pool_dict is not None:
            pool_dict.clear()

    for alias in connections:
        try:
            delattr(connections._connections, alias)
        except AttributeError:
            pass


if hasattr(os, "register_at_fork"):
    os.register_at_fork(after_in_child=_reset_connections_after_fork)
