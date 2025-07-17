import logging
from functools import partial

from django.db import transaction
from django.tasks.signals import task_enqueued, task_finished, task_started
from django.tasks.task import ResultStatus, TaskContext, TaskError, TaskResult
from django.tasks.utils import get_exception_traceback, get_random_id, json_normalize
from django.utils import timezone

from .base import BaseTaskBackend

logger = logging.getLogger(__name__)


class ImmediateBackend(BaseTaskBackend):
    supports_async_task = True

    def __init__(self, alias, params):
        super().__init__(alias, params)

        self.worker_id = get_random_id()

    def _execute_task(self, task_result):
        """
        Execute the task for the given `TaskResult`, mutating it with the outcome
        """
        object.__setattr__(task_result, "enqueued_at", timezone.now())
        task_enqueued.send(type(self), task_result=task_result)

        task = task_result.task

        object.__setattr__(task_result, "status", ResultStatus.RUNNING)
        object.__setattr__(task_result, "started_at", timezone.now())
        object.__setattr__(task_result, "last_attempted_at", timezone.now())
        task_result.worker_ids.append(self.worker_id)
        task_started.send(sender=type(self), task_result=task_result)

        try:
            if task.takes_context:
                raw_return_value = task.call(
                    TaskContext(task_result=task_result),
                    *task_result.args,
                    **task_result.kwargs,
                )
            else:
                raw_return_value = task.call(*task_result.args, **task_result.kwargs)

            object.__setattr__(
                task_result,
                "_return_value",
                json_normalize(raw_return_value),
            )
        except BaseException as e:
            # If the user tried to terminate, let them
            if isinstance(e, KeyboardInterrupt):
                raise

            object.__setattr__(task_result, "finished_at", timezone.now())

            exception_type = type(e)
            task_result.errors.append(
                TaskError(
                    exception_class_path=(
                        f"{exception_type.__module__}.{exception_type.__qualname__}"
                    ),
                    traceback=get_exception_traceback(e),
                )
            )

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
            status=ResultStatus.READY,
            enqueued_at=None,
            started_at=None,
            last_attempted_at=None,
            finished_at=None,
            args=json_normalize(args),
            kwargs=json_normalize(kwargs),
            backend=self.alias,
            errors=[],
            worker_ids=[],
        )

        if self._get_enqueue_on_commit_for_task(task) is not False:
            transaction.on_commit(partial(self._execute_task, task_result))
        else:
            self._execute_task(task_result)

        return task_result
