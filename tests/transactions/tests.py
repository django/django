from __future__ import absolute_import

import sys
try:
    import threading
except ImportError:
    threading = None
import time

from django.db import (connection, transaction,
    DatabaseError, Error, IntegrityError, OperationalError)
from django.test import TransactionTestCase, skipIfDBFeature, skipUnlessDBFeature
from django.test.utils import IgnorePendingDeprecationWarningsMixin
from django.utils import six
from django.utils.unittest import skipIf, skipUnless

from .models import Reporter


@skipUnless(connection.features.uses_savepoints,
        "'atomic' requires transactions and savepoints.")
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

    def test_decorator_syntax_commit(self):
        @transaction.atomic
        def make_reporter():
            Reporter.objects.create(first_name="Tintin")
        make_reporter()
        self.assertQuerysetEqual(Reporter.objects.all(), ['<Reporter: Tintin>'])

    def test_decorator_syntax_rollback(self):
        @transaction.atomic
        def make_reporter():
            Reporter.objects.create(first_name="Haddock")
            raise Exception("Oops, that's his last name")
        with six.assertRaisesRegex(self, Exception, "Oops"):
            make_reporter()
        self.assertQuerysetEqual(Reporter.objects.all(), [])

    def test_alternate_decorator_syntax_commit(self):
        @transaction.atomic()
        def make_reporter():
            Reporter.objects.create(first_name="Tintin")
        make_reporter()
        self.assertQuerysetEqual(Reporter.objects.all(), ['<Reporter: Tintin>'])

    def test_alternate_decorator_syntax_rollback(self):
        @transaction.atomic()
        def make_reporter():
            Reporter.objects.create(first_name="Haddock")
            raise Exception("Oops, that's his last name")
        with six.assertRaisesRegex(self, Exception, "Oops"):
            make_reporter()
        self.assertQuerysetEqual(Reporter.objects.all(), [])

    def test_commit(self):
        with transaction.atomic():
            Reporter.objects.create(first_name="Tintin")
        self.assertQuerysetEqual(Reporter.objects.all(), ['<Reporter: Tintin>'])

    def test_rollback(self):
        with six.assertRaisesRegex(self, Exception, "Oops"):
            with transaction.atomic():
                Reporter.objects.create(first_name="Haddock")
                raise Exception("Oops, that's his last name")
        self.assertQuerysetEqual(Reporter.objects.all(), [])

    def test_nested_commit_commit(self):
        with transaction.atomic():
            Reporter.objects.create(first_name="Tintin")
            with transaction.atomic():
                Reporter.objects.create(first_name="Archibald", last_name="Haddock")
        self.assertQuerysetEqual(Reporter.objects.all(),
                ['<Reporter: Archibald Haddock>', '<Reporter: Tintin>'])

    def test_nested_commit_rollback(self):
        with transaction.atomic():
            Reporter.objects.create(first_name="Tintin")
            with six.assertRaisesRegex(self, Exception, "Oops"):
                with transaction.atomic():
                    Reporter.objects.create(first_name="Haddock")
                    raise Exception("Oops, that's his last name")
        self.assertQuerysetEqual(Reporter.objects.all(), ['<Reporter: Tintin>'])

    def test_nested_rollback_commit(self):
        with six.assertRaisesRegex(self, Exception, "Oops"):
            with transaction.atomic():
                Reporter.objects.create(last_name="Tintin")
                with transaction.atomic():
                    Reporter.objects.create(last_name="Haddock")
                raise Exception("Oops, that's his first name")
        self.assertQuerysetEqual(Reporter.objects.all(), [])

    def test_nested_rollback_rollback(self):
        with six.assertRaisesRegex(self, Exception, "Oops"):
            with transaction.atomic():
                Reporter.objects.create(last_name="Tintin")
                with six.assertRaisesRegex(self, Exception, "Oops"):
                    with transaction.atomic():
                        Reporter.objects.create(first_name="Haddock")
                    raise Exception("Oops, that's his last name")
                raise Exception("Oops, that's his first name")
        self.assertQuerysetEqual(Reporter.objects.all(), [])

    def test_merged_commit_commit(self):
        with transaction.atomic():
            Reporter.objects.create(first_name="Tintin")
            with transaction.atomic(savepoint=False):
                Reporter.objects.create(first_name="Archibald", last_name="Haddock")
        self.assertQuerysetEqual(Reporter.objects.all(),
                ['<Reporter: Archibald Haddock>', '<Reporter: Tintin>'])

    def test_merged_commit_rollback(self):
        with transaction.atomic():
            Reporter.objects.create(first_name="Tintin")
            with six.assertRaisesRegex(self, Exception, "Oops"):
                with transaction.atomic(savepoint=False):
                    Reporter.objects.create(first_name="Haddock")
                    raise Exception("Oops, that's his last name")
        # Writes in the outer block are rolled back too.
        self.assertQuerysetEqual(Reporter.objects.all(), [])

    def test_merged_rollback_commit(self):
        with six.assertRaisesRegex(self, Exception, "Oops"):
            with transaction.atomic():
                Reporter.objects.create(last_name="Tintin")
                with transaction.atomic(savepoint=False):
                    Reporter.objects.create(last_name="Haddock")
                raise Exception("Oops, that's his first name")
        self.assertQuerysetEqual(Reporter.objects.all(), [])

    def test_merged_rollback_rollback(self):
        with six.assertRaisesRegex(self, Exception, "Oops"):
            with transaction.atomic():
                Reporter.objects.create(last_name="Tintin")
                with six.assertRaisesRegex(self, Exception, "Oops"):
                    with transaction.atomic(savepoint=False):
                        Reporter.objects.create(first_name="Haddock")
                    raise Exception("Oops, that's his last name")
                raise Exception("Oops, that's his first name")
        self.assertQuerysetEqual(Reporter.objects.all(), [])

    def test_reuse_commit_commit(self):
        atomic = transaction.atomic()
        with atomic:
            Reporter.objects.create(first_name="Tintin")
            with atomic:
                Reporter.objects.create(first_name="Archibald", last_name="Haddock")
        self.assertQuerysetEqual(Reporter.objects.all(),
                ['<Reporter: Archibald Haddock>', '<Reporter: Tintin>'])

    def test_reuse_commit_rollback(self):
        atomic = transaction.atomic()
        with atomic:
            Reporter.objects.create(first_name="Tintin")
            with six.assertRaisesRegex(self, Exception, "Oops"):
                with atomic:
                    Reporter.objects.create(first_name="Haddock")
                    raise Exception("Oops, that's his last name")
        self.assertQuerysetEqual(Reporter.objects.all(), ['<Reporter: Tintin>'])

    def test_reuse_rollback_commit(self):
        atomic = transaction.atomic()
        with six.assertRaisesRegex(self, Exception, "Oops"):
            with atomic:
                Reporter.objects.create(last_name="Tintin")
                with atomic:
                    Reporter.objects.create(last_name="Haddock")
                raise Exception("Oops, that's his first name")
        self.assertQuerysetEqual(Reporter.objects.all(), [])

    def test_reuse_rollback_rollback(self):
        atomic = transaction.atomic()
        with six.assertRaisesRegex(self, Exception, "Oops"):
            with atomic:
                Reporter.objects.create(last_name="Tintin")
                with six.assertRaisesRegex(self, Exception, "Oops"):
                    with atomic:
                        Reporter.objects.create(first_name="Haddock")
                    raise Exception("Oops, that's his last name")
                raise Exception("Oops, that's his first name")
        self.assertQuerysetEqual(Reporter.objects.all(), [])

    def test_force_rollback(self):
        with transaction.atomic():
            Reporter.objects.create(first_name="Tintin")
            # atomic block shouldn't rollback, but force it.
            self.assertFalse(transaction.get_rollback())
            transaction.set_rollback(True)
        self.assertQuerysetEqual(Reporter.objects.all(), [])

    def test_prevent_rollback(self):
        with transaction.atomic():
            Reporter.objects.create(first_name="Tintin")
            sid = transaction.savepoint()
            # trigger a database error inside an inner atomic without savepoint
            with self.assertRaises(DatabaseError):
                with transaction.atomic(savepoint=False):
                    connection.cursor().execute(
                            "SELECT no_such_col FROM transactions_reporter")
            # prevent atomic from rolling back since we're recovering manually
            self.assertTrue(transaction.get_rollback())
            transaction.set_rollback(False)
            transaction.savepoint_rollback(sid)
        self.assertQuerysetEqual(Reporter.objects.all(), ['<Reporter: Tintin>'])


class AtomicInsideTransactionTests(AtomicTests):
    """All basic tests for atomic should also pass within an existing transaction."""

    def setUp(self):
        self.atomic = transaction.atomic()
        self.atomic.__enter__()

    def tearDown(self):
        self.atomic.__exit__(*sys.exc_info())


@skipIf(connection.features.autocommits_when_autocommit_is_off,
        "This test requires a non-autocommit mode that doesn't autocommit.")
class AtomicWithoutAutocommitTests(AtomicTests):
    """All basic tests for atomic should also pass when autocommit is turned off."""

    def setUp(self):
        transaction.set_autocommit(False)

    def tearDown(self):
        # The tests access the database after exercising 'atomic', initiating
        # a transaction ; a rollback is required before restoring autocommit.
        transaction.rollback()
        transaction.set_autocommit(True)


@skipIf(connection.features.autocommits_when_autocommit_is_off,
        "This test requires a non-autocommit mode that doesn't autocommit.")
class AtomicInsideLegacyTransactionManagementTests(AtomicTests):

    def setUp(self):
        transaction.enter_transaction_management()

    def tearDown(self):
        # The tests access the database after exercising 'atomic', making the
        # connection dirty; a rollback is required to make it clean.
        transaction.rollback()
        transaction.leave_transaction_management()


@skipUnless(connection.features.uses_savepoints,
        "'atomic' requires transactions and savepoints.")
class AtomicMergeTests(TransactionTestCase):
    """Test merging transactions with savepoint=False."""

    available_apps = ['transactions']

    def test_merged_outer_rollback(self):
        with transaction.atomic():
            Reporter.objects.create(first_name="Tintin")
            with transaction.atomic(savepoint=False):
                Reporter.objects.create(first_name="Archibald", last_name="Haddock")
                with six.assertRaisesRegex(self, Exception, "Oops"):
                    with transaction.atomic(savepoint=False):
                        Reporter.objects.create(first_name="Tournesol")
                        raise Exception("Oops, that's his last name")
                # The third insert couldn't be roll back. Temporarily mark the
                # connection as not needing rollback to check it.
                self.assertTrue(transaction.get_rollback())
                transaction.set_rollback(False)
                self.assertEqual(Reporter.objects.count(), 3)
                transaction.set_rollback(True)
            # The second insert couldn't be roll back. Temporarily mark the
            # connection as not needing rollback to check it.
            self.assertTrue(transaction.get_rollback())
            transaction.set_rollback(False)
            self.assertEqual(Reporter.objects.count(), 3)
            transaction.set_rollback(True)
        # The first block has a savepoint and must roll back.
        self.assertQuerysetEqual(Reporter.objects.all(), [])

    def test_merged_inner_savepoint_rollback(self):
        with transaction.atomic():
            Reporter.objects.create(first_name="Tintin")
            with transaction.atomic():
                Reporter.objects.create(first_name="Archibald", last_name="Haddock")
                with six.assertRaisesRegex(self, Exception, "Oops"):
                    with transaction.atomic(savepoint=False):
                        Reporter.objects.create(first_name="Tournesol")
                        raise Exception("Oops, that's his last name")
                # The third insert couldn't be roll back. Temporarily mark the
                # connection as not needing rollback to check it.
                self.assertTrue(transaction.get_rollback())
                transaction.set_rollback(False)
                self.assertEqual(Reporter.objects.count(), 3)
                transaction.set_rollback(True)
            # The second block has a savepoint and must roll back.
            self.assertEqual(Reporter.objects.count(), 1)
        self.assertQuerysetEqual(Reporter.objects.all(), ['<Reporter: Tintin>'])


@skipUnless(connection.features.uses_savepoints,
        "'atomic' requires transactions and savepoints.")
class AtomicErrorsTests(TransactionTestCase):

    available_apps = ['transactions']

    def test_atomic_prevents_setting_autocommit(self):
        autocommit = transaction.get_autocommit()
        with transaction.atomic():
            with self.assertRaises(transaction.TransactionManagementError):
                transaction.set_autocommit(not autocommit)
        # Make sure autocommit wasn't changed.
        self.assertEqual(connection.autocommit, autocommit)

    def test_atomic_prevents_calling_transaction_methods(self):
        with transaction.atomic():
            with self.assertRaises(transaction.TransactionManagementError):
                transaction.commit()
            with self.assertRaises(transaction.TransactionManagementError):
                transaction.rollback()

    def test_atomic_prevents_calling_transaction_management_methods(self):
        with transaction.atomic():
            with self.assertRaises(transaction.TransactionManagementError):
                transaction.enter_transaction_management()
            with self.assertRaises(transaction.TransactionManagementError):
                transaction.leave_transaction_management()

    def test_atomic_prevents_queries_in_broken_transaction(self):
        r1 = Reporter.objects.create(first_name="Archibald", last_name="Haddock")
        with transaction.atomic():
            r2 = Reporter(first_name="Cuthbert", last_name="Calculus", id=r1.id)
            with self.assertRaises(IntegrityError):
                r2.save(force_insert=True)
            # The transaction is marked as needing rollback.
            with self.assertRaises(transaction.TransactionManagementError):
                r2.save(force_update=True)
        self.assertEqual(Reporter.objects.get(pk=r1.pk).last_name, "Haddock")

    @skipIfDBFeature('atomic_transactions')
    def test_atomic_allows_queries_after_fixing_transaction(self):
        r1 = Reporter.objects.create(first_name="Archibald", last_name="Haddock")
        with transaction.atomic():
            r2 = Reporter(first_name="Cuthbert", last_name="Calculus", id=r1.id)
            with self.assertRaises(IntegrityError):
                r2.save(force_insert=True)
            # Mark the transaction as no longer needing rollback.
            transaction.set_rollback(False)
            r2.save(force_update=True)
        self.assertEqual(Reporter.objects.get(pk=r1.pk).last_name, "Calculus")

    @skipUnlessDBFeature('test_db_allows_multiple_connections')
    def test_atomic_prevents_queries_in_broken_transaction_after_client_close(self):
        with transaction.atomic():
            Reporter.objects.create(first_name="Archibald", last_name="Haddock")
            connection.close()
            # The connection is closed and the transaction is marked as
            # needing rollback. This will raise an InterfaceError on databases
            # that refuse to create cursors on closed connections (PostgreSQL)
            # and a TransactionManagementError on other databases.
            with self.assertRaises(Error):
                Reporter.objects.create(first_name="Cuthbert", last_name="Calculus")
        # The connection is usable again .
        self.assertEqual(Reporter.objects.count(), 0)


@skipUnless(connection.vendor == 'mysql', "MySQL-specific behaviors")
class AtomicMySQLTests(TransactionTestCase):

    available_apps = ['transactions']

    @skipIf(threading is None, "Test requires threading")
    def test_implicit_savepoint_rollback(self):
        """MySQL implicitly rolls back savepoints when it deadlocks (#22291)."""

        other_thread_ready = threading.Event()

        def other_thread():
            try:
                with transaction.atomic():
                    Reporter.objects.create(id=1, first_name="Tintin")
                    other_thread_ready.set()
                    # We cannot synchronize the two threads with an event here
                    # because the main thread locks. Sleep for a little while.
                    time.sleep(1)
                    # 2) ... and this line deadlocks. (see below for 1)
                    Reporter.objects.exclude(id=1).update(id=2)
            finally:
                # This is the thread-local connection, not the main connection.
                connection.close()

        other_thread = threading.Thread(target=other_thread)
        other_thread.start()
        other_thread_ready.wait()

        with six.assertRaisesRegex(self, OperationalError, 'Deadlock found'):
            # Double atomic to enter a transaction and create a savepoint.
            with transaction.atomic():
                with transaction.atomic():
                    # 1) This line locks... (see above for 2)
                    Reporter.objects.create(id=1, first_name="Tintin")

        other_thread.join()


class AtomicMiscTests(TransactionTestCase):

    available_apps = []

    def test_wrap_callable_instance(self):
        # Regression test for #20028
        class Callable(object):
            def __call__(self):
                pass
        # Must not raise an exception
        transaction.atomic(Callable())


class TransactionTests(IgnorePendingDeprecationWarningsMixin, TransactionTestCase):

    available_apps = ['transactions']

    def create_a_reporter_then_fail(self, first, last):
        a = Reporter(first_name=first, last_name=last)
        a.save()
        raise Exception("I meant to do that")

    def remove_a_reporter(self, first_name):
        r = Reporter.objects.get(first_name="Alice")
        r.delete()

    def manually_managed(self):
        r = Reporter(first_name="Dirk", last_name="Gently")
        r.save()
        transaction.commit()

    def manually_managed_mistake(self):
        r = Reporter(first_name="Edward", last_name="Woodward")
        r.save()
        # Oops, I forgot to commit/rollback!

    @skipUnlessDBFeature('supports_transactions')
    def test_autocommit(self):
        """
        The default behavior is to autocommit after each save() action.
        """
        self.assertRaises(Exception,
            self.create_a_reporter_then_fail,
            "Alice", "Smith"
        )

        # The object created before the exception still exists
        self.assertEqual(Reporter.objects.count(), 1)

    @skipUnlessDBFeature('supports_transactions')
    def test_autocommit_decorator(self):
        """
        The autocommit decorator works exactly the same as the default behavior.
        """
        autocomitted_create_then_fail = transaction.autocommit(
            self.create_a_reporter_then_fail
        )
        self.assertRaises(Exception,
            autocomitted_create_then_fail,
            "Alice", "Smith"
        )
        # Again, the object created before the exception still exists
        self.assertEqual(Reporter.objects.count(), 1)

    @skipUnlessDBFeature('supports_transactions')
    def test_autocommit_decorator_with_using(self):
        """
        The autocommit decorator also works with a using argument.
        """
        autocomitted_create_then_fail = transaction.autocommit(using='default')(
            self.create_a_reporter_then_fail
        )
        self.assertRaises(Exception,
            autocomitted_create_then_fail,
            "Alice", "Smith"
        )
        # Again, the object created before the exception still exists
        self.assertEqual(Reporter.objects.count(), 1)

    @skipUnlessDBFeature('supports_transactions')
    def test_commit_on_success(self):
        """
        With the commit_on_success decorator, the transaction is only committed
        if the function doesn't throw an exception.
        """
        committed_on_success = transaction.commit_on_success(
            self.create_a_reporter_then_fail)
        self.assertRaises(Exception, committed_on_success, "Dirk", "Gently")
        # This time the object never got saved
        self.assertEqual(Reporter.objects.count(), 0)

    @skipUnlessDBFeature('supports_transactions')
    def test_commit_on_success_with_using(self):
        """
        The commit_on_success decorator also works with a using argument.
        """
        using_committed_on_success = transaction.commit_on_success(using='default')(
            self.create_a_reporter_then_fail
        )
        self.assertRaises(Exception,
            using_committed_on_success,
            "Dirk", "Gently"
        )
        # This time the object never got saved
        self.assertEqual(Reporter.objects.count(), 0)

    @skipUnlessDBFeature('supports_transactions')
    def test_commit_on_success_succeed(self):
        """
        If there aren't any exceptions, the data will get saved.
        """
        Reporter.objects.create(first_name="Alice", last_name="Smith")
        remove_comitted_on_success = transaction.commit_on_success(
            self.remove_a_reporter
        )
        remove_comitted_on_success("Alice")
        self.assertEqual(list(Reporter.objects.all()), [])

    @skipUnlessDBFeature('supports_transactions')
    def test_commit_on_success_exit(self):
        @transaction.autocommit()
        def gen_reporter():
            @transaction.commit_on_success
            def create_reporter():
                Reporter.objects.create(first_name="Bobby", last_name="Tables")

            create_reporter()
            # Much more formal
            r = Reporter.objects.get()
            r.first_name = "Robert"
            r.save()

        gen_reporter()
        r = Reporter.objects.get()
        self.assertEqual(r.first_name, "Robert")


    @skipUnlessDBFeature('supports_transactions')
    def test_manually_managed(self):
        """
        You can manually manage transactions if you really want to, but you
        have to remember to commit/rollback.
        """
        manually_managed = transaction.commit_manually(self.manually_managed)
        manually_managed()
        self.assertEqual(Reporter.objects.count(), 1)

    @skipUnlessDBFeature('supports_transactions')
    def test_manually_managed_mistake(self):
        """
        If you forget, you'll get bad errors.
        """
        manually_managed_mistake = transaction.commit_manually(
            self.manually_managed_mistake
        )
        self.assertRaises(transaction.TransactionManagementError,
            manually_managed_mistake)

    @skipUnlessDBFeature('supports_transactions')
    def test_manually_managed_with_using(self):
        """
        The commit_manually function also works with a using argument.
        """
        using_manually_managed_mistake = transaction.commit_manually(using='default')(
            self.manually_managed_mistake
        )
        self.assertRaises(transaction.TransactionManagementError,
            using_manually_managed_mistake
        )


class TransactionRollbackTests(IgnorePendingDeprecationWarningsMixin, TransactionTestCase):

    available_apps = ['transactions']

    def execute_bad_sql(self):
        cursor = connection.cursor()
        cursor.execute("INSERT INTO transactions_reporter (first_name, last_name) VALUES ('Douglas', 'Adams');")

    @skipUnlessDBFeature('requires_rollback_on_dirty_transaction')
    def test_bad_sql(self):
        """
        Regression for #11900: If a function wrapped by commit_on_success
        writes a transaction that can't be committed, that transaction should
        be rolled back. The bug is only visible using the psycopg2 backend,
        though the fix is generally a good idea.
        """
        execute_bad_sql = transaction.commit_on_success(self.execute_bad_sql)
        self.assertRaises(IntegrityError, execute_bad_sql)
        transaction.rollback()

class TransactionContextManagerTests(IgnorePendingDeprecationWarningsMixin, TransactionTestCase):

    available_apps = ['transactions']

    def create_reporter_and_fail(self):
        Reporter.objects.create(first_name="Bob", last_name="Holtzman")
        raise Exception

    @skipUnlessDBFeature('supports_transactions')
    def test_autocommit(self):
        """
        The default behavior is to autocommit after each save() action.
        """
        with self.assertRaises(Exception):
            self.create_reporter_and_fail()
        # The object created before the exception still exists
        self.assertEqual(Reporter.objects.count(), 1)

    @skipUnlessDBFeature('supports_transactions')
    def test_autocommit_context_manager(self):
        """
        The autocommit context manager works exactly the same as the default
        behavior.
        """
        with self.assertRaises(Exception):
            with transaction.autocommit():
                self.create_reporter_and_fail()

        self.assertEqual(Reporter.objects.count(), 1)

    @skipUnlessDBFeature('supports_transactions')
    def test_autocommit_context_manager_with_using(self):
        """
        The autocommit context manager also works with a using argument.
        """
        with self.assertRaises(Exception):
            with transaction.autocommit(using="default"):
                self.create_reporter_and_fail()

        self.assertEqual(Reporter.objects.count(), 1)

    @skipUnlessDBFeature('supports_transactions')
    def test_commit_on_success(self):
        """
        With the commit_on_success context manager, the transaction is only
        committed if the block doesn't throw an exception.
        """
        with self.assertRaises(Exception):
            with transaction.commit_on_success():
                self.create_reporter_and_fail()

        self.assertEqual(Reporter.objects.count(), 0)

    @skipUnlessDBFeature('supports_transactions')
    def test_commit_on_success_with_using(self):
        """
        The commit_on_success context manager also works with a using argument.
        """
        with self.assertRaises(Exception):
            with transaction.commit_on_success(using="default"):
                self.create_reporter_and_fail()

        self.assertEqual(Reporter.objects.count(), 0)

    @skipUnlessDBFeature('supports_transactions')
    def test_commit_on_success_succeed(self):
        """
        If there aren't any exceptions, the data will get saved.
        """
        Reporter.objects.create(first_name="Alice", last_name="Smith")
        with transaction.commit_on_success():
            Reporter.objects.filter(first_name="Alice").delete()

        self.assertQuerysetEqual(Reporter.objects.all(), [])

    @skipUnlessDBFeature('supports_transactions')
    def test_commit_on_success_exit(self):
        with transaction.autocommit():
            with transaction.commit_on_success():
                Reporter.objects.create(first_name="Bobby", last_name="Tables")

            # Much more formal
            r = Reporter.objects.get()
            r.first_name = "Robert"
            r.save()

        r = Reporter.objects.get()
        self.assertEqual(r.first_name, "Robert")

    @skipUnlessDBFeature('supports_transactions')
    def test_manually_managed(self):
        """
        You can manually manage transactions if you really want to, but you
        have to remember to commit/rollback.
        """
        with transaction.commit_manually():
            Reporter.objects.create(first_name="Libby", last_name="Holtzman")
            transaction.commit()
        self.assertEqual(Reporter.objects.count(), 1)

    @skipUnlessDBFeature('supports_transactions')
    def test_manually_managed_mistake(self):
        """
        If you forget, you'll get bad errors.
        """
        with self.assertRaises(transaction.TransactionManagementError):
            with transaction.commit_manually():
                Reporter.objects.create(first_name="Scott", last_name="Browning")

    @skipUnlessDBFeature('supports_transactions')
    def test_manually_managed_with_using(self):
        """
        The commit_manually function also works with a using argument.
        """
        with self.assertRaises(transaction.TransactionManagementError):
            with transaction.commit_manually(using="default"):
                Reporter.objects.create(first_name="Walter", last_name="Cronkite")

    @skipUnlessDBFeature('requires_rollback_on_dirty_transaction')
    def test_bad_sql(self):
        """
        Regression for #11900: If a block wrapped by commit_on_success
        writes a transaction that can't be committed, that transaction should
        be rolled back. The bug is only visible using the psycopg2 backend,
        though the fix is generally a good idea.
        """
        with self.assertRaises(IntegrityError):
            with transaction.commit_on_success():
                cursor = connection.cursor()
                cursor.execute("INSERT INTO transactions_reporter (first_name, last_name) VALUES ('Douglas', 'Adams');")
        transaction.rollback()
