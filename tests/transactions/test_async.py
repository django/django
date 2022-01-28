import asyncio
import sys
from unittest import skipUnless

from asgiref.sync import async_to_sync, sync_to_async

from django.db import (
    DatabaseError, Error, IntegrityError, OperationalError, connection,
    transaction,
)
from django.test import (
    TestCase, TransactionTestCase, skipIfDBFeature, skipUnlessDBFeature,
)

from .models import Reporter


@skipUnlessDBFeature('uses_savepoints')
class AtomicTests(TransactionTestCase):
    """
    Tests for the atomic decorator and context manager.

    The tests make assertions on internal attributes because there isn't a
    robust way to ask the database for its current transaction state.

    Since the decorator syntax is converted into a context manager (see the
    implementation), there are only a few basic tests with the decorator
    syntax and the bulk of the tests use the context manager syntax.
    """

    available_apps = ['transactions']

    async def test_decorator_syntax_commit(self):
        @transaction.aatomic
        async def make_reporter():
            return await sync_to_async(Reporter.objects.create, thread_sensitive=True)(first_name="Tintin")

        reporter = await make_reporter()
        self.assertSequenceEqual(await sync_to_async(Reporter.objects.all, thread_sensitive=True)(), [reporter])

    async def test_decorator_syntax_rollback(self):
        @transaction.aatomic
        async def make_reporter():
            await sync_to_async(Reporter.objects.create, thread_sensitive=True)(first_name="Haddock")
            raise Exception("Oops, that's his last name")

        with self.assertRaisesMessage(Exception, "Oops"):
            await make_reporter()
        self.assertSequenceEqual(await sync_to_async(Reporter.objects.all, thread_sensitive=True)(), [])

    async def test_alternate_decorator_syntax_commit(self):
        @transaction.aatomic()
        async def make_reporter():
            return await sync_to_async(Reporter.objects.create, thread_sensitive=True)(first_name="Tintin")

        reporter = await make_reporter()
        self.assertSequenceEqual(await sync_to_async(Reporter.objects.all, thread_sensitive=True)(), [reporter])

    async def test_alternate_decorator_syntax_rollback(self):
        @transaction.aatomic()
        async def make_reporter():
            await sync_to_async(Reporter.objects.create, thread_sensitive=True)(first_name="Haddock")
            raise Exception("Oops, that's his last name")

        with self.assertRaisesMessage(Exception, "Oops"):
            await make_reporter()
        self.assertSequenceEqual(await sync_to_async(Reporter.objects.all, thread_sensitive=True)(), [])

    async def test_commit(self):
        async with transaction.aatomic():
            reporter = await sync_to_async(Reporter.objects.create, thread_sensitive=True)(first_name="Tintin")
        self.assertSequenceEqual(await sync_to_async(Reporter.objects.all, thread_sensitive=True)(), [reporter])

    async def test_rollback(self):
        with self.assertRaisesMessage(Exception, "Oops"):
            async with transaction.aatomic():
                await sync_to_async(Reporter.objects.create, thread_sensitive=True)(first_name="Haddock")
                raise Exception("Oops, that's his last name")
        self.assertSequenceEqual(await sync_to_async(Reporter.objects.all, thread_sensitive=True)(), [])

    async def test_nested_commit_commit(self):
        async with transaction.aatomic():
            reporter1 = await sync_to_async(Reporter.objects.create, thread_sensitive=True)(first_name="Tintin")
            async with transaction.aatomic():
                reporter2 = await sync_to_async(Reporter.objects.create, thread_sensitive=True)(first_name="Archibald",
                                                                                                last_name="Haddock")
        self.assertSequenceEqual(await sync_to_async(Reporter.objects.all, thread_sensitive=True)(),
                                 [reporter2, reporter1])

    async def test_nested_commit_rollback(self):
        async with transaction.aatomic():
            reporter = await sync_to_async(Reporter.objects.create, thread_sensitive=True)(first_name="Tintin")
            with self.assertRaisesMessage(Exception, "Oops"):
                async with transaction.aatomic():
                    await sync_to_async(Reporter.objects.create, thread_sensitive=True)(first_name="Haddock")
                    raise Exception("Oops, that's his last name")
        self.assertSequenceEqual(await sync_to_async(Reporter.objects.all, thread_sensitive=True)(), [reporter])

    async def test_nested_rollback_commit(self):
        with self.assertRaisesMessage(Exception, "Oops"):
            async with transaction.aatomic():
                await sync_to_async(Reporter.objects.create, thread_sensitive=True)(last_name="Tintin")
                async with transaction.aatomic():
                    await sync_to_async(Reporter.objects.create, thread_sensitive=True)(last_name="Haddock")
                raise Exception("Oops, that's his first name")
        self.assertSequenceEqual(await sync_to_async(Reporter.objects.all, thread_sensitive=True)(), [])

    async def test_nested_rollback_rollback(self):
        with self.assertRaisesMessage(Exception, "Oops"):
            async with transaction.aatomic():
                await sync_to_async(Reporter.objects.create, thread_sensitive=True)(last_name="Tintin")
                with self.assertRaisesMessage(Exception, "Oops"):
                    async with transaction.aatomic():
                        await sync_to_async(Reporter.objects.create, thread_sensitive=True)(first_name="Haddock")
                    raise Exception("Oops, that's his last name")
                raise Exception("Oops, that's his first name")
        self.assertSequenceEqual(await sync_to_async(Reporter.objects.all, thread_sensitive=True)(), [])

    async def test_merged_commit_commit(self):
        async with transaction.aatomic():
            reporter1 = await sync_to_async(Reporter.objects.create, thread_sensitive=True)(first_name="Tintin")
            async with transaction.aatomic(savepoint=False):
                reporter2 = await sync_to_async(Reporter.objects.create, thread_sensitive=True)(first_name="Archibald",
                                                                                                last_name="Haddock")
        self.assertSequenceEqual(await sync_to_async(Reporter.objects.all, thread_sensitive=True)(),
                                 [reporter2, reporter1])

    async def test_merged_commit_rollback(self):
        async with transaction.aatomic():
            await sync_to_async(Reporter.objects.create, thread_sensitive=True)(first_name="Tintin")
            with self.assertRaisesMessage(Exception, "Oops"):
                async with transaction.aatomic(savepoint=False):
                    await sync_to_async(Reporter.objects.create, thread_sensitive=True)(first_name="Haddock")
                    raise Exception("Oops, that's his last name")
        # Writes in the outer block are rolled back too.
        self.assertSequenceEqual(await sync_to_async(Reporter.objects.all, thread_sensitive=True)(), [])

    async def test_merged_rollback_commit(self):
        with self.assertRaisesMessage(Exception, "Oops"):
            async with transaction.aatomic():
                await sync_to_async(Reporter.objects.create, thread_sensitive=True)(last_name="Tintin")
                async with transaction.aatomic(savepoint=False):
                    await sync_to_async(Reporter.objects.create, thread_sensitive=True)(last_name="Haddock")
                raise Exception("Oops, that's his first name")
        self.assertSequenceEqual(await sync_to_async(Reporter.objects.all, thread_sensitive=True)(), [])

    async def test_merged_rollback_rollback(self):
        with self.assertRaisesMessage(Exception, "Oops"):
            async with transaction.aatomic():
                await sync_to_async(Reporter.objects.create, thread_sensitive=True)(last_name="Tintin")
                with self.assertRaisesMessage(Exception, "Oops"):
                    async with transaction.aatomic(savepoint=False):
                        await sync_to_async(Reporter.objects.create, thread_sensitive=True)(first_name="Haddock")
                    raise Exception("Oops, that's his last name")
                raise Exception("Oops, that's his first name")
        self.assertSequenceEqual(await sync_to_async(Reporter.objects.all, thread_sensitive=True)(), [])

    async def test_reuse_commit_commit(self):
        atomic = transaction.aatomic()
        with atomic:
            reporter1 = await sync_to_async(Reporter.objects.create, thread_sensitive=True)(first_name="Tintin")
            with atomic:
                reporter2 = await sync_to_async(Reporter.objects.create, thread_sensitive=True)(first_name="Archibald",
                                                                                                last_name="Haddock")
        self.assertSequenceEqual(await sync_to_async(Reporter.objects.all, thread_sensitive=True)(),
                                 [reporter2, reporter1])

    async def test_reuse_commit_rollback(self):
        atomic = transaction.aatomic()
        with atomic:
            reporter = await sync_to_async(Reporter.objects.create, thread_sensitive=True)(first_name="Tintin")
            with self.assertRaisesMessage(Exception, "Oops"):
                with atomic:
                    await sync_to_async(Reporter.objects.create, thread_sensitive=True)(first_name="Haddock")
                    raise Exception("Oops, that's his last name")
        self.assertSequenceEqual(await sync_to_async(Reporter.objects.all, thread_sensitive=True)(), [reporter])

    async def test_reuse_rollback_commit(self):
        atomic = transaction.aatomic()
        with self.assertRaisesMessage(Exception, "Oops"):
            with atomic:
                await sync_to_async(Reporter.objects.create, thread_sensitive=True)(last_name="Tintin")
                with atomic:
                    await sync_to_async(Reporter.objects.create, thread_sensitive=True)(last_name="Haddock")
                raise Exception("Oops, that's his first name")
        self.assertSequenceEqual(await sync_to_async(Reporter.objects.all, thread_sensitive=True)(), [])

    async def test_reuse_rollback_rollback(self):
        atomic = transaction.aatomic()
        with self.assertRaisesMessage(Exception, "Oops"):
            async with atomic:
                await sync_to_async(Reporter.objects.create, thread_sensitive=True)(last_name="Tintin")
                with self.assertRaisesMessage(Exception, "Oops"):
                    async with atomic:
                        await sync_to_async(Reporter.objects.create, thread_sensitive=True)(first_name="Haddock")
                    raise Exception("Oops, that's his last name")
                raise Exception("Oops, that's his first name")
        self.assertSequenceEqual(await sync_to_async(Reporter.objects.all, thread_sensitive=True)(), [])

    async def test_force_rollback(self):
        async with transaction.aatomic():
            await sync_to_async(Reporter.objects.create, thread_sensitive=True)(first_name="Tintin")
            # atomic block shouldn't rollback, but force it.
            self.assertFalse(await transaction.get_rollback())
            await transaction.set_rollback(True)
        self.assertSequenceEqual(await sync_to_async(Reporter.objects.all, thread_sensitive=True)(), [])

    async def test_prevent_rollback(self):
        async with transaction.aatomic():
            reporter = await sync_to_async(Reporter.objects.create, thread_sensitive=True)(first_name="Tintin")
            sid = await transaction.savepoint()
            # trigger a database error inside an inner atomic without savepoint
            with self.assertRaises(DatabaseError):
                async with transaction.aatomic(savepoint=False):
                    async with connection.cursor() as cursor:
                        await cursor.execute(
                            "SELECT no_such_col FROM transactions_reporter")
            # prevent atomic from rolling back since we're recovering manually
            self.assertTrue(await transaction.get_rollback())
            await transaction.set_rollback(False)
            transaction.savepoint_rollback(sid)
        self.assertSequenceEqual(await sync_to_async(Reporter.objects.all, thread_sensitive=True)(), [reporter])


class AtomicInsideTransactionTests(AtomicTests):
    """All basic tests for atomic should also pass within an existing transaction."""

    def setUp(self):
        self.atomic = transaction.aatomic()
        async_to_sync(self.atomic.__aenter__)()

    def tearDown(self):
        async_to_sync(self.atomic.__aexit__)(*sys.exc_info())


class AtomicWithoutAutocommitTests(AtomicTests):
    """All basic tests for atomic should also pass when autocommit is turned off."""

    def setUp(self):
        async_to_sync(transaction.set_autocommit)(False)

    def tearDown(self):
        # The tests access the database after exercising 'atomic', initiating
        # a transaction ; a rollback is required before restoring autocommit.
        async def rollback():
            await transaction.rollback()
            await transaction.set_autocommit(True)

        sync_to_async(rollback)()


@skipUnlessDBFeature('uses_savepoints')
class AtomicMergeTests(TransactionTestCase):
    """Test merging transactions with savepoint=False."""

    available_apps = ['transactions']

    async def test_merged_outer_rollback(self):
        async with transaction.aatomic():
            await sync_to_async(Reporter.objects.create, thread_sensitive=True)(first_name="Tintin")
            async with transaction.aatomic(savepoint=False):
                await sync_to_async(Reporter.objects.create, thread_sensitive=True)(first_name="Archibald",
                                                                                    last_name="Haddock")
                with self.assertRaisesMessage(Exception, "Oops"):
                    async with transaction.aatomic(savepoint=False):
                        await sync_to_async(Reporter.objects.create, thread_sensitive=True)(first_name="Calculus")
                        raise Exception("Oops, that's his last name")
                # The third insert couldn't be roll back. Temporarily mark the
                # connection as not needing rollback to check it.
                self.assertTrue(await transaction.get_rollback())
                await transaction.set_rollback(False)
                self.assertEqual(await sync_to_async(Reporter.objects.count, thread_sensitive=True)(), 3)
                await transaction.set_rollback(True)
            # The second insert couldn't be roll back. Temporarily mark the
            # connection as not needing rollback to check it.
            self.assertTrue(await transaction.get_rollback())
            await transaction.set_rollback(False)
            self.assertEqual(await sync_to_async(Reporter.objects.count, thread_sensitive=True)(), 3)
            await transaction.set_rollback(True)
        # The first block has a savepoint and must roll back.
        self.assertSequenceEqual(await sync_to_async(Reporter.objects.all, thread_sensitive=True)(), [])

    async def test_merged_inner_savepoint_rollback(self):
        async with transaction.aatomic():
            reporter = await sync_to_async(Reporter.objects.create, thread_sensitive=True)(first_name="Tintin")
            async with transaction.aatomic():
                await sync_to_async(Reporter.objects.create, thread_sensitive=True)(first_name="Archibald",
                                                                                    last_name="Haddock")
                with self.assertRaisesMessage(Exception, "Oops"):
                    async with transaction.aatomic(savepoint=False):
                        await sync_to_async(Reporter.objects.create, thread_sensitive=True)(first_name="Calculus")
                        raise Exception("Oops, that's his last name")
                # The third insert couldn't be roll back. Temporarily mark the
                # connection as not needing rollback to check it.
                self.assertTrue(await transaction.get_rollback())
                await transaction.set_rollback(False)
                self.assertEqual(await sync_to_async(Reporter.objects.count, thread_sensitive=True)(), 3)
                await transaction.set_rollback(True)
            # The second block has a savepoint and must roll back.
            self.assertEqual(await sync_to_async(Reporter.objects.count, thread_sensitive=True)(), 1)
        self.assertSequenceEqual(await sync_to_async(Reporter.objects.all, thread_sensitive=True)(), [reporter])


@skipUnlessDBFeature('uses_savepoints')
class AtomicErrorsTests(TransactionTestCase):
    available_apps = ['transactions']
    forbidden_atomic_msg = "This is forbidden when an 'atomic' block is active."

    async def test_atomic_prevents_setting_autocommit(self):
        autocommit = transaction.get_autocommit()
        async with transaction.aatomic():
            with self.assertRaisesMessage(transaction.TransactionManagementError, self.forbidden_atomic_msg):
                await transaction.set_autocommit(not autocommit)
        # Make sure autocommit wasn't changed.
        self.assertEqual(connection.autocommit, autocommit)

    async def test_atomic_prevents_calling_transaction_methods(self):
        async with transaction.aatomic():
            with self.assertRaisesMessage(transaction.TransactionManagementError, self.forbidden_atomic_msg):
                await transaction.commit()
            with self.assertRaisesMessage(transaction.TransactionManagementError, self.forbidden_atomic_msg):
                await transaction.rollback()

    async def test_atomic_prevents_queries_in_broken_transaction(self):
        r1 = await sync_to_async(Reporter.objects.create, thread_sensitive=True)(first_name="Archibald",
                                                                                 last_name="Haddock")
        async with transaction.aatomic():
            r2 = Reporter(first_name="Cuthbert", last_name="Calculus", id=r1.id)
            with self.assertRaises(IntegrityError):
                await sync_to_async(r2.save, thread_sensitive=True)(force_insert=True)
            # The transaction is marked as needing rollback.
            msg = (
                "An error occurred in the current transaction. You can't "
                "execute queries until the end of the 'atomic' block."
            )
            with self.assertRaisesMessage(transaction.TransactionManagementError, msg):
                await sync_to_async(r2.save, thread_sensitive=True)(force_update=True)
        self.assertEqual(await sync_to_async(Reporter.objects.get, thread_sensitive=True)(pk=r1.pk).last_name,
                         "Haddock")

    @skipIfDBFeature('atomic_transactions')
    async def test_atomic_allows_queries_after_fixing_transaction(self):
        r1 = await sync_to_async(Reporter.objects.create, thread_sensitive=True)(first_name="Archibald",
                                                                                 last_name="Haddock")
        async with transaction.aatomic():
            r2 = Reporter(first_name="Cuthbert", last_name="Calculus", id=r1.id)
            with self.assertRaises(IntegrityError):
                await sync_to_async(r2.save, thread_sensitive=True)(force_insert=True)
            # Mark the transaction as no longer needing rollback.
            await transaction.set_rollback(False)
            await sync_to_async(r2.save, thread_sensitive=True)(force_update=True)
        self.assertEqual(await sync_to_async(Reporter.objects.get, thread_sensitive=True)(pk=r1.pk).last_name,
                         "Calculus")

    @skipUnlessDBFeature('test_db_allows_multiple_connections')
    async def test_atomic_prevents_queries_in_broken_transaction_after_client_close(self):
        async with transaction.aatomic():
            await sync_to_async(Reporter.objects.create, thread_sensitive=True)(first_name="Archibald",
                                                                                last_name="Haddock")
            await connection.close()
            # The connection is closed and the transaction is marked as
            # needing rollback. This will raise an InterfaceError on databases
            # that refuse to create cursors on closed connections (PostgreSQL)
            # and a TransactionManagementError on other databases.
            with self.assertRaises(Error):
                await sync_to_async(Reporter.objects.create, thread_sensitive=True)(first_name="Cuthbert",
                                                                                    last_name="Calculus")
        # The connection is usable again .
        self.assertEqual(await sync_to_async(Reporter.objects.count, thread_sensitive=True)(), 0)


@skipUnless(connection.vendor == 'mysql', "MySQL-specific behaviors")
class AtomicMySQLTests(TransactionTestCase):
    available_apps = ['transactions']

    async def test_implicit_savepoint_rollback(self):
        """MySQL implicitly rolls back savepoints when it deadlocks (#22291)."""
        await sync_to_async(Reporter.objects.create, thread_sensitive=True)(id=1)
        await sync_to_async(Reporter.objects.create, thread_sensitive=True)(id=2)

        main_task_ready = asyncio.Event()

        async def other_task():
            try:
                async with transaction.aatomic():
                    await sync_to_async(Reporter.objects.select_for_update, thread_sensitive=True)().get(id=1)
                    await main_task_ready.wait()
                    # 1) This line locks... (see below for 2)
                    await sync_to_async(Reporter.objects.exclude, thread_sensitive=True)(id=1).update(id=2)
            finally:
                # This is the thread-local connection, not the main connection.
                await connection.close()

        task = asyncio.create_task(other_task())

        with self.assertRaisesMessage(OperationalError, 'Deadlock found'):
            # Double atomic to enter a transaction and create a savepoint.
            async with transaction.aatomic():
                async with transaction.aatomic():
                    await sync_to_async(Reporter.objects.select_for_update, thread_sensitive=True)().get(id=2)
                    main_task_ready.set()
                    # The two threads can't be synchronized with an event here
                    # because the other thread locks. Sleep for a little while.
                    await asyncio.sleep(1)
                    # 2) ... and this line deadlocks. (see above for 1)
                    await sync_to_async(Reporter.objects.exclude, thread_sensitive=True)(id=2).update(id=1)

        await task


class AtomicMiscTests(TransactionTestCase):
    available_apps = ['transactions']

    async def test_wrap_callable_instance(self):
        """#20028 -- Atomic must support wrapping callable instances."""

        class Callable:
            def __call__(self):
                pass

        # Must not raise an exception
        transaction.aatomic(Callable())

    @skipUnlessDBFeature('can_release_savepoints')
    async def test_atomic_does_not_leak_savepoints_on_failure(self):
        """#23074 -- Savepoints must be released after rollback."""

        # Expect an error when rolling back a savepoint that doesn't exist.
        # Done outside of the transaction block to ensure proper recovery.
        with self.assertRaises(Error):
            # Start a plain transaction.
            async with transaction.aatomic():
                # Swallow the intentional error raised in the sub-transaction.
                with self.assertRaisesMessage(Exception, "Oops"):
                    # Start a sub-transaction with a savepoint.
                    async with transaction.aatomic():
                        sid = connection.savepoint_ids[-1]
                        raise Exception("Oops")

                # This is expected to fail because the savepoint no longer exists.
                await connection.savepoint_rollback(sid)

    async def test_mark_for_rollback_on_error_in_transaction(self):
        async with transaction.aatomic(savepoint=False):
            # Swallow the intentional error raised.
            with self.assertRaisesMessage(Exception, "Oops"):
                # Wrap in `mark_for_rollback_on_error` to check if the transaction is marked broken.
                with transaction.mark_for_rollback_on_error():
                    # Ensure that we are still in a good state.
                    self.assertFalse(await transaction.get_rollback())

                    raise Exception("Oops")

                # Ensure that `mark_for_rollback_on_error` marked the transaction as broken …
                self.assertTrue(await transaction.get_rollback())

            # … and further queries fail.
            msg = "You can't execute queries until the end of the 'atomic' block."
            with self.assertRaisesMessage(transaction.TransactionManagementError, msg):
                await sync_to_async(Reporter.objects.create, thread_sensitive=True)()

        # Transaction errors are reset at the end of an transaction, so this should just work.
        await sync_to_async(Reporter.objects.create, thread_sensitive=True)()

    async def test_mark_for_rollback_on_error_in_autocommit(self):
        self.assertTrue(transaction.get_autocommit())

        # Swallow the intentional error raised.
        with self.assertRaisesMessage(Exception, "Oops"):
            # Wrap in `mark_for_rollback_on_error` to check if the transaction is marked broken.
            with transaction.mark_for_rollback_on_error():
                # Ensure that we are still in a good state.
                self.assertFalse((await transaction.get_connection()).needs_rollback)

                raise Exception("Oops")

            # Ensure that `mark_for_rollback_on_error` did not mark the transaction
            # as broken, since we are in autocommit mode …
            self.assertFalse((await transaction.get_connection()).needs_rollback)

        # … and further queries work nicely.
        await sync_to_async(Reporter.objects.create, thread_sensitive=True)()


class NonAutocommitTests(TransactionTestCase):
    available_apps = []

    def setUp(self):
        sync_to_async(transaction.set_autocommit)(False)

    def tearDown(self):
        async def rollback():
            await transaction.rollback()
            await transaction.set_autocommit(True)

        sync_to_async(rollback)()

    async def test_orm_query_after_error_and_rollback(self):
        """
        ORM queries are allowed after an error and a rollback in non-autocommit
        mode (#27504).
        """
        r1 = await sync_to_async(Reporter.objects.create, thread_sensitive=True)(first_name='Archibald',
                                                                                 last_name='Haddock')
        r2 = Reporter(first_name='Cuthbert', last_name='Calculus', id=r1.id)
        with self.assertRaises(IntegrityError):
            await sync_to_async(r2.save, thread_sensitive=True)(force_insert=True)
        await transaction.rollback()
        await sync_to_async(Reporter.objects.last, thread_sensitive=True)()

    async def test_orm_query_without_autocommit(self):
        """#24921 -- ORM queries must be possible after set_autocommit(False)."""
        await sync_to_async(Reporter.objects.create, thread_sensitive=True)(first_name="Tintin")


class DurableTestsBase:
    available_apps = ['transactions']

    async def test_commit(self):
        async with transaction.aatomic(durable=True):
            reporter = await sync_to_async(Reporter.objects.create, thread_sensitive=True)(first_name='Tintin')
        self.assertEqual(await sync_to_async(Reporter.objects.get, thread_sensitive=True)(), reporter)

    async def test_nested_outer_durable(self):
        async with transaction.aatomic(durable=True):
            reporter1 = await sync_to_async(Reporter.objects.create, thread_sensitive=True)(first_name='Tintin')
            async with transaction.aatomic():
                reporter2 = await sync_to_async(Reporter.objects.create, thread_sensitive=True)(
                    first_name='Archibald',
                    last_name='Haddock',
                )
        self.assertSequenceEqual(await sync_to_async(Reporter.objects.all, thread_sensitive=True)(),
                                 [reporter2, reporter1])

    async def test_nested_both_durable(self):
        msg = 'A durable atomic block cannot be nested within another atomic block.'
        async with transaction.aatomic(durable=True):
            with self.assertRaisesMessage(RuntimeError, msg):
                async with transaction.aatomic(durable=True):
                    pass

    async def test_nested_inner_durable(self):
        msg = 'A durable atomic block cannot be nested within another atomic block.'
        async with transaction.aatomic():
            with self.assertRaisesMessage(RuntimeError, msg):
                async with transaction.aatomic(durable=True):
                    pass

    async def test_sequence_of_durables(self):
        async with transaction.aatomic(durable=True):
            reporter = await sync_to_async(Reporter.objects.create, thread_sensitive=True)(first_name='Tintin 1')
        self.assertEqual(await sync_to_async(Reporter.objects.get, thread_sensitive=True)(first_name='Tintin 1'),
                         reporter)
        async with transaction.aatomic(durable=True):
            reporter = await sync_to_async(Reporter.objects.create, thread_sensitive=True)(first_name='Tintin 2')
        self.assertEqual(await sync_to_async(Reporter.objects.get, thread_sensitive=True)(first_name='Tintin 2'),
                         reporter)


class DurableTransactionTests(DurableTestsBase, TransactionTestCase):
    pass


class DurableTests(DurableTestsBase, TestCase):
    pass
