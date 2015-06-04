from .base import Task, get_backend  # NOQA
from .backends import TaskResult  # NOQA
from .constants import *  # NOQA
from .register import registry


def task(name_or_func=None, name=None, using=None, options=None):
    # @task
    if callable(name_or_func):
        if isinstance(name_or_func, Task):
            name_or_func = name_or_func.run
        t = Task(func=name_or_func, name=name, using=using, options=options)
        registry.register(t)
        return t

    # @task('name')
    if name_or_func:
        name = name_or_func

    # @task()
    return lambda f: task(f, name=name)
