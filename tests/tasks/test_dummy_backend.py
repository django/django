from typing import cast
from unittest import mock

from django.db import transaction
from django.db.utils import ConnectionHandler
from django.tasks import ResultStatus, default_task_backend, tasks
from django.tasks.backends.dummy import DummyBackend
from django.tasks.base import Task
from django.tasks.exceptions import InvalidTaskError, ResultDoesNotExist
from django.test import SimpleTestCase, TransactionTestCase, override_settings

from . import tasks as test_tasks


@override_settings(
    TASKS={
        "default": {
            "BACKEND": "django.tasks.backends.dummy.DummyBackend",
            "ENQUEUE_ON_COMMIT": False,
        }
    }
)
class DummyBackendTestCase(SimpleTestCase):
    def setUp(self):
        default_task_backend.clear()

    def test_using_correct_backend(self):
        self.assertEqual(default_task_backend, tasks["default"])
        self.assertIsInstance(tasks["default"], DummyBackend)
        self.assertEqual(default_task_backend.alias, "default")
        self.assertEqual(default_task_backend.options, {})

    def test_enqueue_task(self):
        for task in [test_tasks.noop_task, test_tasks.noop_task_async]:
            with self.subTest(task):
                result = cast(Task, task).enqueue(1, two=3)

                self.assertEqual(result.status, ResultStatus.READY)
                self.assertFalse(result.is_finished)
                self.assertIsNone(result.started_at)
                self.assertIsNone(result.last_attempted_at)
                self.assertIsNone(result.finished_at)
                with self.assertRaisesMessage(ValueError, "Task has not finished yet"):
                    result.return_value  # noqa:B018
                self.assertEqual(result.task, task)
                self.assertEqual(result.args, [1])
                self.assertEqual(result.kwargs, {"two": 3})
                self.assertEqual(result.attempts, 0)

                self.assertIn(result, default_task_backend.results)

    async def test_enqueue_task_async(self):
        for task in [test_tasks.noop_task, test_tasks.noop_task_async]:
            with self.subTest(task):
                result = await cast(Task, task).aenqueue()

                self.assertEqual(result.status, ResultStatus.READY)
                self.assertFalse(result.is_finished)
                self.assertIsNone(result.started_at)
                self.assertIsNone(result.last_attempted_at)
                self.assertIsNone(result.finished_at)
                with self.assertRaisesMessage(ValueError, "Task has not finished yet"):
                    result.return_value  # noqa:B018
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
        object.__setattr__(enqueued_result, "status", ResultStatus.SUCCEEDED)

        self.assertEqual(result.status, ResultStatus.READY)
        result.refresh()
        self.assertEqual(result.status, ResultStatus.SUCCEEDED)

    async def test_refresh_result_async(self):
        result = await default_task_backend.aenqueue(
            test_tasks.calculate_meaning_of_life, (), {}
        )

        enqueued_result = default_task_backend.results[0]
        object.__setattr__(enqueued_result, "status", ResultStatus.SUCCEEDED)

        self.assertEqual(result.status, ResultStatus.READY)
        await result.arefresh()
        self.assertEqual(result.status, ResultStatus.SUCCEEDED)

    async def test_get_missing_result(self):
        with self.assertRaises(ResultDoesNotExist):
            default_task_backend.get_result("123")

        with self.assertRaises(ResultDoesNotExist):
            await default_task_backend.aget_result("123")

    def test_enqueue_on_commit(self):
        self.assertTrue(
            default_task_backend._get_enqueue_on_commit_for_task(
                test_tasks.enqueue_on_commit_task
            )
        )

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
                InvalidTaskError, "Backend does not support async Tasks."
            ):
                default_task_backend.validate_task(test_tasks.noop_task_async)

    def test_check(self):
        errors = list(default_task_backend.check())
        self.assertEqual(len(errors), 0, errors)

    @override_settings(
        TASKS={
            "default": {
                "BACKEND": "django.tasks.backends.dummy.DummyBackend",
                "ENQUEUE_ON_COMMIT": True,
            }
        }
    )
    @mock.patch("django.tasks.backends.base.connections", ConnectionHandler({}))
    def test_enqueue_on_commit_with_no_databases(self):
        errors = list(default_task_backend.check())
        self.assertEqual(len(errors), 1)
        self.assertEqual(
            "ENQUEUE_ON_COMMIT cannot be used when no databases are configured.",
            errors[0].msg,
        )
        self.assertEqual("Set ENQUEUE_ON_COMMIT to False", errors[0].hint)

    def test_takes_context(self):
        result = test_tasks.get_task_id.enqueue()
        self.assertEqual(result.status, ResultStatus.READY)

    def test_clear(self):
        result = test_tasks.noop_task.enqueue()

        default_task_backend.get_result(result.id)

        default_task_backend.clear()

        with self.assertRaisesMessage(ResultDoesNotExist, result.id):
            default_task_backend.get_result(result.id)


class DummyBackendTransactionTestCase(TransactionTestCase):
    available_apps = []

    @override_settings(
        TASKS={
            "default": {
                "BACKEND": "django.tasks.backends.dummy.DummyBackend",
                "ENQUEUE_ON_COMMIT": True,
            }
        }
    )
    def test_wait_until_transaction_commit(self):
        self.assertTrue(default_task_backend.enqueue_on_commit)
        self.assertTrue(
            default_task_backend._get_enqueue_on_commit_for_task(test_tasks.noop_task)
        )

        with transaction.atomic():
            test_tasks.noop_task.enqueue()

            self.assertEqual(len(default_task_backend.results), 0)

        self.assertEqual(len(default_task_backend.results), 1)

    @override_settings(
        TASKS={
            "default": {
                "BACKEND": "django.tasks.backends.dummy.DummyBackend",
                "ENQUEUE_ON_COMMIT": False,
            }
        }
    )
    def test_doesnt_wait_until_transaction_commit(self):
        self.assertFalse(default_task_backend.enqueue_on_commit)
        self.assertFalse(
            default_task_backend._get_enqueue_on_commit_for_task(test_tasks.noop_task)
        )

        with transaction.atomic():
            result = test_tasks.noop_task.enqueue()

            self.assertIsNotNone(result.enqueued_at)

            self.assertEqual(len(default_task_backend.results), 1)

        self.assertEqual(len(default_task_backend.results), 1)

    @override_settings(
        TASKS={
            "default": {
                "BACKEND": "django.tasks.backends.dummy.DummyBackend",
            }
        }
    )
    def test_wait_until_transaction_by_default(self):
        self.assertTrue(default_task_backend.enqueue_on_commit)
        self.assertTrue(
            default_task_backend._get_enqueue_on_commit_for_task(test_tasks.noop_task)
        )

        with transaction.atomic():
            result = test_tasks.noop_task.enqueue()

            self.assertIsNone(result.enqueued_at)

            self.assertEqual(len(default_task_backend.results), 0)

        self.assertEqual(len(default_task_backend.results), 1)
        self.assertIsNone(result.enqueued_at)
        result.refresh()
        self.assertIsNotNone(result.enqueued_at)

    @override_settings(
        TASKS={
            "default": {
                "BACKEND": "django.tasks.backends.dummy.DummyBackend",
                "ENQUEUE_ON_COMMIT": False,
            }
        }
    )
    def test_task_specific_enqueue_on_commit(self):
        self.assertFalse(default_task_backend.enqueue_on_commit)
        self.assertTrue(test_tasks.enqueue_on_commit_task.enqueue_on_commit)
        self.assertTrue(
            default_task_backend._get_enqueue_on_commit_for_task(
                test_tasks.enqueue_on_commit_task
            )
        )

        with transaction.atomic():
            result = test_tasks.enqueue_on_commit_task.enqueue()

            self.assertIsNone(result.enqueued_at)

            self.assertEqual(len(default_task_backend.results), 0)

        self.assertEqual(len(default_task_backend.results), 1)
        self.assertIsNone(result.enqueued_at)
        result.refresh()
        self.assertIsNotNone(result.enqueued_at)
