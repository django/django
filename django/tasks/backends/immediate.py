import logging
from traceback import format_exception

from django.tasks.base import TaskContext, TaskError, TaskResult, TaskResultStatus
from django.tasks.signals import task_enqueued, task_finished, task_started
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.json import normalize_json

from .base import BaseTaskBackend

logger = logging.getLogger(__name__)


class ImmediateBackend(BaseTaskBackend):
    supports_async_task = True
    supports_priority = True

    def __init__(self, alias, params):
        super().__init__(alias, params)
        self.worker_id = get_random_string(32)

    def _execute_task(self, task_result):
        """
        Execute the Task for the given TaskResult, mutating it with the
        outcome.
        """
        object.__setattr__(task_result, "enqueued_at", timezone.now())
        task_enqueued.send(type(self), task_result=task_result)

        task = task_result.task
        task_start_time = timezone.now()
        object.__setattr__(task_result, "status", TaskResultStatus.RUNNING)
        object.__setattr__(task_result, "started_at", task_start_time)
        object.__setattr__(task_result, "last_attempted_at", task_start_time)
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
                normalize_json(raw_return_value),
            )
        except KeyboardInterrupt:
            # If the user tried to terminate, let them
            raise
        except BaseException as e:
            object.__setattr__(task_result, "finished_at", timezone.now())
            exception_type = type(e)
            task_result.errors.append(
                TaskError(
                    exception_class_path=(
                        f"{exception_type.__module__}.{exception_type.__qualname__}"
                    ),
                    traceback="".join(format_exception(e)),
                )
            )
            object.__setattr__(task_result, "status", TaskResultStatus.FAILED)
            task_finished.send(type(self), task_result=task_result)
        else:
            object.__setattr__(task_result, "finished_at", timezone.now())
            object.__setattr__(task_result, "status", TaskResultStatus.SUCCESSFUL)
            task_finished.send(type(self), task_result=task_result)

    def enqueue(self, task, args, kwargs):
        self.validate_task(task)

        task_result = TaskResult(
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
        )

        self._execute_task(task_result)

        return task_result
