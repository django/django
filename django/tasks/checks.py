from django.core import checks


@checks.register
def check_tasks(app_configs=None, **kwargs):
    """Checks all registered Task backends."""

    from . import task_backends

    for backend in task_backends.all():
        yield from backend.check()
