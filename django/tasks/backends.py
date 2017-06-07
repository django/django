from itertools import count

from . import constants
from ..utils.six import string_types
from .base import get_backend
from .exceptions import ResultUnavailable


class TaskResult(object):
    """
    Wrapper class representing a status of a task. Provides methods to retrieve
    the task's status and result value/error.
    """
    def __init__(self, task_id, backend='default'):
        if isinstance(backend, string_types):
            backend = get_backend(backend)
        self._backend = backend
        self.task_id = task_id

    def __repr__(self):
        return 'TaskResul(%r, backend=%r)' % (self.task_id, self.alias)

    @property
    def alias(self):
        return self._backend.alias

    def get_status(self, **kwargs):
        """
        Retrieve the status of the task from the backend.

        All keyword arguments are passed to the backend.
        """
        return self._backend.status(self.task_id, **kwargs)

    def get_result(self, **kwargs):
        """
        Retrieve the result of the task from the backend if the task has
        successfully finished or the causing error if the task has failed.

        All keyword arguments are passed to the backend.

        Raises a ResultUnavailable exception when there is no result available:
            ResultUnknown if status is UNKNOWN
            ResultPending if status is PENDING
        """
        return self._backend.get_result(self.task_id, **kwargs)


class BaseBackend(object):
    def __init__(self, alias, **kwargs):
        self.alias = alias

    def get_status(self, task_id, **kwargs):
        """
        The current status of the task.

        UNKNOWN: unable to determine the status of the task
        PENDING: the task is currently in-queue, and waiting to be ran.
        FAILED: the task attempted to run, but failed for some reason
        SUCCESS: the task successfully ran
        """
        raise NotImplementedError

    def get_result(self, task_id, **kwargs):
        """
        If the task has ran and returned a result, return that result.

        If not, raise a ResultUnavailable exception:
            ResultUnknown if status is UNKNOWN
            ResultPending if status is PENDING
        """
        raise NotImplementedError

    def delay(self, task, *args, **kwargs):
        """
        Enqueue provided task and return TaskResult instance.
        """
        raise NotImplementedError


class DummyTaskResult(TaskResult):
    """
    TaskResult subclass used by DummyTaskBackend. It embeds the status and the
    result.
    """
    def __init__(self, task_id, backend, status, result):
        super(DummyTaskResult, self).__init__(task_id, backend)
        self._status = status
        self._result = result

    def get_status(self, **kwargs):
        return self._status

    def get_result(self, **kwargs):
        return self._result


class DummyTaskBackend(BaseBackend):
    """
    Dummy backend that executes tasks in-place and returns an instance of
    DummyTaskResult containing the status (SUCCESS/FAILED) and the result of
    the task's execution.
    """
    def __init__(self, *args, **kwargs):
        super(DummyTaskBackend, self).__init__(*args, **kwargs)
        self._next_task_id = count()

    def get_status(self, task_id):
        return constants.UNKNOWN

    def get_result(self, task_id):
        raise ResultUnavailable(
            "DummyTaskBackend doesn't support storing and retrieving results.")

    def delay(self, task, *args, **kwargs):
        task_id = self._next_task_id.next()
        result = None
        status = constants.SUCCESS
        try:
            result = task(*args, **kwargs)
        except Exception as e:
            result = e
            status = constants.FAILED

        return DummyTaskResult(task_id, self, status, result)
