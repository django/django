from copy import deepcopy
from functools import partial

from django.db import transaction
from django.tasks.base import ResultStatus, TaskResult
from django.tasks.exceptions import ResultDoesNotExist
from django.tasks.signals import task_enqueued
from django.tasks.utils import get_random_id
from django.utils import timezone

from .base import BaseTaskBackend


class DummyBackend(BaseTaskBackend):
    supports_defer = True
    supports_async_task = True
    supports_priority = True

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
            id=get_random_id(),
            status=ResultStatus.READY,
            enqueued_at=None,
            started_at=None,
            last_attempted_at=None,
            finished_at=None,
            args=args,
            kwargs=kwargs,
            backend=self.alias,
            errors=[],
            worker_ids=[],
        )

        if self._get_enqueue_on_commit_for_task(task) is not False:
            transaction.on_commit(partial(self._store_result, result))
        else:
            self._store_result(result)

        # Copy the task to prevent mutation issues.
        return deepcopy(result)

    def get_result(self, result_id):
        # Results are only scoped to the current thread, hence
        # supports_get_result is False.
        try:
            return next(result for result in self.results if result.id == result_id)
        except StopIteration:
            raise ResultDoesNotExist(result_id) from None

    async def aget_result(self, result_id):
        try:
            return next(result for result in self.results if result.id == result_id)
        except StopIteration:
            raise ResultDoesNotExist(result_id) from None

    def clear(self):
        self.results.clear()
