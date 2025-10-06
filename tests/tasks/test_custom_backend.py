import logging
from unittest import mock

from django.tasks import default_task_backend, task_backends
from django.tasks.backends.base import BaseTaskBackend
from django.tasks.exceptions import InvalidTask
from django.test import SimpleTestCase, override_settings

from . import tasks as test_tasks


class CustomBackend(BaseTaskBackend):
    def __init__(self, alias, params):
        super().__init__(alias, params)
        self.prefix = self.options.get("prefix", "")

    def enqueue(self, *args, **kwargs):
        logger = logging.getLogger(__name__)
        logger.info(f"{self.prefix}Task enqueued.")


class CustomBackendNoEnqueue(BaseTaskBackend):
    pass


@override_settings(
    TASKS={
        "default": {
            "BACKEND": f"{CustomBackend.__module__}.{CustomBackend.__qualname__}",
            "OPTIONS": {"prefix": "PREFIX: "},
        },
        "no_enqueue": {
            "BACKEND": f"{CustomBackendNoEnqueue.__module__}."
            f"{CustomBackendNoEnqueue.__qualname__}",
        },
    }
)
class CustomBackendTestCase(SimpleTestCase):
    def test_using_correct_backend(self):
        self.assertEqual(default_task_backend, task_backends["default"])
        self.assertIsInstance(task_backends["default"], CustomBackend)
        self.assertEqual(default_task_backend.alias, "default")
        self.assertEqual(default_task_backend.options, {"prefix": "PREFIX: "})

    @mock.patch.multiple(CustomBackend, supports_async_task=False)
    def test_enqueue_async_task_on_non_async_backend(self):
        with self.assertRaisesMessage(
            InvalidTask, "Backend does not support async Tasks."
        ):
            default_task_backend.validate_task(test_tasks.noop_task_async)

    def test_backend_does_not_support_priority(self):
        with self.assertRaisesMessage(
            InvalidTask, "Backend does not support setting priority of tasks."
        ):
            test_tasks.noop_task.using(priority=10)

    def test_options(self):
        with self.assertLogs(__name__, level="INFO") as captured_logs:
            test_tasks.noop_task.enqueue()
        self.assertEqual(len(captured_logs.output), 1)
        self.assertIn("PREFIX: Task enqueued", captured_logs.output[0])

    def test_no_enqueue(self):
        with self.assertRaisesMessage(
            TypeError,
            "Can't instantiate abstract class CustomBackendNoEnqueue "
            "without an implementation for abstract method 'enqueue'",
        ):
            test_tasks.noop_task.using(backend="no_enqueue")
