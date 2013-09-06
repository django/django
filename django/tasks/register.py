from django.tasks.base import Task

class AlreadyRegistered(Exception):
    pass

class TaskRegistry(object):
    def __init__(self):
        self._registry = {}

    def register(self, task):
        if not isinstance(task, Task):
            # we've been given a class, instantiate it
            task = task()

        if task.name in self._registry:
            raise AlreadyRegistered('The task %s is already registered' % task.name)
        self._registry[task.name] = task

registry = TaskRegistry()
