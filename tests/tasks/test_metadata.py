import pickle
from unittest import mock

from django.tasks import default_task_backend, task_backends
from django.tasks.backends.base import BaseTaskBackend
from django.tasks.backends.immediate import ImmediateBackend
from django.tasks.base import TaskContext, TaskResultStatus
from django.tasks.exceptions import InvalidTask
from django.test import SimpleTestCase, override_settings

from . import tasks as test_tasks


class NoMetadataBackend(BaseTaskBackend):
    def enqueue(self, task, args, kwargs):
        pass


class SyncSaveMetadataBackend(BaseTaskBackend):
    supports_metadata = True

    def enqueue(self, task, args, kwargs):
        pass

    def save_metadata(self, task_result, metadata):
        self.saved = metadata


class AsyncSaveMetadataBackend(SyncSaveMetadataBackend):
    save_metadata = BaseTaskBackend.save_metadata

    async def asave_metadata(self, task_result, metadata):
        self.saved = metadata


def backend_path(backend_class):
    return f"{backend_class.__module__}.{backend_class.__qualname__}"


@override_settings(
    TASKS={
        "default": {
            "BACKEND": "django.tasks.backends.immediate.ImmediateBackend",
            "QUEUES": [],
        },
        "dummy": {"BACKEND": "django.tasks.backends.dummy.DummyBackend"},
        "no_metadata": {"BACKEND": backend_path(NoMetadataBackend)},
        "sync_save": {"BACKEND": backend_path(SyncSaveMetadataBackend)},
        "async_save": {"BACKEND": backend_path(AsyncSaveMetadataBackend)},
    }
)
class TaskMetadataTestCase(SimpleTestCase):
    def test_using_metadata(self):
        task = test_tasks.noop_task.using(metadata={"trace_id": 123})

        self.assertEqual(task.metadata, {"trace_id": 123})
        self.assertEqual(test_tasks.noop_task.metadata, {})
        self.assertEqual(task.using(priority=1).metadata, {"trace_id": 123})
        self.assertEqual(task.using(metadata={}).metadata, {})

    def test_task_with_metadata_is_hashable(self):
        task = test_tasks.noop_task.using(metadata={"trace_id": 123})

        self.assertEqual(hash(task), hash(test_tasks.noop_task))
        self.assertNotEqual(task, test_tasks.noop_task)

    def test_task_with_metadata_is_picklable(self):
        task = test_tasks.noop_task.using(metadata={"trace_id": 123})

        self.assertEqual(pickle.loads(pickle.dumps(task)), task)

    def test_invalid_metadata(self):
        tests = [
            ([("a", 1)], "metadata must be a dict."),
            ({1: "a"}, "metadata keys must be strings."),
            ({"a": object()}, "metadata must be JSON-serializable"),
        ]
        for metadata, message in tests:
            with self.subTest(metadata=metadata):
                with self.assertRaisesMessage(InvalidTask, message):
                    test_tasks.noop_task.using(metadata=metadata)

    def test_backend_without_metadata_support(self):
        task = test_tasks.noop_task.using(backend="no_metadata")
        self.assertIs(task.get_backend().supports_metadata, False)

        with self.assertRaisesMessage(
            InvalidTask, "Backend does not support metadata."
        ):
            task.using(metadata={"trace_id": 123})
        # Empty metadata is allowed.
        task.using(metadata={})

    def test_enqueue_with_metadata(self):
        result = test_tasks.get_metadata.using(
            metadata={"trace_id": 123, "tags": ("a", "b")}
        ).enqueue()

        self.assertEqual(result.status, TaskResultStatus.SUCCESSFUL)
        self.assertEqual(result.return_value, {"trace_id": 123, "tags": ["a", "b"]})
        self.assertEqual(result.metadata, {"trace_id": 123, "tags": ["a", "b"]})

    def test_reserved_keys_are_hidden(self):
        result = test_tasks.get_metadata.using(
            metadata={"trace_id": 123, "_django_internal": 1, "_lib": 2}
        ).enqueue()

        self.assertEqual(result.return_value, {"trace_id": 123})
        self.assertEqual(result.metadata, {"trace_id": 123})
        self.assertEqual(
            result.raw_metadata, {"trace_id": 123, "_django_internal": 1, "_lib": 2}
        )

    def test_result_metadata_is_a_copy(self):
        result = test_tasks.noop_task.using(metadata={"trace_id": 123}).enqueue()

        result.metadata["trace_id"] = 456
        self.assertEqual(result.metadata, {"trace_id": 123})

    def test_modified_metadata_saved_on_success(self):
        result = test_tasks.update_metadata.using(metadata={"a": 1}).enqueue(b=2)

        self.assertEqual(result.status, TaskResultStatus.SUCCESSFUL)
        self.assertEqual(result.metadata, {"a": 1, "b": 2})

    async def test_modified_metadata_saved_on_success_async(self):
        result = await test_tasks.update_metadata_async.using(
            metadata={"a": 1}
        ).aenqueue(b=2)

        self.assertEqual(result.status, TaskResultStatus.SUCCESSFUL)
        self.assertEqual(result.metadata, {"a": 1, "b": 2})

    def test_modified_metadata_saved_on_failure(self):
        result = test_tasks.update_metadata_and_fail.enqueue(b=2)

        self.assertEqual(result.status, TaskResultStatus.FAILED)
        self.assertEqual(result.metadata, {"b": 2})

    def test_modified_nested_metadata_saved(self):
        result = test_tasks.append_to_metadata_list.using(
            metadata={"items": [1]}
        ).enqueue("items", 2)

        self.assertEqual(result.status, TaskResultStatus.SUCCESSFUL)
        self.assertEqual(result.metadata, {"items": [1, 2]})

    def test_unmodified_metadata_not_saved(self):
        with mock.patch.object(ImmediateBackend, "save_metadata") as save_metadata:
            test_tasks.get_metadata.using(metadata={"a": 1}).enqueue()

        save_metadata.assert_not_called()

    def test_invalid_modified_metadata_fails_task(self):
        result = test_tasks.set_invalid_metadata.enqueue()

        self.assertEqual(result.status, TaskResultStatus.FAILED)
        self.assertEqual(result.errors[0].exception_class, TypeError)
        self.assertEqual(result.metadata, {})

    def test_save_metadata(self):
        result = test_tasks.save_metadata_explicitly.enqueue("a", 1)

        self.assertEqual(result.return_value, {"a": 1})
        self.assertEqual(result.metadata, {"a": 1})

    async def test_asave_metadata(self):
        result = await test_tasks.save_metadata_explicitly_async.aenqueue("a", 1)

        self.assertEqual(result.return_value, {"a": 1})
        self.assertEqual(result.metadata, {"a": 1})

    def test_save_preserves_reserved_keys(self):
        result = test_tasks.update_metadata.using(
            metadata={"_reserved": "backend", "a": 1}
        ).enqueue(_reserved="user", _other="user", b=2)

        self.assertEqual(result.metadata, {"a": 1, "b": 2})
        self.assertEqual(result.raw_metadata, {"_reserved": "backend", "a": 1, "b": 2})

    def test_dummy_backend_save_metadata(self):
        task = test_tasks.noop_task.using(backend="dummy", metadata={"a": 1})
        result = task.enqueue()
        self.assertEqual(result.metadata, {"a": 1})

        context = TaskContext(task_result=result)
        context.metadata["b"] = 2
        self.assertIs(context.metadata_modified, True)
        context.save_metadata()
        self.assertIs(context.metadata_modified, False)

        stored_result = task_backends["dummy"].get_result(result.id)
        self.assertEqual(stored_result.metadata, {"a": 1, "b": 2})

        # Saving must not share state with the stored result.
        context.metadata["c"] = 3
        self.assertEqual(stored_result.metadata, {"a": 1, "b": 2})

    async def test_dummy_backend_asave_metadata(self):
        task = test_tasks.noop_task.using(backend="dummy", metadata={"a": 1})
        result = await task.aenqueue()

        context = TaskContext(task_result=result)
        context.metadata["b"] = 2
        await context.asave_metadata()

        stored_result = await task_backends["dummy"].aget_result(result.id)
        self.assertEqual(stored_result.metadata, {"a": 1, "b": 2})

    def test_refresh_metadata(self):
        task = test_tasks.noop_task.using(backend="dummy", metadata={"a": 1})
        result = task.enqueue()

        stored_result = task_backends["dummy"].get_result(result.id)
        object.__setattr__(stored_result, "raw_metadata", {"a": 2, "_x": 3})

        result.refresh()
        self.assertEqual(result.metadata, {"a": 2})
        self.assertEqual(result.raw_metadata, {"a": 2, "_x": 3})

    async def test_asave_metadata_falls_back_to_sync(self):
        backend = task_backends["sync_save"]

        await backend.asave_metadata(None, {"a": 1})
        self.assertEqual(backend.saved, {"a": 1})

    def test_save_metadata_falls_back_to_async(self):
        backend = task_backends["async_save"]

        backend.save_metadata(None, {"a": 1})
        self.assertEqual(backend.saved, {"a": 1})

    async def test_save_metadata_not_implemented(self):
        backend = task_backends["no_metadata"]
        message = "This backend does not support saving metadata."

        with self.assertRaisesMessage(NotImplementedError, message):
            backend.save_metadata(None, {})
        with self.assertRaisesMessage(NotImplementedError, message):
            await backend.asave_metadata(None, {})

    def test_default_backend_supports_metadata(self):
        self.assertIs(default_task_backend.supports_metadata, True)
        self.assertIs(task_backends["dummy"].supports_metadata, True)
