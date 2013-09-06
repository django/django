from __future__ import unicode_literals

from django.tasks.backends import DummyBackend


class TaskResult(object):
    def __init__(self, backend, task_id):
        self._backend = backend
        self._task_id = task_id

    def status(self, **kwargs):
        return self._backend.status(self._task_id, **kwargs)

    def get_result(self, **kwargs):
        return self._backend.get_result(self._task_id, **kwargs)


class Task(object):
    def __init__(self, func=None, name=None):
        if not func and not hasattr(self, 'run'):
            raise
        self.run = func

    def __repr__(self):
        return "<task %s>" % self.name

    def _get_backend(self):
        return DummyBackend()

    def delay(self, *args, **kwargs):
        backend = self._get_backend()
        task_id = backend.delay(self, *args, **kwargs)
        return TaskResult(backend, task_id)

    def __call__(self):
        # call it right away
        return self._run(*self.args, **self.kwargs)

