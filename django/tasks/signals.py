import logging

from asgiref.local import Local

from django.core.signals import setting_changed
from django.dispatch import Signal, receiver

from .base import ResultStatus

logger = logging.getLogger("django.tasks")

task_enqueued = Signal()
task_finished = Signal()
task_started = Signal()


@receiver(setting_changed)
def clear_tasks_handlers(*, setting: str, **kwargs: dict):
    """
    Reset the connection handler whenever the settings change
    """
    if setting == "TASKS":
        from django.tasks import tasks

        tasks._settings = tasks.settings = tasks.configure_settings(None)
        tasks._connections = Local()


@receiver(task_enqueued)
def log_task_enqueued(sender, task_result, **kwargs):
    logger.debug(
        "Task id=%s path=%s enqueued backend=%s",
        task_result.id,
        task_result.task.module_path,
        task_result.backend,
    )


@receiver(task_started)
def log_task_started(sender, task_result, **kwargs):
    logger.info(
        "Task id=%s path=%s state=%s",
        task_result.id,
        task_result.task.module_path,
        task_result.status,
    )


@receiver(task_finished)
def log_task_finished(sender, task_result, **kwargs):
    if task_result.status == ResultStatus.FAILED:
        # Use `.exception` to integrate with error monitoring tools (eg Sentry)
        log_method = logger.exception
    else:
        log_method = logger.info

    log_method(
        "Task id=%s path=%s state=%s",
        task_result.id,
        task_result.task.module_path,
        task_result.status,
    )
