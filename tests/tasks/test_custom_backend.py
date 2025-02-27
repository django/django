from unittest import mock

from django.tasks import default_task_backend, tasks
from django.tasks.backends.base import BaseTaskBackend
from django.tasks.exceptions import InvalidTaskError
from django.tasks.utils import get_module_path
from django.test import SimpleTestCase, override_settings

from . import tasks as test_tasks


class CustomBackend(BaseTaskBackend):
    def enqueue(self, *args, **kwargs):
        pass


@override_settings(
    TASKS={
        "default": {
            "BACKEND": get_module_path(CustomBackend),
            "ENQUEUE_ON_COMMIT": False,
        }
    }
)
class CustomBackendTestCase(SimpleTestCase):
    def test_using_correct_backend(self):
        self.assertEqual(default_task_backend, tasks["default"])
        self.assertIsInstance(tasks["default"], CustomBackend)

    @mock.patch.multiple(CustomBackend, supports_async_task=False)
    def test_enqueue_async_task_on_non_async_backend(self):
        with self.assertRaisesMessage(
            InvalidTaskError, "Backend does not support async tasks"
        ):
            default_task_backend.validate_task(test_tasks.noop_task_async)
