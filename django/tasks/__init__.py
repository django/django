from django.utils.connection import BaseConnectionHandler, ConnectionProxy
from django.utils.module_loading import import_string

from . import checks, signals  # NOQA
from .base import (
    DEFAULT_TASK_BACKEND_ALIAS,
    DEFAULT_TASK_QUEUE_NAME,
    Task,
    TaskContext,
    TaskResult,
    TaskResultStatus,
    task,
)
from .exceptions import InvalidTaskBackend

__all__ = [
    "DEFAULT_TASK_BACKEND_ALIAS",
    "DEFAULT_TASK_QUEUE_NAME",
    "default_task_backend",
    "task",
    "task_backends",
    "Task",
    "TaskContext",
    "TaskResult",
    "TaskResultStatus",
]


class TaskBackendHandler(BaseConnectionHandler):
    settings_name = "TASKS"
    exception_class = InvalidTaskBackend

    def create_connection(self, alias):
        params = self.settings[alias]
        backend = params["BACKEND"]
        try:
            backend_cls = import_string(backend)
        except ImportError as e:
            raise InvalidTaskBackend(f"Could not find backend '{backend}': {e}") from e
        return backend_cls(alias=alias, params=params)


task_backends = TaskBackendHandler()

default_task_backend = ConnectionProxy(task_backends, DEFAULT_TASK_BACKEND_ALIAS)
