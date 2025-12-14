import logging
import sys

from asgiref.local import Local

from django.core.signals import setting_changed
from django.dispatch import Signal, receiver

from .base import TaskResultStatus

logger = logging.getLogger("django.tasks")

task_enqueued = Signal()
task_finished = Signal()
task_started = Signal()


@receiver(setting_changed)
def clear_tasks_handlers(*, setting, **kwargs):
    """Reset the connection handler whenever the settings change."""
    if setting == "TASKS":
        from . import task_backends

        task_backends._settings = task_backends.settings = (
            task_backends.configure_settings(None)
        )
        task_backends._connections = Local()


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
    logger.log(
        (
            logging.ERROR
            if task_result.status == TaskResultStatus.FAILED
            else logging.INFO
        ),
        "Task id=%s path=%s state=%s",
        task_result.id,
        task_result.task.module_path,
        task_result.status,
        # Signal is sent inside exception handlers, so exc_info() is available.
        exc_info=sys.exc_info(),
    )
