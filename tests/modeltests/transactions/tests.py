from __future__ import with_statement, absolute_import

from django.db import connection, transaction, IntegrityError
from django.test import TransactionTestCase, skipUnlessDBFeature

from .models import Reporter


class TransactionTests(TransactionTestCase):
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


class TransactionRollbackTests(TransactionTestCase):
    def execute_bad_sql(self):
        cursor = connection.cursor()
        cursor.execute("INSERT INTO transactions_reporter (first_name, last_name) VALUES ('Douglas', 'Adams');")
        transaction.set_dirty()

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

class TransactionContextManagerTests(TransactionTestCase):
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
                transaction.set_dirty()
        transaction.rollback()
