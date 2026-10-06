import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
from unittest import mock

from asgiref.sync import async_to_sync, sync_to_async

from django.db import connection, connections, transaction
from django.test import TestCase, TransactionTestCase, skipUnlessDBFeature

from .models import Reporter


def current_thread_and_connection():
    return threading.current_thread(), connections["default"]


def current_transaction_state():
    """Snapshot the state that rejected atomic entry must leave unchanged."""
    return {
        "thread_and_connection": current_thread_and_connection(),
        "atomic_blocks": tuple(connection.atomic_blocks),
        "savepoint_ids": tuple(connection.savepoint_ids),
        "savepoint_counter": connection.savepoint_state,
        "owning_tasks": tuple(connection._async_atomic_tasks),
    }


@skipUnlessDBFeature("uses_savepoints")
class AsyncAtomicTests(TransactionTestCase):
    available_apps = ["transactions"]

    async def test_commit(self):
        async with transaction.atomic():
            await Reporter.objects.acreate(first_name="Tintin")
        self.assertEqual(
            [r.first_name async for r in Reporter.objects.all()], ["Tintin"]
        )

    async def test_rollback(self):
        with self.assertRaisesMessage(Exception, "Oops"):
            async with transaction.atomic():
                await Reporter.objects.acreate(first_name="Haddock")
                raise Exception("Oops, that's his last name")
        self.assertEqual(await Reporter.objects.acount(), 0)

    async def test_nested_rollback_commit(self):
        async with transaction.atomic():
            await Reporter.objects.acreate(last_name="Tintin")
            with self.assertRaisesMessage(Exception, "Oops"):
                async with transaction.atomic():
                    await Reporter.objects.acreate(first_name="Haddock")
                    raise Exception("Oops, that's his last name")
        self.assertEqual(
            [r.last_name async for r in Reporter.objects.all()], ["Tintin"]
        )

    async def test_nested_commit_rollback(self):
        with self.assertRaisesMessage(Exception, "Oops"):
            async with transaction.atomic():
                async with transaction.atomic():
                    await Reporter.objects.acreate(first_name="Tintin")
                raise Exception("Oops, that's his first name")
        self.assertEqual(await Reporter.objects.acount(), 0)

    async def test_reuse_nested(self):
        atomic = transaction.atomic()
        async with atomic:
            await Reporter.objects.acreate(first_name="Tintin")
            with self.assertRaisesMessage(Exception, "Oops"):
                async with atomic:
                    await Reporter.objects.acreate(first_name="Haddock")
                    raise Exception("Oops, that's his last name")
        self.assertEqual(await Reporter.objects.acount(), 1)

    async def test_awaited_coroutine_can_nest(self):
        """An ordinary await keeps transaction ownership in the same task."""
        get = sync_to_async(current_thread_and_connection)

        async def create():
            async with transaction.atomic():
                self.assertEqual(await get(), parent)
                await Reporter.objects.acreate(first_name="Tintin")

        with self.assertRaisesMessage(ValueError, "Undo parent"):
            async with transaction.atomic():
                parent = await get()
                await create()
                raise ValueError("Undo parent")
        self.assertEqual(await Reporter.objects.acount(), 0)

    async def test_sync_atomic_inside_async_atomic(self):
        def create_and_fail():
            with transaction.atomic():
                Reporter.objects.create(first_name="Haddock")
                raise Exception("Oops, that's his last name")

        async with transaction.atomic():
            await Reporter.objects.acreate(first_name="Tintin")
            with self.assertRaisesMessage(Exception, "Oops"):
                await sync_to_async(create_and_fail)()
        self.assertEqual(await Reporter.objects.acount(), 1)

    async def test_outermost_block_uses_own_thread_and_connection(self):
        get = sync_to_async(current_thread_and_connection)
        outer_thread, outer_connection = await get()
        async with transaction.atomic():
            block_thread, block_connection = await get()
            async with transaction.atomic():
                nested_thread, nested_connection = await get()
            # Leaving a nested block keeps the outermost block's worker.
            self.assertEqual(await get(), (block_thread, block_connection))
        self.assertEqual(await get(), (outer_thread, outer_connection))
        self.assertIsNot(block_thread, outer_thread)
        self.assertIsNot(block_connection, outer_connection)
        self.assertIs(nested_thread, block_thread)
        self.assertIs(nested_connection, block_connection)

    async def test_child_task_cannot_enter_atomic(self):
        """Reject child entry without a new worker or savepoint changes."""
        get_state = sync_to_async(current_transaction_state)
        callbacks = []

        async def child(**options):
            async with transaction.atomic(**options):
                self.fail("A child task must not enter an async atomic block.")

        # Open a parent transaction and savepoint before creating children.
        async with transaction.atomic():
            await Reporter.objects.acreate(first_name="Tintin")
            await sync_to_async(transaction.on_commit)(
                lambda: callbacks.append("parent")
            )
            async with transaction.atomic():
                parent_state = await get_state()
                # Rejection must not change parent state or create a worker.
                with mock.patch(
                    "django.db.transaction.ThreadPoolExecutor", wraps=ThreadPoolExecutor
                ) as create_worker:
                    for options in ({}, {"savepoint": False}, {"durable": True}):
                        with self.subTest(options=options):
                            with self.assertRaisesMessage(
                                transaction.TransactionManagementError,
                                "Cannot enter an async atomic block in another "
                                "task's atomic context.",
                            ):
                                async with asyncio.timeout(10):
                                    await asyncio.create_task(child(**options))
                            self.assertEqual(await get_state(), parent_state)
                    create_worker.assert_not_called()
                # The parent must still be able to write and commit.
                await Reporter.objects.acreate(first_name="Haddock")
            self.assertEqual(callbacks, [])
        self.assertEqual(callbacks, ["parent"])
        self.assertEqual(
            [r.first_name async for r in Reporter.objects.order_by("first_name")],
            ["Haddock", "Tintin"],
        )

    async def test_reuse_atomic_in_child_task_is_rejected(self):
        """A rejected child does not prevent same-task reuse of the manager."""
        atomic = transaction.atomic()
        get_state = sync_to_async(current_transaction_state)

        async def child():
            async with atomic:
                self.fail("A child task must not enter an async atomic block.")

        async with atomic:
            before = await get_state()
            with self.assertRaisesMessage(
                transaction.TransactionManagementError,
                "Cannot enter an async atomic block in another task's atomic context.",
            ):
                async with asyncio.timeout(10):
                    await asyncio.create_task(child())
            self.assertEqual(await get_state(), before)
            async with atomic:
                await Reporter.objects.acreate(first_name="Tintin")
        self.assertEqual(await Reporter.objects.acount(), 1)

    async def test_child_entry_after_parent_exit_is_rejected(self):
        """Reject an inherited context even after its worker has stopped."""
        release = asyncio.Event()
        get = sync_to_async(current_thread_and_connection)

        async def child():
            await release.wait()
            with self.assertRaisesMessage(
                transaction.TransactionManagementError,
                "Cannot enter an async atomic block in another task's atomic context.",
            ):
                async with transaction.atomic():
                    self.fail("A child task must not enter an async atomic block.")

        async with asyncio.timeout(10), asyncio.TaskGroup() as tasks:
            async with transaction.atomic():
                parent_thread, _ = await get()
                tasks.create_task(child())
            await asyncio.to_thread(parent_thread.join, 5)
            self.assertIs(parent_thread.is_alive(), False)
            release.set()

    async def test_rejected_children_preserve_parent_rollback(self):
        """Repeated child rejections leave the owner's rollback intact."""
        callbacks = []

        async def child():
            with self.assertRaisesMessage(
                transaction.TransactionManagementError,
                "Cannot enter an async atomic block in another task's atomic context.",
            ):
                async with transaction.atomic():
                    self.fail("A child task must not enter an async atomic block.")

        with self.assertRaisesMessage(ValueError, "Undo parent"):
            async with transaction.atomic():
                await Reporter.objects.acreate(first_name="Tintin")
                await sync_to_async(transaction.on_commit)(
                    lambda: callbacks.append("parent")
                )
                async with asyncio.timeout(10), asyncio.TaskGroup() as tasks:
                    tasks.create_task(child())
                    tasks.create_task(child())
                async with transaction.atomic():
                    await Reporter.objects.acreate(first_name="Haddock")
                raise ValueError("Undo parent")
        self.assertEqual(await Reporter.objects.acount(), 0)
        self.assertEqual(callbacks, [])

    async def test_unhandled_child_rejection_rolls_back_parent(self):
        """An unhandled child rejection rolls back the parent."""
        get = sync_to_async(current_thread_and_connection)
        parent = await get()
        callbacks = []

        async def child():
            async with transaction.atomic():
                self.fail("A child task must not enter an async atomic block.")

        with self.assertRaises(ExceptionGroup) as raised:
            async with transaction.atomic():
                worker, _ = await get()
                await Reporter.objects.acreate(first_name="Tintin")
                await sync_to_async(transaction.on_commit)(
                    lambda: callbacks.append("parent")
                )
                async with asyncio.timeout(10), asyncio.TaskGroup() as tasks:
                    tasks.create_task(child())
        errors = raised.exception.exceptions
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], transaction.TransactionManagementError)
        self.assertEqual(
            str(errors[0]),
            "Cannot enter an async atomic block in another task's atomic context.",
        )
        self.assertEqual(await Reporter.objects.acount(), 0)
        self.assertEqual(callbacks, [])
        self.assertEqual(await get(), parent)
        await asyncio.to_thread(worker.join, 5)
        self.assertIs(worker.is_alive(), False)

    async def test_cancellation_rolls_back_transaction(self):
        """Cancelling the owner rolls back its writes and stops its worker."""
        ready = asyncio.Event()
        get = sync_to_async(current_thread_and_connection)
        callbacks = []
        workers = []
        parent = await get()

        async def owner():
            try:
                async with transaction.atomic():
                    workers.append(await get())
                    await Reporter.objects.acreate(first_name="Tintin")
                    await sync_to_async(transaction.on_commit)(
                        lambda: callbacks.append("owner")
                    )
                    ready.set()
                    await asyncio.Event().wait()
            finally:
                self.assertEqual(await get(), parent)

        async with asyncio.timeout(10), asyncio.TaskGroup() as tasks:
            task = tasks.create_task(owner())
            await ready.wait()
            task.cancel()
        self.assertIs(task.cancelled(), True)
        self.assertEqual(await Reporter.objects.acount(), 0)
        self.assertEqual(callbacks, [])
        worker, _ = workers[0]
        self.assertIsNot(worker, parent[0])
        await asyncio.to_thread(worker.join, 5)
        self.assertIs(worker.is_alive(), False)

    async def test_exit_from_another_task_is_rejected(self):
        """Cross-task exit must not pop or close the parent's transaction."""
        atomic = transaction.atomic()
        get = sync_to_async(current_thread_and_connection)
        async with atomic:
            parent = await get()
            with self.assertRaisesMessage(
                transaction.TransactionManagementError,
                "An async atomic block must be exited in the task that entered it.",
            ):
                await asyncio.create_task(atomic.__aexit__(None, None, None))
            self.assertEqual(await get(), parent)
            self.assertIs(
                await sync_to_async(lambda: connection.in_atomic_block)(), True
            )
            await Reporter.objects.acreate(first_name="Tintin")
        self.assertEqual(await Reporter.objects.acount(), 1)

    async def test_async_bridge_task_cannot_enter_atomic(self):
        """An async bridge cannot transfer ownership to its new task."""
        get_state = sync_to_async(current_transaction_state)

        async def callback():
            async with transaction.atomic():
                self.fail("A bridge task must not enter an async atomic block.")

        async with transaction.atomic():
            before = await get_state()
            with self.assertRaisesMessage(
                transaction.TransactionManagementError,
                "Cannot enter an async atomic block in another task's atomic context.",
            ):
                async with asyncio.timeout(10):
                    await sync_to_async(async_to_sync(callback))()
            self.assertEqual(await get_state(), before)
            async with transaction.atomic():
                await Reporter.objects.acreate(first_name="Tintin")
        self.assertEqual(await Reporter.objects.acount(), 1)

    async def test_async_block_joins_synchronous_transaction(self):
        """An async bridge can join an existing synchronous transaction."""

        async def callback():
            async with transaction.atomic():
                self.assertEqual(await Reporter.objects.acount(), 1)
                await Reporter.objects.acreate(first_name="Haddock")

        def sync_caller():
            with transaction.atomic():
                Reporter.objects.create(first_name="Tintin")
                async_to_sync(callback)()
                raise ValueError("Undo both writes")

        with self.assertRaisesMessage(ValueError, "Undo both writes"):
            await sync_to_async(sync_caller)()
        self.assertEqual(await Reporter.objects.acount(), 0)

    async def test_synchronous_parent_rejects_overlapping_tasks(self):
        """Tasks cannot overlap savepoints in an inherited sync transaction."""
        # Order: A enters, B is rejected, A rolls back, then C succeeds.
        events = {
            name: asyncio.Event() for name in ("a_entered", "b_attempted", "a_exited")
        }

        async def rollback_a():
            try:
                with self.assertRaisesMessage(ValueError, "Undo A"):
                    async with transaction.atomic():
                        await Reporter.objects.acreate(first_name="Haddock")
                        async with transaction.atomic():
                            self.assertEqual(await Reporter.objects.acount(), 2)
                        events["a_entered"].set()
                        await events["b_attempted"].wait()
                        raise ValueError("Undo A")
            finally:
                events["a_exited"].set()

        async def overlap_b():
            await events["a_entered"].wait()
            try:
                async with transaction.atomic():
                    await Reporter.objects.acreate(first_name="Sakharine")
                    events["b_attempted"].set()
                    # If entry is wrongly allowed, keep B open until A exits.
                    # This reproduces the unsafe savepoint order.
                    await events["a_exited"].wait()
            except transaction.TransactionManagementError as exc:
                return str(exc)
            finally:
                events["b_attempted"].set()

        async def write_c():
            async with transaction.atomic():
                await Reporter.objects.acreate(first_name="Calculus")

        async def run_tasks():
            async with asyncio.timeout(10), asyncio.TaskGroup() as tasks:
                tasks.create_task(rollback_a())
                rejected_task = tasks.create_task(overlap_b())
            # A new task can use the parent after rejection and rollback.
            await asyncio.create_task(write_c())
            return rejected_task.result()

        def sync_parent():
            with transaction.atomic():
                Reporter.objects.create(first_name="Tintin")
                return async_to_sync(run_tasks)()

        rejection_message = await sync_to_async(sync_parent)()
        self.assertEqual(
            [r.first_name async for r in Reporter.objects.order_by("first_name")],
            ["Calculus", "Tintin"],
        )
        self.assertEqual(
            rejection_message,
            "Cannot enter an async atomic block while another task is using "
            "this connection's transaction.",
        )

    async def test_synchronous_parent_reusable_after_async_errors(self):
        """Failed entry or exit must release task ownership."""

        async def successful_block():
            async with transaction.atomic():
                async with transaction.atomic():
                    await Reporter.objects.acreate(first_name="Calculus")

        async def callback():
            for method in ("__enter__", "__exit__"):
                atomic = transaction.atomic()
                original = getattr(atomic, method)

                def fail(*args):
                    if method == "__exit__":
                        original(*args)
                    raise ValueError("Atomic failed")

                async def failing_block():
                    with self.assertRaisesMessage(ValueError, "Atomic failed"):
                        async with atomic:
                            pass

                with mock.patch.object(atomic, method, side_effect=fail):
                    await asyncio.create_task(failing_block())
                await asyncio.create_task(successful_block())

        def sync_caller():
            with transaction.atomic():
                async_to_sync(callback)()
                self.assertEqual(Reporter.objects.count(), 2)
                raise ValueError("Undo parent")

        with self.assertRaisesMessage(ValueError, "Undo parent"):
            await sync_to_async(sync_caller)()
        self.assertEqual(await Reporter.objects.acount(), 0)

    async def test_synchronous_parent_reusable_after_async_cancellation(self):
        """Cancelling an async block releases ownership, not its parent."""
        ready = asyncio.Event()
        callbacks = []

        async def cancelled_block():
            async with transaction.atomic():
                await Reporter.objects.acreate(first_name="Haddock")
                await sync_to_async(transaction.on_commit)(
                    lambda: callbacks.append("cancelled")
                )
                ready.set()
                await asyncio.Event().wait()

        async def successful_block():
            async with transaction.atomic():
                self.assertEqual(await Reporter.objects.acount(), 1)
                await Reporter.objects.acreate(first_name="Calculus")
                await sync_to_async(transaction.on_commit)(
                    lambda: callbacks.append("successful")
                )

        async def callback():
            async with asyncio.timeout(10), asyncio.TaskGroup() as tasks:
                task = tasks.create_task(cancelled_block())
                await ready.wait()
                task.cancel()
            self.assertIs(task.cancelled(), True)
            await asyncio.create_task(successful_block())
            self.assertEqual(callbacks, [])

        def sync_caller():
            with transaction.atomic():
                Reporter.objects.create(first_name="Tintin")
                async_to_sync(callback)()

        await sync_to_async(sync_caller)()
        self.assertEqual(
            [r.first_name async for r in Reporter.objects.order_by("first_name")],
            ["Calculus", "Tintin"],
        )
        self.assertEqual(callbacks, ["successful"])

    async def test_child_without_atomic_uses_parent_transaction(self):
        """Creating a task alone does not isolate its ORM calls."""
        get = sync_to_async(current_thread_and_connection)

        async def child():
            self.assertEqual(await get(), parent)
            await Reporter.objects.acreate(first_name="Haddock")

        with self.assertRaisesMessage(ValueError, "Undo parent"):
            async with transaction.atomic():
                parent = await get()
                async with asyncio.timeout(10):
                    await asyncio.create_task(child())
                raise ValueError("Undo parent")
        self.assertEqual(await Reporter.objects.acount(), 0)

    async def test_worker_not_reused(self):
        get = sync_to_async(current_thread_and_connection)
        async with transaction.atomic():
            first_thread, first_connection = await get()
        async with transaction.atomic():
            second_thread, second_connection = await get()
        self.assertIsNot(first_thread, second_thread)
        self.assertIsNot(first_connection, second_connection)
        for thread in (first_thread, second_thread):
            await asyncio.to_thread(thread.join, 5)
            self.assertIs(thread.is_alive(), False)

    async def test_worker_closed_on_enter_error(self):
        get = sync_to_async(current_thread_and_connection)
        parent = await get()
        atomic = transaction.atomic()
        cleanup_threads = []
        close_all = connections.close_all

        def cleanup():
            cleanup_threads.append(threading.current_thread())
            close_all()

        with (
            mock.patch.object(atomic, "__enter__", side_effect=RuntimeError("Oops")),
            mock.patch.object(connections, "close_all", side_effect=cleanup),
        ):
            with self.assertRaisesMessage(RuntimeError, "Oops"):
                async with atomic:
                    self.fail("Atomic entry should fail")
        self.assertEqual(await get(), parent)
        self.assertEqual(len(cleanup_threads), 1)
        thread = cleanup_threads[0]
        self.assertIsNot(thread, parent[0])
        await asyncio.to_thread(thread.join, 5)
        self.assertIs(thread.is_alive(), False)

    async def test_cancellation_does_not_cancel_queued_cleanup(self):
        """Connection cleanup still runs if its owning task is cancelled."""
        # Block the worker, queue cleanup, cancel the owner, then release the
        # worker and check that cleanup still runs.
        get_thread_and_connection = sync_to_async(current_thread_and_connection)
        original_thread_and_connection = await get_thread_and_connection()
        loop = asyncio.get_running_loop()
        worker_blocked = asyncio.Event()
        release_worker = threading.Event()
        cleanup_finished = threading.Event()
        worker_threads = []
        original_close_all = connections.close_all
        executor = ThreadPoolExecutor(max_workers=1)
        original_submit = executor.submit

        def block_worker():
            worker_threads.append(threading.current_thread())
            loop.call_soon_threadsafe(worker_blocked.set)
            release_worker.wait(10)

        def close_connections():
            self.assertIs(threading.current_thread(), worker_threads[0])
            original_close_all()
            cleanup_finished.set()

        def queue_blocker_before_cleanup(func, *args, **kwargs):
            if func is connections.close_all:
                # Hold the worker so cleanup is queued, but has not started.
                original_submit(block_worker)
            return original_submit(func, *args, **kwargs)

        async def own_transaction():
            try:
                async with transaction.atomic():
                    pass
            finally:
                # The original thread and connection must already be restored.
                self.assertEqual(
                    await get_thread_and_connection(), original_thread_and_connection
                )

        with (
            mock.patch(
                "django.db.transaction.ThreadPoolExecutor", return_value=executor
            ),
            mock.patch.object(
                executor, "submit", side_effect=queue_blocker_before_cleanup
            ),
            mock.patch.object(connections, "close_all", side_effect=close_connections),
        ):
            owner_task = asyncio.create_task(own_transaction())
            try:
                await asyncio.wait_for(worker_blocked.wait(), 5)
                owner_task.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await asyncio.wait_for(owner_task, 5)
                # The owner has stopped, but cleanup must still be waiting.
                self.assertIs(cleanup_finished.is_set(), False)
            finally:
                release_worker.set()
                await asyncio.gather(owner_task, return_exceptions=True)
                executor.shutdown(wait=False)
                for thread in worker_threads:
                    await asyncio.to_thread(thread.join, 5)
                    self.assertIs(thread.is_alive(), False)
        self.assertIs(cleanup_finished.is_set(), True)

    async def test_error_on_enter(self):
        async with transaction.atomic():
            await Reporter.objects.acreate(first_name="Tintin")
            with self.assertRaisesMessage(RuntimeError, "durable"):
                async with transaction.atomic(durable=True):
                    pass
            # The enclosing block is still usable.
            await Reporter.objects.acreate(first_name="Haddock")
        self.assertEqual(await Reporter.objects.acount(), 2)

    async def test_on_commit(self):
        callbacks = []
        async with transaction.atomic():
            await sync_to_async(transaction.on_commit)(lambda: callbacks.append(1))
            self.assertEqual(callbacks, [])
        self.assertEqual(callbacks, [1])

    async def test_outer_connection_not_in_transaction(self):
        async with transaction.atomic():
            self.assertIs(
                await sync_to_async(lambda: connection.in_atomic_block)(), True
            )
        self.assertIs(await sync_to_async(lambda: connection.in_atomic_block)(), False)


# The database must allow a transaction on one connection while other
# connections write, so these tests can't use an in-memory SQLite database.
@skipUnlessDBFeature("uses_savepoints", "test_db_allows_multiple_connections")
class AsyncAtomicIsolationTests(TransactionTestCase):
    available_apps = ["transactions"]

    async def test_connection_closed_on_exit(self):
        get = sync_to_async(current_thread_and_connection)
        for max_age in (0, None):
            with (
                self.subTest(CONN_MAX_AGE=max_age),
                mock.patch.dict(connection.settings_dict, CONN_MAX_AGE=max_age),
            ):
                async with transaction.atomic():
                    await Reporter.objects.acreate(first_name="Tintin")
                    block_thread, block_connection = await get()
                    self.assertIsNotNone(block_connection.connection)
                self.assertIsNone(block_connection.connection)
                await asyncio.to_thread(block_thread.join, 5)
                self.assertIs(block_thread.is_alive(), False)

    async def test_rollback_does_not_undo_other_task(self):
        transaction_started = asyncio.Event()
        other_write_finished = asyncio.Event()

        async def task_one():
            with self.assertRaisesMessage(ValueError, "Undo my work"):
                async with transaction.atomic():
                    await Reporter.objects.acreate(first_name="Tintin")
                    transaction_started.set()
                    await other_write_finished.wait()
                    raise ValueError("Undo my work")

        async def task_two():
            await transaction_started.wait()
            # This is outside the atomic block.
            await Reporter.objects.acreate(first_name="Haddock")
            other_write_finished.set()

        await asyncio.gather(task_one(), task_two())
        self.assertEqual(
            [r.first_name async for r in Reporter.objects.all()], ["Haddock"]
        )

    async def test_concurrent_transactions(self):
        both_started = asyncio.Barrier(2)

        async def create(name, fail):
            async with transaction.atomic():
                await Reporter.objects.acreate(first_name=name)
                await both_started.wait()
                if fail:
                    raise ValueError(name)

        async with asyncio.timeout(10):
            results = await asyncio.gather(
                create("Tintin", fail=False),
                create("Haddock", fail=True),
                return_exceptions=True,
            )
        self.assertIsNone(results[0])
        self.assertIsInstance(results[1], ValueError)
        self.assertEqual(
            [r.first_name async for r in Reporter.objects.all()], ["Tintin"]
        )


@skipUnlessDBFeature("uses_savepoints")
class AsyncAtomicMultipleDatabaseTests(TransactionTestCase):
    available_apps = ["transactions"]
    databases = {"default", "other"}

    async def test_synchronous_parents_allow_tasks_on_separate_connections(self):
        """Ownership belongs to each connection, not to the worker thread."""
        both_entered = asyncio.Barrier(2)

        async def child(using):
            async with transaction.atomic(using=using):
                await Reporter.objects.using(using).acreate(first_name="Tintin")
                await both_entered.wait()

        async def callback():
            async with asyncio.timeout(10), asyncio.TaskGroup() as tasks:
                for using in self.databases:
                    tasks.create_task(child(using))

        def sync_caller():
            with transaction.atomic(), transaction.atomic(using="other"):
                async_to_sync(callback)()

        await sync_to_async(sync_caller)()
        for using in self.databases:
            self.assertEqual(await Reporter.objects.using(using).acount(), 1)


@skipUnlessDBFeature("uses_savepoints")
class AsyncAtomicInsideTestCaseTests(TestCase):
    """
    TestCase runs async tests with async_to_sync(), inside an atomic block on
    the test thread. An async atomic block must join that transaction.
    """

    @classmethod
    def setUpTestData(cls):
        Reporter.objects.create(first_name="Tintin")

    async def test_sees_test_data(self):
        async with transaction.atomic():
            self.assertEqual(await Reporter.objects.acount(), 1)

    async def test_uses_test_connection(self):
        get = sync_to_async(current_thread_and_connection)
        test_thread_and_connection = await get()
        async with transaction.atomic():
            self.assertEqual(await get(), test_thread_and_connection)

    async def test_rollback(self):
        with self.assertRaisesMessage(Exception, "Oops"):
            async with transaction.atomic():
                await Reporter.objects.acreate(first_name="Haddock")
                raise Exception("Oops, that's his last name")
        self.assertEqual(await Reporter.objects.acount(), 1)

    async def test_durable(self):
        async with transaction.atomic(durable=True):
            await Reporter.objects.acreate(first_name="Haddock")
        self.assertEqual(await Reporter.objects.acount(), 2)
