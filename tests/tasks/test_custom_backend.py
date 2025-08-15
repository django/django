import logging
from unittest import mock

from django.tasks import default_task_backend, tasks
from django.tasks.backends.base import BaseTaskBackend
from django.tasks.exceptions import InvalidTaskError
from django.test import SimpleTestCase, override_settings

from . import tasks as test_tasks


class CustomBackend(BaseTaskBackend):
    def __init__(self, alias, params):
        super().__init__(alias, params)
        self.prefix = self.options.get("prefix", "")

    def enqueue(self, *args, **kwargs):
        logger = logging.getLogger(__name__)
        logger.info(f"{self.prefix}Task enqueued.")


@override_settings(
    TASKS={
        "default": {
            "BACKEND": f"{CustomBackend.__module__}.{CustomBackend.__qualname__}",
            "ENQUEUE_ON_COMMIT": False,
            "OPTIONS": {"prefix": "PREFIX: "},
        }
    }
)
class CustomBackendTestCase(SimpleTestCase):
    def test_using_correct_backend(self):
        self.assertEqual(default_task_backend, tasks["default"])
        self.assertIsInstance(tasks["default"], CustomBackend)
        self.assertEqual(default_task_backend.alias, "default")
        self.assertEqual(default_task_backend.options, {"prefix": "PREFIX: "})

    @mock.patch.multiple(CustomBackend, supports_async_task=False)
    def test_enqueue_async_task_on_non_async_backend(self):
        with self.assertRaisesMessage(
            InvalidTaskError, "Backend does not support async tasks"
        ):
            default_task_backend.validate_task(test_tasks.noop_task_async)

    def test_options(self):
        with self.assertLogs(__name__, level="INFO") as captured_logs:
            test_tasks.noop_task.enqueue()
        self.assertEqual(len(captured_logs.output), 1)
        self.assertIn("PREFIX: Task enqueued", captured_logs.output[0])
