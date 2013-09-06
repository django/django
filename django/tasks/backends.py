UNKNOWN = 0
PENDING = 1
FAILED = 2
SUCCESS = 3

class ResultUnavailable(Exception):
    pass

class DummyBackend(object):
    def __init__(self):
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
