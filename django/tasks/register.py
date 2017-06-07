from .exceptions import AlreadyRegistered, TaskDoesNotExist


class TaskRegistry(object):
    def __init__(self):
        self._registry = {}

    def register(self, task):
        if task.name in self._registry:
            raise AlreadyRegistered('The task %s is already registered' % task.name)
        self._registry[task.name] = task

    def get_task(self, name):
        try:
            return self._registry[name]
        except KeyError:
            raise TaskDoesNotExist("There is no task registered under '%s'" % name)

    def delay_by_name(self, name, *args, **kwargs):
        task = self.get_task(name)
        return task.delay(*args, **kwargs)

registry = TaskRegistry()
