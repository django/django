from django.core.exceptions import ImproperlyConfigured
from django.db import connection, transaction
from django.db.transaction import commit_on_success, commit_manually, TransactionManagementError
from django.test import TransactionTestCase, skipUnlessDBFeature

from models import Mod


class TestTransactionClosing(TransactionTestCase):
    """
    Tests to make sure that transactions are properly closed
    when they should be, and aren't left pending after operations
    have been performed in them. Refs #9964.
    """
    def test_raw_committed_on_success(self):
        """
        Make sure a transaction consisting of raw SQL execution gets
        committed by the commit_on_success decorator.
        """
        @commit_on_success
        def raw_sql():
            "Write a record using raw sql under a commit_on_success decorator"
            cursor = connection.cursor()
            cursor.execute("INSERT into transactions_regress_mod (id,fld) values (17,18)")

        raw_sql()
        # Rollback so that if the decorator didn't commit, the record is unwritten
        transaction.rollback()
        try:
            # Check that the record is in the DB
            obj = Mod.objects.get(pk=17)
            self.assertEqual(obj.fld, 18)
        except Mod.DoesNotExist:
            self.fail("transaction with raw sql not committed")

    def test_commit_manually_enforced(self):
        """
        Make sure that under commit_manually, even "read-only" transaction require closure
        (commit or rollback), and a transaction left pending is treated as an error.
        """
        @commit_manually
        def non_comitter():
            "Execute a managed transaction with read-only operations and fail to commit"
            _ = Mod.objects.count()

        self.assertRaises(TransactionManagementError, non_comitter)

    def test_commit_manually_commit_ok(self):
        """
        Test that under commit_manually, a committed transaction is accepted by the transaction
        management mechanisms
        """
        @commit_manually
        def committer():
            """
            Perform a database query, then commit the transaction
            """
            _ = Mod.objects.count()
            transaction.commit()

        try:
            committer()
        except TransactionManagementError:
            self.fail("Commit did not clear the transaction state")

    def test_commit_manually_rollback_ok(self):
        """
        Test that under commit_manually, a rolled-back transaction is accepted by the transaction
        management mechanisms
        """
        @commit_manually
        def roller_back():
            """
            Perform a database query, then rollback the transaction
            """
            _ = Mod.objects.count()
            transaction.rollback()

        try:
            roller_back()
        except TransactionManagementError:
            self.fail("Rollback did not clear the transaction state")

    def test_commit_manually_enforced_after_commit(self):
        """
        Test that under commit_manually, if a transaction is committed and an operation is
        performed later, we still require the new transaction to be closed
        """
        @commit_manually
        def fake_committer():
            "Query, commit, then query again, leaving with a pending transaction"
            _ = Mod.objects.count()
            transaction.commit()
            _ = Mod.objects.count()

        self.assertRaises(TransactionManagementError, fake_committer)

    @skipUnlessDBFeature('supports_transactions')
    def test_reuse_cursor_reference(self):
        """
        Make sure transaction closure is enforced even when the queries are performed
        through a single cursor reference retrieved in the beginning
        (this is to show why it is wrong to set the transaction dirty only when a cursor
        is fetched from the connection).
        """
        @commit_on_success
        def reuse_cursor_ref():
            """
            Fetch a cursor, perform an query, rollback to close the transaction,
            then write a record (in a new transaction) using the same cursor object
            (reference). All this under commit_on_success, so the second insert should
            be committed.
            """
            cursor = connection.cursor()
            cursor.execute("INSERT into transactions_regress_mod (id,fld) values (1,2)")
            transaction.rollback()
            cursor.execute("INSERT into transactions_regress_mod (id,fld) values (1,2)")

        reuse_cursor_ref()
        # Rollback so that if the decorator didn't commit, the record is unwritten
        transaction.rollback()
        try:
            # Check that the record is in the DB
            obj = Mod.objects.get(pk=1)
            self.assertEqual(obj.fld, 2)
        except Mod.DoesNotExist:
            self.fail("After ending a transaction, cursor use no longer sets dirty")

    def test_failing_query_transaction_closed(self):
        """
        Make sure that under commit_on_success, a transaction is rolled back even if
        the first database-modifying operation fails.
        This is prompted by http://code.djangoproject.com/ticket/6669 (and based on sample
        code posted there to exemplify the problem): Before Django 1.3,
        transactions were only marked "dirty" by the save() function after it successfully
        wrote the object to the database.
        """
        from django.contrib.auth.models import User

        @transaction.commit_on_success
        def create_system_user():
            "Create a user in a transaction"
            user = User.objects.create_user(username='system', password='iamr00t', email='root@SITENAME.com')
            # Redundant, just makes sure the user id was read back from DB
            Mod.objects.create(fld=user.id)

        # Create a user
        create_system_user()

        try:
            # The second call to create_system_user should fail for violating a unique constraint
            # (it's trying to re-create the same user)
            create_system_user()
        except:
            pass
        else:
            raise ImproperlyConfigured('Unique constraint not enforced on django.contrib.auth.models.User')

        try:
            # Try to read the database. If the last transaction was indeed closed,
            # this should cause no problems
            _ = User.objects.all()[0]
        except:
            self.fail("A transaction consisting of a failed operation was not closed.")
