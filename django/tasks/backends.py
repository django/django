UNKNOWN = 0
PENDING = 1
FAILED = 2
SUCCESS = 3

class ResultUnavailable(Exception):
    pass

class InvalidCacheBackendError(Exception):
    pass

class BaseBackend(object):

    def __init__(self, connection, **kwargs):
        self._connection = connection

    def status(self, task_id):
        """
        The current status of the task.

        PENDING: the task is currently in-queue, and waiting to be ran.
        FAILED: the task attempted to run, but failed for some reason
        SUCCESS: the task successfully ran
        UNKNOWN: unable to determine the status of the task
        """
        raise NotImplementedError

    def get_result(self, task_id):
        """
        If the task has ran and returned a result, return that result.

        If not, raise a ResultUnavailable exception
        """
        raise NotImplementedError

    def remove_task(self, task_id, *args, **kwargs):
        """
        Given task_id, attempt to remove it from the queue
        """
        raise NotImplementedError

    def delay(self, task, *args, **kwargs):
        """
        Enqueue provided task
        """
        raise NotImplementedError


class DummyTaskBackend(BaseBackend):
    def __init__(self, *args, **kwargs):
        super(DummyTaskBackend, self).__init__(*args, **kwargs)
        self._next_task_id = 1
        self._results = {}
        self._fails = set()

    def status(self, task_id):
        if task_id in self._fails:
            return FAILED
        elif task_id in self._results:
            return SUCCESS
        return UNKNOWN

    def kill(self, task_id):
        return

    def get_result(self, task_id):
        try:
            return self._results.pop(task_id)
        except KeyError:
            raise ResultUnavailable()

    def delay(self, task, *args, **kwargs):
        task_id = self._next_task_id
        self._next_task_id += 1
        try:
            self._results[task_id] = task(*args, **kwargs)
        except:
            self._fails.add(task_id)

        return task_id
