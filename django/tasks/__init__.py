from django.tasks.base import Task
from django.tasks.register import registry

def task(name_or_func=None, name=None):
    # @task
    if callable(name_or_func):
        t = Task(func=name_or_func, name=name)
        registry.register(t)
        return t

    # @task('name')
    if name_or_func:
        name = name_or_func

    # @task()
    return lambda f: task(f, name=name)

