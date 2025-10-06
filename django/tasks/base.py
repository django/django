from dataclasses import dataclass, field, replace
from datetime import datetime
from inspect import isclass, iscoroutinefunction
from typing import Any, Callable, Dict, Optional

from asgiref.sync import async_to_sync, sync_to_async

from django.db.models.enums import TextChoices
from django.utils.json import normalize_json
from django.utils.module_loading import import_string
from django.utils.translation import pgettext_lazy

from .exceptions import TaskResultMismatch

DEFAULT_TASK_BACKEND_ALIAS = "default"
DEFAULT_TASK_PRIORITY = 0
DEFAULT_TASK_QUEUE_NAME = "default"
TASK_MAX_PRIORITY = 100
TASK_MIN_PRIORITY = -100
TASK_REFRESH_ATTRS = {
    "errors",
    "_return_value",
    "finished_at",
    "started_at",
    "last_attempted_at",
    "status",
    "enqueued_at",
    "worker_ids",
}


class TaskResultStatus(TextChoices):
    # The Task has just been enqueued, or is ready to be executed again.
    READY = ("READY", pgettext_lazy("Task", "Ready"))
    # The Task is currently running.
    RUNNING = ("RUNNING", pgettext_lazy("Task", "Running"))
    # The Task raised an exception during execution, or was unable to start.
    FAILED = ("FAILED", pgettext_lazy("Task", "Failed"))
    # The Task has finished running successfully.
    SUCCESSFUL = ("SUCCESSFUL", pgettext_lazy("Task", "Successful"))


@dataclass(frozen=True, slots=True, kw_only=True)
class Task:
    priority: int
    func: Callable  # The Task function.
    backend: str
    queue_name: str
    run_after: Optional[datetime]  # The earliest this Task will run.

    # Whether the Task receives the Task context when executed.
    takes_context: bool = False

    def __post_init__(self):
        self.get_backend().validate_task(self)

    @property
    def name(self):
        return self.func.__name__

    def using(
        self,
        *,
        priority=None,
        queue_name=None,
        run_after=None,
        backend=None,
    ):
        """Create a new Task with modified defaults."""

        changes = {}
        if priority is not None:
            changes["priority"] = priority
        if queue_name is not None:
            changes["queue_name"] = queue_name
        if run_after is not None:
            changes["run_after"] = run_after
        if backend is not None:
            changes["backend"] = backend
        return replace(self, **changes)

    def enqueue(self, *args, **kwargs):
        """Queue up the Task to be executed."""
        return self.get_backend().enqueue(self, args, kwargs)

    async def aenqueue(self, *args, **kwargs):
        """Queue up the Task to be executed."""
        return await self.get_backend().aenqueue(self, args, kwargs)

    def get_result(self, result_id):
        """
        Retrieve a task result by id.

        Raise TaskResultDoesNotExist if such result does not exist, or raise
        TaskResultMismatch if the result exists but belongs to another Task.
        """
        result = self.get_backend().get_result(result_id)
        if result.task.func != self.func:
            raise TaskResultMismatch(
                f"Task does not match (received {result.task.module_path!r})"
            )
        return result

    async def aget_result(self, result_id):
        """See get_result()."""
        result = await self.get_backend().aget_result(result_id)
        if result.task.func != self.func:
            raise TaskResultMismatch(
                f"Task does not match (received {result.task.module_path!r})"
            )
        return result

    def call(self, *args, **kwargs):
        if iscoroutinefunction(self.func):
            return async_to_sync(self.func)(*args, **kwargs)
        return self.func(*args, **kwargs)

    async def acall(self, *args, **kwargs):
        if iscoroutinefunction(self.func):
            return await self.func(*args, **kwargs)
        return await sync_to_async(self.func)(*args, **kwargs)

    def get_backend(self):
        from . import task_backends

        return task_backends[self.backend]

    @property
    def module_path(self):
        return f"{self.func.__module__}.{self.func.__qualname__}"


def task(
    function=None,
    *,
    priority=DEFAULT_TASK_PRIORITY,
    queue_name=DEFAULT_TASK_QUEUE_NAME,
    backend=DEFAULT_TASK_BACKEND_ALIAS,
    takes_context=False,
):
    from . import task_backends

    def wrapper(f):
        return task_backends[backend].task_class(
            priority=priority,
            func=f,
            queue_name=queue_name,
            backend=backend,
            takes_context=takes_context,
            run_after=None,
        )

    if function:
        return wrapper(function)
    return wrapper


@dataclass(frozen=True, slots=True, kw_only=True)
class TaskError:
    exception_class_path: str
    traceback: str

    @property
    def exception_class(self):
        # Lazy resolve the exception class.
        exception_class = import_string(self.exception_class_path)

        if not isclass(exception_class) or not issubclass(
            exception_class, BaseException
        ):
            raise ValueError(
                f"{self.exception_class_path!r} does not reference a valid exception."
            )
        return exception_class


@dataclass(frozen=True, slots=True, kw_only=True)
class TaskResult:
    task: Task

    id: str  # Unique identifier for the task result.
    status: TaskResultStatus
    enqueued_at: Optional[datetime]  # Time the task was enqueued.
    started_at: Optional[datetime]  # Time the task was started.
    finished_at: Optional[datetime]  # Time the task was finished.

    # Time the task was last attempted to be run.
    last_attempted_at: Optional[datetime]

    args: list  # Arguments to pass to the task function.
    kwargs: Dict[str, Any]  # Keyword arguments to pass to the task function.
    backend: str
    errors: list[TaskError]  # Errors raised when running the task.
    worker_ids: list[str]  # Workers which have processed the task.

    _return_value: Optional[Any] = field(init=False, default=None)

    def __post_init__(self):
        object.__setattr__(self, "args", normalize_json(self.args))
        object.__setattr__(self, "kwargs", normalize_json(self.kwargs))

    @property
    def return_value(self):
        """
        The return value of the task.

        If the task didn't succeed, an exception is raised.
        This is to distinguish against the task returning None.
        """
        if self.status == TaskResultStatus.SUCCESSFUL:
            return self._return_value
        elif self.status == TaskResultStatus.FAILED:
            raise ValueError("Task failed")
        else:
            raise ValueError("Task has not finished yet")

    @property
    def is_finished(self):
        return self.status in {TaskResultStatus.FAILED, TaskResultStatus.SUCCESSFUL}

    @property
    def attempts(self):
        return len(self.worker_ids)

    def refresh(self):
        """Reload the cached task data from the task store."""
        refreshed_task = self.task.get_backend().get_result(self.id)

        for attr in TASK_REFRESH_ATTRS:
            object.__setattr__(self, attr, getattr(refreshed_task, attr))

    async def arefresh(self):
        """
        Reload the cached task data from the task store
        """
        refreshed_task = await self.task.get_backend().aget_result(self.id)
        for attr in TASK_REFRESH_ATTRS:
            object.__setattr__(self, attr, getattr(refreshed_task, attr))


@dataclass(frozen=True, slots=True, kw_only=True)
class TaskContext:
    task_result: TaskResult

    @property
    def attempt(self):
        return self.task_result.attempts
