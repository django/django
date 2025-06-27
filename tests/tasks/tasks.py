import time

from django.tasks import TaskContext, task


@task()
def noop_task(*args: tuple, **kwargs: dict):
    return None


@task
def noop_task_from_bare_decorator(*args: tuple, **kwargs: dict):
    return None


@task()
async def noop_task_async(*args: tuple, **kwargs: dict):
    return None


@task()
def calculate_meaning_of_life():
    return 42


@task()
def failing_task_value_error():
    raise ValueError("This task failed due to ValueError")


@task()
def failing_task_system_exit():
    raise SystemExit("This task failed due to SystemExit")


@task()
def failing_task_keyboard_interrupt():
    raise KeyboardInterrupt("This task failed due to KeyboardInterrupt")


@task()
def complex_exception():
    raise ValueError(ValueError("This task failed"))


@task()
def exit_task():
    exit(1)


@task(enqueue_on_commit=True)
def enqueue_on_commit_task():
    pass


@task(enqueue_on_commit=False)
def never_enqueue_on_commit_task():
    pass


@task()
def hang():
    """
    Do nothing for 5 minutes
    """
    time.sleep(300)


@task()
def sleep_for(seconds: float):
    time.sleep(seconds)


@task(takes_context=True)
def get_task_id(context):
    return context.task_result.id


@task(takes_context=True)
def test_context(context, attempt):
    assert isinstance(context, TaskContext)
    assert context.attempt == attempt
