from copy import deepcopy
from functools import partial
from uuid import uuid4

from django.db import transaction
from django.tasks.exceptions import ResultDoesNotExist
from django.tasks.signals import task_enqueued
from django.tasks.task import ResultStatus, TaskResult
from django.tasks.utils import json_normalize
from django.utils import timezone

from .base import BaseTaskBackend


class DummyBackend(BaseTaskBackend):
    supports_defer = True
    supports_async_task = True

    def __init__(self, options) -> None:
        super().__init__(options)

        self.results = []

    def _store_result(self, result) -> None:
        object.__setattr__(result, "enqueued_at", timezone.now())
        self.results.append(result)
        task_enqueued.send(type(self), task_result=result)

    def enqueue(self, task, args, kwargs) -> TaskResult:
        self.validate_task(task)

        result = TaskResult(
            task=task,
            id=str(uuid4()),
            status=ResultStatus.NEW,
            enqueued_at=None,
            started_at=None,
            finished_at=None,
            args=json_normalize(args),
            kwargs=json_normalize(kwargs),
            backend=self.alias,
        )

        if self._get_enqueue_on_commit_for_task(task) is not False:
            transaction.on_commit(partial(self._store_result, result))
        else:
            self._store_result(result)

        # Copy the task to prevent mutation issues
        return deepcopy(result)

    # Don't set `supports_get_result` as the results are scoped to the current thread
    def get_result(self, result_id):
        try:
            return next(result for result in self.results if result.id == result_id)
        except StopIteration:
            raise ResultDoesNotExist(result_id) from None

    def clear(self):
        self.results.clear()
