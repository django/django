import dataclasses
from datetime import datetime

from django.tasks import (
    DEFAULT_TASK_QUEUE_NAME,
    TaskResultStatus,
    default_task_backend,
    task,
    task_backends,
)
from django.tasks.backends.dummy import DummyBackend
from django.tasks.backends.immediate import ImmediateBackend
from django.tasks.base import TASK_MAX_PRIORITY, TASK_MIN_PRIORITY, Task
from django.tasks.exceptions import (
    InvalidTask,
    InvalidTaskBackend,
    TaskResultDoesNotExist,
    TaskResultMismatch,
)
from django.test import SimpleTestCase, override_settings
from django.utils import timezone
from django.utils.module_loading import import_string

from . import tasks as test_tasks


@override_settings(
    TASKS={
        "default": {
            "BACKEND": "django.tasks.backends.dummy.DummyBackend",
            "QUEUES": ["default", "queue_1"],
        },
        "immediate": {
            "BACKEND": "django.tasks.backends.immediate.ImmediateBackend",
            "QUEUES": [],
        },
        "missing": {"BACKEND": "does.not.exist"},
    },
    USE_TZ=True,
)
class TaskTestCase(SimpleTestCase):
    def setUp(self):
        default_task_backend.clear()

    def test_using_correct_backend(self):
        self.assertEqual(default_task_backend, task_backends["default"])
        self.assertIsInstance(task_backends["default"], DummyBackend)

    def test_task_decorator(self):
        self.assertIsInstance(test_tasks.noop_task, Task)
        self.assertIsInstance(test_tasks.noop_task_async, Task)
        self.assertIsInstance(test_tasks.noop_task_from_bare_decorator, Task)

    def test_enqueue_task(self):
        result = test_tasks.noop_task.enqueue()

        self.assertEqual(result.status, TaskResultStatus.READY)
        self.assertEqual(result.task, test_tasks.noop_task)
        self.assertEqual(result.args, [])
        self.assertEqual(result.kwargs, {})

        self.assertEqual(default_task_backend.results, [result])

    async def test_enqueue_task_async(self):
        result = await test_tasks.noop_task.aenqueue()

        self.assertEqual(result.status, TaskResultStatus.READY)
        self.assertEqual(result.task, test_tasks.noop_task)
        self.assertEqual(result.args, [])
        self.assertEqual(result.kwargs, {})

        self.assertEqual(default_task_backend.results, [result])

    def test_enqueue_with_invalid_argument(self):
        with self.assertRaisesMessage(TypeError, "Unsupported type"):
            test_tasks.noop_task.enqueue(datetime.now())

    async def test_aenqueue_with_invalid_argument(self):
        with self.assertRaisesMessage(TypeError, "Unsupported type"):
            await test_tasks.noop_task.aenqueue(datetime.now())

    def test_using_priority(self):
        self.assertEqual(test_tasks.noop_task.priority, 0)
        self.assertEqual(test_tasks.noop_task.using(priority=1).priority, 1)
        self.assertEqual(test_tasks.noop_task.priority, 0)

    def test_using_queue_name(self):
        self.assertEqual(test_tasks.noop_task.queue_name, DEFAULT_TASK_QUEUE_NAME)
        self.assertEqual(
            test_tasks.noop_task.using(queue_name="queue_1").queue_name, "queue_1"
        )
        self.assertEqual(test_tasks.noop_task.queue_name, DEFAULT_TASK_QUEUE_NAME)

    def test_using_run_after(self):
        now = timezone.now()

        self.assertIsNone(test_tasks.noop_task.run_after)
        self.assertEqual(test_tasks.noop_task.using(run_after=now).run_after, now)
        self.assertIsNone(test_tasks.noop_task.run_after)

    def test_using_unknown_backend(self):
        self.assertEqual(test_tasks.noop_task.backend, "default")

        with self.assertRaisesMessage(
            InvalidTaskBackend, "The connection 'unknown' doesn't exist."
        ):
            test_tasks.noop_task.using(backend="unknown")

    def test_using_missing_backend(self):
        self.assertEqual(test_tasks.noop_task.backend, "default")

        with self.assertRaisesMessage(
            InvalidTaskBackend,
            "Could not find backend 'does.not.exist': No module named 'does'",
        ):
            test_tasks.noop_task.using(backend="missing")

    def test_using_creates_new_instance(self):
        new_task = test_tasks.noop_task.using()

        self.assertEqual(new_task, test_tasks.noop_task)
        self.assertIsNot(new_task, test_tasks.noop_task)

    def test_chained_using(self):
        now = timezone.now()

        run_after_task = test_tasks.noop_task.using(run_after=now)
        self.assertEqual(run_after_task.run_after, now)

        priority_task = run_after_task.using(priority=10)
        self.assertEqual(priority_task.priority, 10)
        self.assertEqual(priority_task.run_after, now)

        self.assertEqual(run_after_task.priority, 0)

    async def test_refresh_result(self):
        result = await test_tasks.noop_task.aenqueue()

        original_result = dataclasses.asdict(result)

        result.refresh()

        self.assertEqual(dataclasses.asdict(result), original_result)

        await result.arefresh()

        self.assertEqual(dataclasses.asdict(result), original_result)

    def test_naive_datetime(self):
        with self.assertRaisesMessage(
            InvalidTask, "run_after must be an aware datetime."
        ):
            test_tasks.noop_task.using(run_after=datetime.now())

    def test_invalid_priority(self):
        with self.assertRaisesMessage(
            InvalidTask,
            f"priority must be a whole number between {TASK_MIN_PRIORITY} and "
            f"{TASK_MAX_PRIORITY}.",
        ):
            test_tasks.noop_task.using(priority=-101)

        with self.assertRaisesMessage(
            InvalidTask,
            f"priority must be a whole number between {TASK_MIN_PRIORITY} and "
            f"{TASK_MAX_PRIORITY}.",
        ):
            test_tasks.noop_task.using(priority=101)

        with self.assertRaisesMessage(
            InvalidTask,
            f"priority must be a whole number between {TASK_MIN_PRIORITY} and "
            f"{TASK_MAX_PRIORITY}.",
        ):
            test_tasks.noop_task.using(priority=3.1)

        test_tasks.noop_task.using(priority=100)
        test_tasks.noop_task.using(priority=-100)
        test_tasks.noop_task.using(priority=0)

    def test_unknown_queue_name(self):
        with self.assertRaisesMessage(
            InvalidTask, "Queue 'queue-2' is not valid for backend."
        ):
            test_tasks.noop_task.using(queue_name="queue-2")
        # Validation is bypassed when the backend QUEUES is an empty list.
        self.assertEqual(
            test_tasks.noop_task.using(
                queue_name="queue-2", backend="immediate"
            ).queue_name,
            "queue-2",
        )

    def test_call_task(self):
        self.assertEqual(test_tasks.calculate_meaning_of_life.call(), 42)

    async def test_call_task_async(self):
        self.assertEqual(await test_tasks.calculate_meaning_of_life.acall(), 42)

    async def test_call_async_task(self):
        self.assertIsNone(await test_tasks.noop_task_async.acall())

    def test_call_async_task_sync(self):
        self.assertIsNone(test_tasks.noop_task_async.call())

    def test_get_result(self):
        result = default_task_backend.enqueue(test_tasks.noop_task, (), {})

        new_result = test_tasks.noop_task.get_result(result.id)

        self.assertEqual(result, new_result)

    async def test_get_result_async(self):
        result = await default_task_backend.aenqueue(test_tasks.noop_task, (), {})

        new_result = await test_tasks.noop_task.aget_result(result.id)

        self.assertEqual(result, new_result)

    async def test_get_missing_result(self):
        with self.assertRaises(TaskResultDoesNotExist):
            test_tasks.noop_task.get_result("123")

        with self.assertRaises(TaskResultDoesNotExist):
            await test_tasks.noop_task.aget_result("123")

    def test_get_incorrect_result(self):
        result = default_task_backend.enqueue(test_tasks.noop_task_async, (), {})
        with self.assertRaisesMessage(TaskResultMismatch, "Task does not match"):
            test_tasks.noop_task.get_result(result.id)

    async def test_get_incorrect_result_async(self):
        result = await default_task_backend.aenqueue(test_tasks.noop_task_async, (), {})
        with self.assertRaisesMessage(TaskResultMismatch, "Task does not match"):
            await test_tasks.noop_task.aget_result(result.id)

    def test_invalid_function(self):
        for invalid_function in [any, self.test_invalid_function]:
            with self.subTest(invalid_function):
                with self.assertRaisesMessage(
                    InvalidTask,
                    "Task function must be defined at a module level.",
                ):
                    task()(invalid_function)

    def test_get_backend(self):
        self.assertEqual(test_tasks.noop_task.backend, "default")
        self.assertIsInstance(test_tasks.noop_task.get_backend(), DummyBackend)

        immediate_task = test_tasks.noop_task.using(backend="immediate")
        self.assertEqual(immediate_task.backend, "immediate")
        self.assertIsInstance(immediate_task.get_backend(), ImmediateBackend)

    def test_name(self):
        self.assertEqual(test_tasks.noop_task.name, "noop_task")
        self.assertEqual(test_tasks.noop_task_async.name, "noop_task_async")

    def test_module_path(self):
        self.assertEqual(test_tasks.noop_task.module_path, "tasks.tasks.noop_task")
        self.assertEqual(
            test_tasks.noop_task_async.module_path, "tasks.tasks.noop_task_async"
        )

        self.assertIs(
            import_string(test_tasks.noop_task.module_path), test_tasks.noop_task
        )
        self.assertIs(
            import_string(test_tasks.noop_task_async.module_path),
            test_tasks.noop_task_async,
        )

    @override_settings(TASKS={})
    def test_no_backends(self):
        with self.assertRaises(InvalidTaskBackend):
            test_tasks.noop_task.enqueue()

    def test_task_error_invalid_exception(self):
        with self.assertLogs("django.tasks"):
            immediate_task = test_tasks.failing_task_value_error.using(
                backend="immediate"
            ).enqueue()

        self.assertEqual(len(immediate_task.errors), 1)

        object.__setattr__(
            immediate_task.errors[0], "exception_class_path", "subprocess.run"
        )

        with self.assertRaisesMessage(
            ValueError, "'subprocess.run' does not reference a valid exception."
        ):
            immediate_task.errors[0].exception_class

    def test_task_error_unknown_module(self):
        with self.assertLogs("django.tasks"):
            immediate_task = test_tasks.failing_task_value_error.using(
                backend="immediate"
            ).enqueue()

        self.assertEqual(len(immediate_task.errors), 1)

        object.__setattr__(
            immediate_task.errors[0], "exception_class_path", "does.not.exist"
        )

        with self.assertRaises(ImportError):
            immediate_task.errors[0].exception_class

    def test_takes_context_without_taking_context(self):
        with self.assertRaisesMessage(
            InvalidTask,
            "Task takes context but does not have a first argument of 'context'.",
        ):
            task(takes_context=True)(test_tasks.calculate_meaning_of_life.func)
