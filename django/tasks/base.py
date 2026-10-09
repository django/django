from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass, field, fields, replace
from datetime import datetime
from inspect import isclass, iscoroutinefunction
from typing import Any

from asgiref.sync import async_to_sync, sync_to_async

from django.db.models.enums import TextChoices
from django.utils.json import normalize_json
from django.utils.module_loading import import_string, qualname
from django.utils.translation import pgettext_lazy

from .exceptions import TaskResultMismatch

DEFAULT_TASK_BACKEND_ALIAS = "default"
DEFAULT_TASK_PRIORITY = 0
DEFAULT_TASK_QUEUE_NAME = "default"
TASK_MAX_PRIORITY = 100
TASK_MIN_PRIORITY = -100
# Metadata keys starting with this prefix are reserved for backends and
# libraries. They're hidden from users, and preserved when saving metadata.
RESERVED_METADATA_PREFIX = "_"
TASK_REFRESH_ATTRS = {
    "errors",
    "raw_metadata",
    "_return_value",
    "finished_at",
    "started_at",
    "last_attempted_at",
    "status",
    "enqueued_at",
    "worker_ids",
}


def get_user_metadata(raw_metadata):
    """Return a copy of the metadata without reserved keys."""
    return {
        key: value
        for key, value in raw_metadata.items()
        if not key.startswith(RESERVED_METADATA_PREFIX)
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
    func: Callable[..., Any]  # The Task function.
    priority: int = DEFAULT_TASK_PRIORITY
    backend: str = DEFAULT_TASK_BACKEND_ALIAS
    queue_name: str = DEFAULT_TASK_QUEUE_NAME
    run_after: datetime | None = None  # The earliest this Task will run.

    # Whether the Task receives the Task context when executed.
    takes_context: bool = False

    # Additional JSON-compatible data stored alongside the Task.
    metadata: dict[str, Any] = field(default_factory=dict, hash=False)

    def __post_init__(self):
        self.get_backend().validate_task(self)

    @classmethod
    def _reconstruct(cls, kwargs):
        func_path = kwargs["func"]
        try:
            func = import_string(func_path)
            kwargs["func"] = func.func
        except (ImportError, AttributeError) as e:
            msg = f"Expected {func_path!r} to point to a Task instance."
            raise ValueError(msg) from e
        return cls(**kwargs)

    def __reduce__(self):
        kwargs = {f.name: getattr(self, f.name) for f in fields(self)}
        kwargs["func"] = self.module_path

        return (self.__class__._reconstruct, (kwargs,))

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
        metadata=None,
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
        if metadata is not None:
            changes["metadata"] = metadata
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
        return qualname(self.func)


def task(
    function=None,
    *,
    priority=DEFAULT_TASK_PRIORITY,
    queue_name=DEFAULT_TASK_QUEUE_NAME,
    backend=DEFAULT_TASK_BACKEND_ALIAS,
    takes_context=False,
    **kwargs,
):
    from . import task_backends

    if "run_after" in kwargs:
        raise TypeError(
            "run_after cannot be defined statically with the @task decorator. "
            "Use .using(run_after=...) to set it dynamically."
        )

    def wrapper(f):
        return task_backends[backend].task_class(
            func=f,
            priority=priority,
            queue_name=queue_name,
            backend=backend,
            takes_context=takes_context,
            **kwargs,
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
    enqueued_at: datetime | None  # Time the task was enqueued.
    started_at: datetime | None  # Time the task was started.
    finished_at: datetime | None  # Time the task was finished.

    # Time the task was last attempted to be run.
    last_attempted_at: datetime | None

    args: list[Any]  # Arguments to pass to the task function.
    kwargs: dict[str, Any]  # Keyword arguments to pass to the task function.
    backend: str
    errors: list[TaskError]  # Errors raised when running the task.
    worker_ids: list[str]  # Workers which have processed the task.

    # Metadata about the task, including reserved keys.
    raw_metadata: dict[str, Any] = field(default_factory=dict)

    _return_value: Any | None = field(init=False, default=None)

    def __post_init__(self):
        object.__setattr__(self, "args", normalize_json(self.args))
        object.__setattr__(self, "kwargs", normalize_json(self.kwargs))
        object.__setattr__(self, "raw_metadata", normalize_json(self.raw_metadata))

    @property
    def metadata(self):
        """
        A copy of the task's metadata, excluding reserved keys.

        Use TaskContext.metadata to modify metadata from within a task.
        """
        return get_user_metadata(self.raw_metadata)

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

    # A mutable copy of the task's metadata, excluding reserved keys.
    metadata: dict[str, Any] = field(init=False)

    def __post_init__(self):
        object.__setattr__(self, "metadata", deepcopy(self.task_result.metadata))

    @property
    def attempt(self):
        return self.task_result.attempts

    @property
    def metadata_modified(self):
        """Whether metadata has changed since it was last saved."""
        return self.metadata != self.task_result.metadata

    def _get_metadata_to_save(self):
        # Reserved keys can't be modified by users, so retain their existing
        # values.
        raw_metadata = {
            key: value
            for key, value in self.task_result.raw_metadata.items()
            if key.startswith(RESERVED_METADATA_PREFIX)
        }
        raw_metadata.update(get_user_metadata(self.metadata))
        return normalize_json(raw_metadata)

    def save_metadata(self):
        """Persist the task's metadata."""
        raw_metadata = self._get_metadata_to_save()
        self.task_result.task.get_backend().save_metadata(
            self.task_result, raw_metadata
        )
        object.__setattr__(self.task_result, "raw_metadata", raw_metadata)

    async def asave_metadata(self):
        """See save_metadata()."""
        raw_metadata = self._get_metadata_to_save()
        await self.task_result.task.get_backend().asave_metadata(
            self.task_result, raw_metadata
        )
        object.__setattr__(self.task_result, "raw_metadata", raw_metadata)
