import time

from django.tasks import TaskContext, task


@task()
def noop_task(*args, **kwargs):
    return None


@task
def noop_task_from_bare_decorator(*args, **kwargs):
    return None


@task()
async def noop_task_async(*args, **kwargs):
    return None


@task()
def calculate_meaning_of_life():
    return 42


@task()
def failing_task_value_error():
    raise ValueError("This Task failed due to ValueError")


@task()
def failing_task_system_exit():
    raise SystemExit("This Task failed due to SystemExit")


@task()
def failing_task_keyboard_interrupt():
    raise KeyboardInterrupt("This Task failed due to KeyboardInterrupt")


@task()
def complex_exception():
    raise ValueError(ValueError("This task failed"))


@task()
def complex_return_value():
    # Return something which isn't JSON serializable nor picklable.
    return lambda: True


@task()
def exit_task():
    exit(1)


@task()
def hang():
    """
    Do nothing for 5 minutes
    """
    time.sleep(300)


@task()
def sleep_for(seconds):
    time.sleep(seconds)


@task(takes_context=True)
def get_task_id(context):
    return context.task_result.id


@task(takes_context=True)
def test_context(context, attempt):
    assert isinstance(context, TaskContext)
    assert context.attempt == attempt


@task(takes_context=True)
def update_metadata(context, **values):
    context.metadata.update(values)


@task(takes_context=True)
async def update_metadata_async(context, **values):
    context.metadata.update(values)


@task(takes_context=True)
def update_metadata_and_fail(context, **values):
    context.metadata.update(values)
    raise ValueError("Task failed after updating metadata")


@task(takes_context=True)
def save_metadata_explicitly(context, key, value):
    context.metadata[key] = value
    context.save_metadata()
    return context.task_result.metadata


@task(takes_context=True)
async def save_metadata_explicitly_async(context, key, value):
    context.metadata[key] = value
    await context.asave_metadata()
    return context.task_result.metadata


@task(takes_context=True)
def append_to_metadata_list(context, key, value):
    context.metadata[key].append(value)


@task(takes_context=True)
def get_metadata(context):
    return context.metadata


@task(takes_context=True)
def set_invalid_metadata(context):
    context.metadata["invalid"] = {1, 2}
