from typing import cast
from unittest import mock

from django.db import transaction
from django.tasks import TaskResultStatus, default_task_backend, task_backends
from django.tasks.backends.dummy import DummyBackend
from django.tasks.base import Task
from django.tasks.exceptions import InvalidTask, TaskResultDoesNotExist
from django.test import SimpleTestCase, TransactionTestCase, override_settings

from . import tasks as test_tasks


@override_settings(
    TASKS={
        "default": {
            "BACKEND": "django.tasks.backends.dummy.DummyBackend",
            "QUEUES": [],
        }
    }
)
class DummyBackendTestCase(SimpleTestCase):
    def setUp(self):
        default_task_backend.clear()

    def test_using_correct_backend(self):
        self.assertEqual(default_task_backend, task_backends["default"])
        self.assertIsInstance(task_backends["default"], DummyBackend)
        self.assertEqual(default_task_backend.alias, "default")
        self.assertEqual(default_task_backend.options, {})

    def test_enqueue_task(self):
        for task in [test_tasks.noop_task, test_tasks.noop_task_async]:
            with self.subTest(task):
                result = cast(Task, task).enqueue(1, two=3)

                self.assertEqual(result.status, TaskResultStatus.READY)
                self.assertIs(result.is_finished, False)
                self.assertIsNone(result.started_at)
                self.assertIsNone(result.last_attempted_at)
                self.assertIsNone(result.finished_at)
                with self.assertRaisesMessage(ValueError, "Task has not finished yet"):
                    result.return_value
                self.assertEqual(result.task, task)
                self.assertEqual(result.args, [1])
                self.assertEqual(result.kwargs, {"two": 3})
                self.assertEqual(result.attempts, 0)

                self.assertIn(result, default_task_backend.results)

    async def test_enqueue_task_async(self):
        for task in [test_tasks.noop_task, test_tasks.noop_task_async]:
            with self.subTest(task):
                result = await cast(Task, task).aenqueue()

                self.assertEqual(result.status, TaskResultStatus.READY)
                self.assertIs(result.is_finished, False)
                self.assertIsNone(result.started_at)
                self.assertIsNone(result.last_attempted_at)
                self.assertIsNone(result.finished_at)
                with self.assertRaisesMessage(ValueError, "Task has not finished yet"):
                    result.return_value
                self.assertEqual(result.task, task)
                self.assertEqual(result.args, [])
                self.assertEqual(result.kwargs, {})
                self.assertEqual(result.attempts, 0)

                self.assertIn(result, default_task_backend.results)

    def test_get_result(self):
        result = default_task_backend.enqueue(test_tasks.noop_task, (), {})

        new_result = default_task_backend.get_result(result.id)

        self.assertEqual(result, new_result)

    async def test_get_result_async(self):
        result = await default_task_backend.aenqueue(test_tasks.noop_task, (), {})

        new_result = await default_task_backend.aget_result(result.id)

        self.assertEqual(result, new_result)

    def test_refresh_result(self):
        result = default_task_backend.enqueue(
            test_tasks.calculate_meaning_of_life, (), {}
        )

        enqueued_result = default_task_backend.results[0]
        object.__setattr__(enqueued_result, "status", TaskResultStatus.SUCCESSFUL)

        self.assertEqual(result.status, TaskResultStatus.READY)
        result.refresh()
        self.assertEqual(result.status, TaskResultStatus.SUCCESSFUL)

    async def test_refresh_result_async(self):
        result = await default_task_backend.aenqueue(
            test_tasks.calculate_meaning_of_life, (), {}
        )

        enqueued_result = default_task_backend.results[0]
        object.__setattr__(enqueued_result, "status", TaskResultStatus.SUCCESSFUL)

        self.assertEqual(result.status, TaskResultStatus.READY)
        await result.arefresh()
        self.assertEqual(result.status, TaskResultStatus.SUCCESSFUL)

    async def test_get_missing_result(self):
        with self.assertRaises(TaskResultDoesNotExist):
            default_task_backend.get_result("123")

        with self.assertRaises(TaskResultDoesNotExist):
            await default_task_backend.aget_result("123")

    def test_enqueue_logs(self):
        with self.assertLogs("django.tasks", level="DEBUG") as captured_logs:
            result = test_tasks.noop_task.enqueue()

        self.assertEqual(len(captured_logs.output), 1)
        self.assertIn("enqueued", captured_logs.output[0])
        self.assertIn(result.id, captured_logs.output[0])

    def test_errors(self):
        result = test_tasks.noop_task.enqueue()
        self.assertEqual(result.errors, [])

    def test_validate_disallowed_async_task(self):
        with mock.patch.multiple(default_task_backend, supports_async_task=False):
            with self.assertRaisesMessage(
                InvalidTask, "Backend does not support async Tasks."
            ):
                default_task_backend.validate_task(test_tasks.noop_task_async)

    def test_check(self):
        errors = list(default_task_backend.check())
        self.assertEqual(len(errors), 0, errors)

    def test_takes_context(self):
        result = test_tasks.get_task_id.enqueue()
        self.assertEqual(result.status, TaskResultStatus.READY)

    def test_clear(self):
        result = test_tasks.noop_task.enqueue()

        default_task_backend.get_result(result.id)

        default_task_backend.clear()

        with self.assertRaisesMessage(TaskResultDoesNotExist, result.id):
            default_task_backend.get_result(result.id)

    def test_validate_on_enqueue(self):
        task_with_custom_queue_name = test_tasks.noop_task.using(
            queue_name="unknown_queue"
        )

        with override_settings(
            TASKS={
                "default": {
                    "BACKEND": "django.tasks.backends.dummy.DummyBackend",
                    "QUEUES": ["queue-1"],
                }
            }
        ):
            with self.assertRaisesMessage(
                InvalidTask, "Queue 'unknown_queue' is not valid for backend"
            ):
                task_with_custom_queue_name.enqueue()

    async def test_validate_on_aenqueue(self):
        task_with_custom_queue_name = test_tasks.noop_task.using(
            queue_name="unknown_queue"
        )

        with override_settings(
            TASKS={
                "default": {
                    "BACKEND": "django.tasks.backends.dummy.DummyBackend",
                    "QUEUES": ["queue-1"],
                }
            }
        ):
            with self.assertRaisesMessage(
                InvalidTask, "Queue 'unknown_queue' is not valid for backend"
            ):
                await task_with_custom_queue_name.aenqueue()


class DummyBackendTransactionTestCase(TransactionTestCase):
    available_apps = []

    @override_settings(
        TASKS={
            "default": {
                "BACKEND": "django.tasks.backends.dummy.DummyBackend",
            }
        }
    )
    def test_doesnt_wait_until_transaction_commit_by_default(self):
        with transaction.atomic():
            result = test_tasks.noop_task.enqueue()

            self.assertIsNotNone(result.enqueued_at)

            self.assertEqual(len(default_task_backend.results), 1)

        self.assertEqual(len(default_task_backend.results), 1)
