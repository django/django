from django.utils.connection import BaseConnectionHandler, ConnectionProxy
from django.utils.module_loading import import_string

from . import checks, signal_handlers  # noqa
from .exceptions import InvalidTaskBackendError
from .task import (
    DEFAULT_QUEUE_NAME,
    DEFAULT_TASK_BACKEND_ALIAS,
    ResultStatus,
    TaskResult,
    task,
)

__all__ = [
    "tasks",
    "default_task_backend",
    "DEFAULT_TASK_BACKEND_ALIAS",
    "DEFAULT_QUEUE_NAME",
    "task",
    "ResultStatus",
    "TaskResult",
]


class TasksHandler(BaseConnectionHandler):
    settings_name = "TASKS"
    exception_class = InvalidTaskBackendError

    def create_connection(self, alias):
        params = self.settings[alias]

        backend = params["BACKEND"]

        try:
            backend_cls = import_string(backend)
        except ImportError as e:
            raise InvalidTaskBackendError(
                f"Could not find backend '{backend}': {e}"
            ) from e

        return backend_cls({**params, "ALIAS": alias})


tasks = TasksHandler()

default_task_backend = ConnectionProxy(tasks, DEFAULT_TASK_BACKEND_ALIAS)
