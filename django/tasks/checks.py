from django.core import checks


@checks.register
def check_tasks(app_configs=None, **kwargs):
    """Checks all registered task backends."""

    from django.tasks import tasks

    for backend in tasks.all():
        yield from backend.check()
