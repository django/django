import logging
from functools import partial
from inspect import iscoroutinefunction

from asgiref.sync import async_to_sync

from django.db import transaction
from django.tasks.signals import task_enqueued, task_finished
from django.tasks.task import ResultStatus, TaskResult
from django.tasks.utils import get_exception_traceback, get_random_id, json_normalize
from django.utils import timezone

from .base import BaseTaskBackend

logger = logging.getLogger(__name__)


class ImmediateBackend(BaseTaskBackend):
    supports_async_task = True

    def _execute_task(self, task_result):
        """
        Execute the task for the given `TaskResult`, mutating it with the outcome
        """
        object.__setattr__(task_result, "enqueued_at", timezone.now())
        task_enqueued.send(type(self), task_result=task_result)

        task = task_result.task

        calling_task_func = (
            async_to_sync(task.func) if iscoroutinefunction(task.func) else task.func
        )

        object.__setattr__(task_result, "started_at", timezone.now())
        try:
            object.__setattr__(
                task_result,
                "_return_value",
                json_normalize(
                    calling_task_func(*task_result.args, **task_result.kwargs)
                ),
            )
        except BaseException as e:
            # If the user tried to terminate, let them
            if isinstance(e, KeyboardInterrupt):
                raise

            object.__setattr__(task_result, "finished_at", timezone.now())

            object.__setattr__(task_result, "_traceback", get_exception_traceback(e))
            object.__setattr__(task_result, "_exception_class", type(e))

            object.__setattr__(task_result, "status", ResultStatus.FAILED)

            task_finished.send(type(self), task_result=task_result)
        else:
            object.__setattr__(task_result, "finished_at", timezone.now())
            object.__setattr__(task_result, "status", ResultStatus.SUCCEEDED)

            task_finished.send(type(self), task_result=task_result)

    def enqueue(self, task, args, kwargs):
        self.validate_task(task)

        task_result = TaskResult(
            task=task,
            id=get_random_id(),
            status=ResultStatus.NEW,
            enqueued_at=None,
            started_at=None,
            finished_at=None,
            args=args,
            kwargs=kwargs,
            backend=self.alias,
        )

        if self._get_enqueue_on_commit_for_task(task) is not False:
            transaction.on_commit(partial(self._execute_task, task_result))
        else:
            self._execute_task(task_result)

        return task_result
