from abc import ABCMeta, abstractmethod
from inspect import iscoroutinefunction

from asgiref.sync import sync_to_async

from django.core.checks import messages
from django.db import connections
from django.tasks import DEFAULT_QUEUE_NAME
from django.tasks.exceptions import InvalidTaskError
from django.tasks.task import MAX_PRIORITY, MIN_PRIORITY, Task
from django.tasks.utils import is_module_level_function
from django.utils import timezone


class BaseTaskBackend(metaclass=ABCMeta):
    task_class = Task

    supports_defer = False
    """Can tasks be enqueued with the run_after attribute"""

    supports_async_task = False
    """Can coroutines be enqueued"""

    supports_get_result = False
    """Can results be retrieved after the fact (from **any** thread / process)"""

    def __init__(self, alias, params):
        self.alias = alias
        self.queues = set(params.get("QUEUES", [DEFAULT_QUEUE_NAME]))
        self.enqueue_on_commit = bool(params.get("ENQUEUE_ON_COMMIT", True))

    def _get_enqueue_on_commit_for_task(self, task):
        """
        Determine the correct `enqueue_on_commit` setting to use for a given task.

        If the task defines it, use that, otherwise, fall back to the backend.
        """
        # If the task defines it, use that, otherwise, fall back to the backend.
        return (
            task.enqueue_on_commit
            if task.enqueue_on_commit is not None
            else self.enqueue_on_commit
        )

    def validate_task(self, task):
        """
        Determine whether the provided task is one which can be executed by the backend.
        """
        if not is_module_level_function(task.func):
            raise InvalidTaskError("Task function must be defined at a module level")

        if not self.supports_async_task and iscoroutinefunction(task.func):
            raise InvalidTaskError("Backend does not support async tasks")

        if (
            task.priority < MIN_PRIORITY
            or task.priority > MAX_PRIORITY
            or int(task.priority) != task.priority
        ):
            raise InvalidTaskError(
                f"priority must be a whole number between {MIN_PRIORITY} and "
                f"{MAX_PRIORITY}"
            )

        if not self.supports_defer and task.run_after is not None:
            raise InvalidTaskError("Backend does not support run_after")

        if task.run_after is not None and not timezone.is_aware(task.run_after):
            raise InvalidTaskError("run_after must be an aware datetime")

        if self.queues and task.queue_name not in self.queues:
            raise InvalidTaskError(
                f"Queue '{task.queue_name}' is not valid for backend"
            )

    @abstractmethod
    def enqueue(self, task, args, kwargs):
        """
        Queue up a task to be executed
        """

    async def aenqueue(self, task, args, kwargs):
        """
        Queue up a task function (or coroutine) to be executed
        """
        return await sync_to_async(self.enqueue, thread_sensitive=True)(
            task=task, args=args, kwargs=kwargs
        )

    def get_result(self, result_id):
        """
        Retrieve a result by its id (if one exists).
        If one doesn't, raises ResultDoesNotExist.
        """
        raise NotImplementedError(
            "This backend does not support retrieving or refreshing results."
        )

    async def aget_result(self, result_id):
        """
        Queue up a task function (or coroutine) to be executed
        """
        return await sync_to_async(self.get_result, thread_sensitive=True)(
            result_id=result_id
        )

    def check(self, **kwargs):
        if self.enqueue_on_commit and not connections._settings:
            yield messages.Error(
                "`ENQUEUE_ON_COMMIT` cannot be used when no databases are configured",
                hint="Set `ENQUEUE_ON_COMMIT` to False",
            )
