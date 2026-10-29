import logging
from dataclasses import dataclass
from unittest import mock

from django.tasks import Task, default_task_backend, task, task_backends
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


@dataclass(frozen=True, slots=True, kw_only=True)
class CustomTask(Task):
    foo: int = 3
    bar: int = 300


class CustomTaskBackend(BaseTaskBackend):
    task_class = CustomTask
    supports_priority = True

    def enqueue(self, task, args, kwargs):
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


@override_settings(
    TASKS={
        "default": {
            "BACKEND": f"{CustomTaskBackend.__module__}."
            f"{CustomTaskBackend.__qualname__}",
            "QUEUES": ["default", "high"],
        },
    }
)
class CustomTaskTestCase(SimpleTestCase):
    def test_custom_task_default_values(self):
        my_task = task()(test_tasks.noop_task.func)

        self.assertIsInstance(my_task, CustomTask)
        self.assertEqual(my_task.foo, 3)
        self.assertEqual(my_task.bar, 300)

    def test_custom_task_with_custom_values(self):
        my_task = task(foo=5, bar=600)(test_tasks.noop_task.func)

        self.assertIsInstance(my_task, CustomTask)
        self.assertEqual(my_task.foo, 5)
        self.assertEqual(my_task.bar, 600)

    def test_custom_task_with_standard_and_custom_values(self):
        my_task = task(priority=10, queue_name="high", foo=10, bar=1000)(
            test_tasks.noop_task.func
        )

        self.assertIsInstance(my_task, CustomTask)
        self.assertEqual(my_task.priority, 10)
        self.assertEqual(my_task.queue_name, "high")
        self.assertEqual(my_task.foo, 10)
        self.assertEqual(my_task.bar, 1000)
        self.assertFalse(my_task.takes_context)
        self.assertIsNone(my_task.run_after)

    def test_custom_task_invalid_kwarg(self):
        with self.assertRaises(TypeError):
            task(unknown_param=123)(test_tasks.noop_task.func)
