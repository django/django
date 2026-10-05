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

    async def test_child_task_uses_independent_worker(self):
        """A child gets its own worker, even inside a parent's savepoint."""
        get = sync_to_async(current_thread_and_connection)

        async def child():
            async with transaction.atomic(durable=True):
                child_thread, child_connection = await get()
                self.assertIsNot(child_thread, parent_thread)
                self.assertIsNot(child_connection, parent_connection)
                async with transaction.atomic():
                    self.assertEqual(await get(), (child_thread, child_connection))
            return child_thread, child_connection

        async with transaction.atomic():
            parent_thread, parent_connection = await get()
            async with transaction.atomic():
                async with asyncio.timeout(10):
                    worker, _ = await asyncio.create_task(child())
                self.assertEqual(await get(), (parent_thread, parent_connection))
            self.assertIsNotNone(parent_connection.connection)
        await asyncio.to_thread(worker.join, 5)
        self.assertIs(worker.is_alive(), False)

    async def test_reuse_atomic_in_child_task(self):
        """Reusing a manager does not share its task's transaction state."""
        atomic = transaction.atomic()
        get = sync_to_async(current_thread_and_connection)

        async def child():
            async with atomic:
                child_thread, child_connection = await get()
                self.assertIsNot(child_thread, parent_thread)
                self.assertIsNot(child_connection, parent_connection)
                async with atomic:
                    self.assertEqual(await get(), (child_thread, child_connection))

        async with atomic:
            parent_thread, parent_connection = await get()
            async with asyncio.timeout(10):
                await asyncio.create_task(child())
            self.assertEqual(await get(), (parent_thread, parent_connection))

    async def test_child_enters_after_parent_exit(self):
        """An inherited, closed worker is not consulted before child entry."""
        release = asyncio.Event()
        get = sync_to_async(current_thread_and_connection)

        async def child():
            await release.wait()
            async with transaction.atomic():
                return await get()

        async with asyncio.timeout(10), asyncio.TaskGroup() as tasks:
            async with transaction.atomic():
                parent_thread, parent_connection = await get()
                task = tasks.create_task(child())
            release.set()
        child_thread, child_connection = task.result()
        self.assertIsNot(child_thread, parent_thread)
        self.assertIsNot(child_connection, parent_connection)
        await asyncio.to_thread(child_thread.join, 5)
        self.assertIs(child_thread.is_alive(), False)

    async def test_child_cancellation_preserves_parent(self):
        """Cancelling a child's block leaves its parent's block usable."""
        ready = asyncio.Event()
        get = sync_to_async(current_thread_and_connection)
        callbacks = []
        child_workers = []

        async def child():
            async with transaction.atomic():
                child_workers.append(await get())
                await sync_to_async(transaction.on_commit)(
                    lambda: callbacks.append("child")
                )
                ready.set()
                await asyncio.Event().wait()

        async with transaction.atomic():
            parent = await get()
            await sync_to_async(transaction.on_commit)(
                lambda: callbacks.append("parent")
            )
            async with asyncio.timeout(10), asyncio.TaskGroup() as tasks:
                task = tasks.create_task(child())
                await ready.wait()
                task.cancel()
            self.assertEqual(await get(), parent)
            self.assertIs(
                await sync_to_async(lambda: connection.in_atomic_block)(), True
            )
            async with transaction.atomic():
                self.assertEqual(await get(), parent)
            self.assertEqual(callbacks, [])
        self.assertEqual(callbacks, ["parent"])
        child_thread, child_connection = child_workers[0]
        self.assertIsNot(child_thread, parent[0])
        await asyncio.to_thread(child_thread.join, 5)
        self.assertIs(child_thread.is_alive(), False)

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

    async def test_async_bridge_task_uses_independent_worker(self):
        """An async bridge's new task follows the same ownership rule."""
        get = sync_to_async(current_thread_and_connection)

        async def callback():
            async with transaction.atomic():
                return await get()

        async with transaction.atomic():
            parent = await get()
            async with asyncio.timeout(10):
                child_thread, child_connection = await sync_to_async(
                    async_to_sync(callback)
                )()
            self.assertIsNot(child_thread, parent[0])
            self.assertIsNot(child_connection, parent[1])
            async with transaction.atomic():
                self.assertEqual(await get(), parent)
        await asyncio.to_thread(child_thread.join, 5)
        self.assertIs(child_thread.is_alive(), False)

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
                    await events["a_exited"].wait()
            except transaction.TransactionManagementError as exc:
                return str(exc)
            finally:
                events["b_attempted"].set()

        async def after_overlap():
            async with transaction.atomic():
                await Reporter.objects.acreate(first_name="Calculus")

        async def callback():
            async with asyncio.timeout(10), asyncio.TaskGroup() as tasks:
                tasks.create_task(rollback_a())
                rejected = tasks.create_task(overlap_b())
            # A new task can use the parent after rejection and rollback.
            await asyncio.create_task(after_overlap())
            return rejected.result()

        def sync_caller():
            with transaction.atomic():
                Reporter.objects.create(first_name="Tintin")
                return async_to_sync(callback)()

        error = await sync_to_async(sync_caller)()
        self.assertEqual(
            [r.first_name async for r in Reporter.objects.order_by("first_name")],
            ["Calculus", "Tintin"],
        )
        self.assertEqual(
            error,
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
        get = sync_to_async(current_thread_and_connection)
        parent = await get()
        loop = asyncio.get_running_loop()
        worker_busy = asyncio.Event()
        release = threading.Event()
        cleanup_finished = threading.Event()
        worker_threads = []
        close_all = connections.close_all
        worker = ThreadPoolExecutor(max_workers=1)
        submit = worker.submit

        def blocking():
            worker_threads.append(threading.current_thread())
            loop.call_soon_threadsafe(worker_busy.set)
            release.wait(10)

        def cleanup():
            self.assertIs(threading.current_thread(), worker_threads[0])
            close_all()
            cleanup_finished.set()

        def submit_work(func, *args, **kwargs):
            if func is connections.close_all:
                # Hold the worker so cleanup is queued, but has not started.
                submit(blocking)
            return submit(func, *args, **kwargs)

        async def run():
            try:
                async with transaction.atomic():
                    pass
            finally:
                # Cancellation must restore the parent context before
                # returning.
                self.assertEqual(await get(), parent)

        with (
            mock.patch("django.db.transaction.ThreadPoolExecutor", return_value=worker),
            mock.patch.object(worker, "submit", side_effect=submit_work),
            mock.patch.object(connections, "close_all", side_effect=cleanup),
        ):
            task = asyncio.create_task(run())
            try:
                await asyncio.wait_for(worker_busy.wait(), 5)
                task.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await asyncio.wait_for(task, 5)
                self.assertIs(cleanup_finished.is_set(), False)
            finally:
                release.set()
                await asyncio.gather(task, return_exceptions=True)
                worker.shutdown(wait=False)
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

    async def test_child_commit_survives_parent_rollback(self):
        """A completed child transaction is not a parent's savepoint."""
        get = sync_to_async(current_thread_and_connection)
        callbacks = []
        child_workers = []

        async def child():
            async with transaction.atomic():
                child_thread, child_connection = await get()
                child_workers.append((child_thread, child_connection))
                self.assertIsNot(child_thread, parent_thread)
                self.assertIsNot(child_connection, parent_connection)
                self.assertIs(
                    await Reporter.objects.filter(pk=parent.pk).aexists(), False
                )
                await Reporter.objects.acreate(first_name="Haddock")
                await sync_to_async(transaction.on_commit)(
                    lambda: callbacks.append("child")
                )

        with self.assertRaisesMessage(ValueError, "Undo parent"):
            async with transaction.atomic():
                parent_thread, parent_connection = await get()
                parent = await Reporter.objects.acreate(first_name="Tintin")
                await sync_to_async(transaction.on_commit)(
                    lambda: callbacks.append("parent")
                )
                async with asyncio.timeout(10), asyncio.TaskGroup() as tasks:
                    tasks.create_task(child())
                self.assertEqual(callbacks, ["child"])
                self.assertEqual(await get(), (parent_thread, parent_connection))
                raise ValueError("Undo parent")
        self.assertEqual(
            [r.first_name async for r in Reporter.objects.all()], ["Haddock"]
        )
        self.assertEqual(callbacks, ["child"])
        child_thread, child_connection = child_workers[0]
        await asyncio.to_thread(child_thread.join, 5)
        self.assertIs(child_thread.is_alive(), False)
        self.assertIsNone(child_connection.connection)

    async def test_overlapping_child_blocks_rollback_their_own_writes(self):
        """Crossed child exits must not pop each other's savepoints."""
        a_entered = asyncio.Event()
        b_entered = asyncio.Event()
        a_exited = asyncio.Event()

        async def rollback_a():
            try:
                with self.assertRaisesMessage(ValueError, "Undo A"):
                    async with transaction.atomic():
                        await Reporter.objects.acreate(first_name="Haddock")
                        a_entered.set()
                        await b_entered.wait()
                        raise ValueError("Undo A")
            finally:
                a_exited.set()

        async def commit_b():
            await a_entered.wait()
            async with transaction.atomic():
                await Reporter.objects.acreate(first_name="Calculus")
                b_entered.set()
                await a_exited.wait()

        async with transaction.atomic():
            await Reporter.objects.acreate(first_name="Tintin")
            async with asyncio.timeout(10), asyncio.TaskGroup() as tasks:
                tasks.create_task(rollback_a())
                tasks.create_task(commit_b())
        self.assertEqual(
            [r.first_name async for r in Reporter.objects.order_by("first_name")],
            ["Calculus", "Tintin"],
        )

    async def test_concurrent_transactions(self):
        both_started = asyncio.Barrier(2)

        async def create(name, fail):
            async with transaction.atomic():
                await Reporter.objects.acreate(first_name=name)
                await both_started.wait()
                if fail:
                    raise ValueError(name)

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
