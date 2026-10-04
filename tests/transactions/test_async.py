import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
from unittest import mock

from asgiref.sync import sync_to_async

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
