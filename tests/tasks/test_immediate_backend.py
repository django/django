from django.db import transaction
from django.tasks import TaskResultStatus, default_task_backend, task_backends
from django.tasks.backends.immediate import ImmediateBackend
from django.tasks.exceptions import InvalidTask
from django.test import SimpleTestCase, TransactionTestCase, override_settings
from django.utils import timezone

from . import tasks as test_tasks


@override_settings(
    TASKS={
        "default": {
            "BACKEND": "django.tasks.backends.immediate.ImmediateBackend",
            "QUEUES": [],
        }
    }
)
class ImmediateBackendTestCase(SimpleTestCase):
    def test_using_correct_backend(self):
        self.assertEqual(default_task_backend, task_backends["default"])
        self.assertIsInstance(task_backends["default"], ImmediateBackend)
        self.assertEqual(default_task_backend.alias, "default")
        self.assertEqual(default_task_backend.options, {})

    def test_enqueue_task(self):
        for task in [test_tasks.noop_task, test_tasks.noop_task_async]:
            with self.subTest(task):
                result = task.enqueue(1, two=3)

                self.assertEqual(result.status, TaskResultStatus.SUCCESSFUL)
                self.assertIs(result.is_finished, True)
                self.assertIsNotNone(result.started_at)
                self.assertIsNotNone(result.last_attempted_at)
                self.assertIsNotNone(result.finished_at)
                self.assertGreaterEqual(result.started_at, result.enqueued_at)
                self.assertGreaterEqual(result.finished_at, result.started_at)
                self.assertIsNone(result.return_value)
                self.assertEqual(result.task, task)
                self.assertEqual(result.args, [1])
                self.assertEqual(result.kwargs, {"two": 3})
                self.assertEqual(result.attempts, 1)

    async def test_enqueue_task_async(self):
        for task in [test_tasks.noop_task, test_tasks.noop_task_async]:
            with self.subTest(task):
                result = await task.aenqueue()

                self.assertEqual(result.status, TaskResultStatus.SUCCESSFUL)
                self.assertIs(result.is_finished, True)
                self.assertIsNotNone(result.started_at)
                self.assertIsNotNone(result.last_attempted_at)
                self.assertIsNotNone(result.finished_at)
                self.assertGreaterEqual(result.started_at, result.enqueued_at)
                self.assertGreaterEqual(result.finished_at, result.started_at)
                self.assertIsNone(result.return_value)
                self.assertEqual(result.task, task)
                self.assertEqual(result.args, [])
                self.assertEqual(result.kwargs, {})
                self.assertEqual(result.attempts, 1)

    def test_catches_exception(self):
        test_data = [
            (
                test_tasks.failing_task_value_error,  # Task function.
                ValueError,  # Expected exception.
                "This Task failed due to ValueError",  # Expected message.
            ),
            (
                test_tasks.failing_task_system_exit,
                SystemExit,
                "This Task failed due to SystemExit",
            ),
        ]
        for task, exception, message in test_data:
            with (
                self.subTest(task),
                self.assertLogs("django.tasks", level="ERROR") as captured_logs,
            ):
                result = task.enqueue()

                self.assertEqual(len(captured_logs.output), 1)
                self.assertIn(message, captured_logs.output[0])

                self.assertEqual(result.status, TaskResultStatus.FAILED)
                with self.assertRaisesMessage(ValueError, "Task failed"):
                    result.return_value
                self.assertIs(result.is_finished, True)
                self.assertIsNotNone(result.started_at)
                self.assertIsNotNone(result.last_attempted_at)
                self.assertIsNotNone(result.finished_at)
                self.assertGreaterEqual(result.started_at, result.enqueued_at)
                self.assertGreaterEqual(result.finished_at, result.started_at)
                self.assertEqual(result.errors[0].exception_class, exception)
                traceback = result.errors[0].traceback
                self.assertIs(
                    traceback
                    and traceback.endswith(f"{exception.__name__}: {message}\n"),
                    True,
                    traceback,
                )
                self.assertEqual(result.task, task)
                self.assertEqual(result.args, [])
                self.assertEqual(result.kwargs, {})

    def test_throws_keyboard_interrupt(self):
        with self.assertRaises(KeyboardInterrupt):
            with self.assertNoLogs("django.tasks", level="ERROR"):
                default_task_backend.enqueue(
                    test_tasks.failing_task_keyboard_interrupt, [], {}
                )

    def test_complex_exception(self):
        with self.assertLogs("django.tasks", level="ERROR"):
            result = test_tasks.complex_exception.enqueue()

        self.assertEqual(result.status, TaskResultStatus.FAILED)
        with self.assertRaisesMessage(ValueError, "Task failed"):
            result.return_value
        self.assertIsNotNone(result.started_at)
        self.assertIsNotNone(result.last_attempted_at)
        self.assertIsNotNone(result.finished_at)
        self.assertGreaterEqual(result.started_at, result.enqueued_at)
        self.assertGreaterEqual(result.finished_at, result.started_at)

        self.assertIsNone(result._return_value)
        self.assertEqual(result.errors[0].exception_class, ValueError)
        self.assertIn(
            'ValueError(ValueError("This task failed"))', result.errors[0].traceback
        )

        self.assertEqual(result.task, test_tasks.complex_exception)
        self.assertEqual(result.args, [])
        self.assertEqual(result.kwargs, {})

    def test_complex_return_value(self):
        with self.assertLogs("django.tasks", level="ERROR"):
            result = test_tasks.complex_return_value.enqueue()

        self.assertEqual(result.status, TaskResultStatus.FAILED)
        self.assertIsNotNone(result.started_at)
        self.assertIsNotNone(result.last_attempted_at)
        self.assertIsNotNone(result.finished_at)
        self.assertGreaterEqual(result.started_at, result.enqueued_at)
        self.assertGreaterEqual(result.finished_at, result.started_at)
        self.assertIsNone(result._return_value)
        self.assertEqual(result.errors[0].exception_class, TypeError)
        self.assertIn("Unsupported type", result.errors[0].traceback)

    def test_result(self):
        result = default_task_backend.enqueue(
            test_tasks.calculate_meaning_of_life, [], {}
        )

        self.assertEqual(result.status, TaskResultStatus.SUCCESSFUL)
        self.assertEqual(result.return_value, 42)

    async def test_result_async(self):
        result = await default_task_backend.aenqueue(
            test_tasks.calculate_meaning_of_life, [], {}
        )

        self.assertEqual(result.status, TaskResultStatus.SUCCESSFUL)
        self.assertEqual(result.return_value, 42)

    async def test_cannot_get_result(self):
        with self.assertRaisesMessage(
            NotImplementedError,
            "This backend does not support retrieving or refreshing results.",
        ):
            default_task_backend.get_result("123")

        with self.assertRaisesMessage(
            NotImplementedError,
            "This backend does not support retrieving or refreshing results.",
        ):
            await default_task_backend.aget_result(123)

    async def test_cannot_refresh_result(self):
        result = await default_task_backend.aenqueue(
            test_tasks.calculate_meaning_of_life, (), {}
        )

        with self.assertRaisesMessage(
            NotImplementedError,
            "This backend does not support retrieving or refreshing results.",
        ):
            await result.arefresh()

        with self.assertRaisesMessage(
            NotImplementedError,
            "This backend does not support retrieving or refreshing results.",
        ):
            result.refresh()

    def test_cannot_pass_run_after(self):
        with self.assertRaisesMessage(
            InvalidTask,
            "Backend does not support run_after.",
        ):
            default_task_backend.validate_task(
                test_tasks.failing_task_value_error.using(run_after=timezone.now())
            )

    def test_enqueue_logs(self):
        with self.assertLogs("django.tasks", level="DEBUG") as captured_logs:
            result = test_tasks.noop_task.enqueue()

        self.assertEqual(len(captured_logs.output), 3)

        self.assertIn("enqueued", captured_logs.output[0])
        self.assertIn(result.id, captured_logs.output[0])

        self.assertIn("state=RUNNING", captured_logs.output[1])
        self.assertIn(result.id, captured_logs.output[1])

        self.assertIn("state=SUCCESSFUL", captured_logs.output[2])
        self.assertIn(result.id, captured_logs.output[2])

    def test_failed_logs(self):
        with self.assertLogs("django.tasks", level="DEBUG") as captured_logs:
            result = test_tasks.failing_task_value_error.enqueue()

        self.assertEqual(len(captured_logs.output), 3)
        self.assertIn("state=RUNNING", captured_logs.output[1])
        self.assertIn(result.id, captured_logs.output[1])

        self.assertIn("state=FAILED", captured_logs.output[2])
        self.assertIn(result.id, captured_logs.output[2])

    def test_takes_context(self):
        result = test_tasks.get_task_id.enqueue()

        self.assertEqual(result.return_value, result.id)

    def test_context(self):
        result = test_tasks.test_context.enqueue(1)
        self.assertEqual(result.status, TaskResultStatus.SUCCESSFUL)

    def test_validate_on_enqueue(self):
        task_with_custom_queue_name = test_tasks.noop_task.using(
            queue_name="unknown_queue"
        )

        with override_settings(
            TASKS={
                "default": {
                    "BACKEND": "django.tasks.backends.immediate.ImmediateBackend",
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
                    "BACKEND": "django.tasks.backends.immediate.ImmediateBackend",
                    "QUEUES": ["queue-1"],
                }
            }
        ):
            with self.assertRaisesMessage(
                InvalidTask, "Queue 'unknown_queue' is not valid for backend"
            ):
                await task_with_custom_queue_name.aenqueue()


class ImmediateBackendTransactionTestCase(TransactionTestCase):
    available_apps = []

    @override_settings(
        TASKS={
            "default": {
                "BACKEND": "django.tasks.backends.immediate.ImmediateBackend",
            }
        }
    )
    def test_doesnt_wait_until_transaction_commit_by_default(self):
        with transaction.atomic():
            result = test_tasks.noop_task.enqueue()

            self.assertIsNotNone(result.enqueued_at)

            self.assertEqual(result.status, TaskResultStatus.SUCCESSFUL)

        self.assertEqual(result.status, TaskResultStatus.SUCCESSFUL)
