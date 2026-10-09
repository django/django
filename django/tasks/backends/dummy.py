from copy import deepcopy

from django.tasks.base import TaskResult, TaskResultStatus
from django.tasks.exceptions import TaskResultDoesNotExist
from django.tasks.signals import task_enqueued
from django.utils import timezone
from django.utils.crypto import get_random_string

from .base import BaseTaskBackend


class DummyBackend(BaseTaskBackend):
    supports_defer = True
    supports_async_task = True
    supports_priority = True
    supports_metadata = True

    def __init__(self, alias, params):
        super().__init__(alias, params)
        self.results = []

    def _store_result(self, result):
        object.__setattr__(result, "enqueued_at", timezone.now())
        self.results.append(result)
        task_enqueued.send(type(self), task_result=result)

    def enqueue(self, task, args, kwargs):
        self.validate_task(task)

        result = TaskResult(
            task=task,
            id=get_random_string(32),
            status=TaskResultStatus.READY,
            enqueued_at=None,
            started_at=None,
            last_attempted_at=None,
            finished_at=None,
            args=args,
            kwargs=kwargs,
            backend=self.alias,
            errors=[],
            worker_ids=[],
            raw_metadata=task.metadata,
        )

        self._store_result(result)

        # Copy the task to prevent mutation issues.
        return deepcopy(result)

    def get_result(self, result_id):
        # Results are only scoped to the current thread, hence
        # supports_get_result is False.
        try:
            return next(result for result in self.results if result.id == result_id)
        except StopIteration:
            raise TaskResultDoesNotExist(result_id) from None

    async def aget_result(self, result_id):
        try:
            return next(result for result in self.results if result.id == result_id)
        except StopIteration:
            raise TaskResultDoesNotExist(result_id) from None

    def save_metadata(self, task_result, metadata):
        stored_result = self.get_result(task_result.id)
        object.__setattr__(stored_result, "raw_metadata", deepcopy(metadata))

    async def asave_metadata(self, task_result, metadata):
        stored_result = await self.aget_result(task_result.id)
        object.__setattr__(stored_result, "raw_metadata", deepcopy(metadata))

    def clear(self):
        self.results.clear()
