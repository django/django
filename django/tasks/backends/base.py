from abc import ABCMeta, abstractmethod
from inspect import iscoroutinefunction

from asgiref.sync import sync_to_async

from django.conf import settings
from django.tasks import DEFAULT_TASK_QUEUE_NAME
from django.tasks.base import (
    DEFAULT_TASK_PRIORITY,
    TASK_MAX_PRIORITY,
    TASK_MIN_PRIORITY,
    Task,
)
from django.tasks.exceptions import InvalidTask
from django.utils import timezone
from django.utils.inspect import get_func_args, is_module_level_function


class BaseTaskBackend(metaclass=ABCMeta):
    task_class = Task

    # Does the backend support Tasks to be enqueued with the run_after
    # attribute?
    supports_defer = False

    # Does the backend support coroutines to be enqueued?
    supports_async_task = False

    # Does the backend support results being retrieved (from any
    # thread/process)?
    supports_get_result = False

    # Does the backend support executing Tasks in a given
    # priority order?
    supports_priority = False

    def __init__(self, alias, params):
        self.alias = alias
        self.queues = set(params.get("QUEUES", [DEFAULT_TASK_QUEUE_NAME]))
        self.options = params.get("OPTIONS", {})

    def validate_task(self, task):
        """
        Determine whether the provided Task can be executed by the backend.
        """
        if not is_module_level_function(task.func):
            raise InvalidTask("Task function must be defined at a module level.")

        if not self.supports_async_task and iscoroutinefunction(task.func):
            raise InvalidTask("Backend does not support async Tasks.")

        task_func_args = get_func_args(task.func)
        if task.takes_context and (
            not task_func_args or task_func_args[0] != "context"
        ):
            raise InvalidTask(
                "Task takes context but does not have a first argument of 'context'."
            )

        if not self.supports_priority and task.priority != DEFAULT_TASK_PRIORITY:
            raise InvalidTask("Backend does not support setting priority of tasks.")
        if (
            task.priority < TASK_MIN_PRIORITY
            or task.priority > TASK_MAX_PRIORITY
            or int(task.priority) != task.priority
        ):
            raise InvalidTask(
                f"priority must be a whole number between {TASK_MIN_PRIORITY} and "
                f"{TASK_MAX_PRIORITY}."
            )

        if not self.supports_defer and task.run_after is not None:
            raise InvalidTask("Backend does not support run_after.")

        if (
            settings.USE_TZ
            and task.run_after is not None
            and not timezone.is_aware(task.run_after)
        ):
            raise InvalidTask("run_after must be an aware datetime.")

        if self.queues and task.queue_name not in self.queues:
            raise InvalidTask(f"Queue '{task.queue_name}' is not valid for backend.")

    @abstractmethod
    def enqueue(self, task, args, kwargs):
        """Queue up a task to be executed."""

    async def aenqueue(self, task, args, kwargs):
        """Queue up a task function (or coroutine) to be executed."""
        return await sync_to_async(self.enqueue, thread_sensitive=True)(
            task=task, args=args, kwargs=kwargs
        )

    def get_result(self, result_id):
        """
        Retrieve a task result by id.

        Raise TaskResultDoesNotExist if such result does not exist.
        """
        raise NotImplementedError(
            "This backend does not support retrieving or refreshing results."
        )

    async def aget_result(self, result_id):
        """See get_result()."""
        return await sync_to_async(self.get_result, thread_sensitive=True)(
            result_id=result_id
        )

    def check(self, **kwargs):
        return []
