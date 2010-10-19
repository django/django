from __future__ import with_statement

from django.db import connection, transaction, IntegrityError
from django.test import TransactionTestCase, skipUnlessDBFeature

from models import Reporter


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
