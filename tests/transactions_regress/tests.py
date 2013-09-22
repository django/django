from __future__ import absolute_import

from django.db import (connection, connections, transaction, DEFAULT_DB_ALIAS, DatabaseError,
                       IntegrityError)
from django.db.transaction import commit_on_success, commit_manually, TransactionManagementError
from django.test import TransactionTestCase, skipUnlessDBFeature
from django.test.utils import override_settings, IgnorePendingDeprecationWarningsMixin
from django.utils.unittest import skipIf, skipUnless, SkipTest

from .models import Mod, M2mA, M2mB, SubMod

class ModelInheritanceTests(TransactionTestCase):

    available_apps = ['transactions_regress']

    def test_save(self):
        # First, create a SubMod, then try to save another with conflicting
        # cnt field. The problem was that transactions were committed after
        # every parent save when not in managed transaction. As the cnt
        # conflict is in the second model, we can check if the first save
        # was committed or not.
        SubMod(fld=1, cnt=1).save()
        # We should have committed the transaction for the above - assert this.
        connection.rollback()
        self.assertEqual(SubMod.objects.count(), 1)
        try:
            SubMod(fld=2, cnt=1).save()
        except IntegrityError:
            connection.rollback()
        self.assertEqual(SubMod.objects.count(), 1)
        self.assertEqual(Mod.objects.count(), 1)

class TestTransactionClosing(IgnorePendingDeprecationWarningsMixin, TransactionTestCase):
    """
    Tests to make sure that transactions are properly closed
    when they should be, and aren't left pending after operations
    have been performed in them. Refs #9964.
    """

    available_apps = [
        'transactions_regress',
        'django.contrib.auth',
        'django.contrib.contenttypes',
    ]

    def test_raw_committed_on_success(self):
        """
        Make sure a transaction consisting of raw SQL execution gets
        committed by the commit_on_success decorator.
        """
        @commit_on_success
        def raw_sql():
            "Write a record using raw sql under a commit_on_success decorator"
            cursor = connection.cursor()
            cursor.execute("INSERT into transactions_regress_mod (fld) values (18)")

        raw_sql()
        # Rollback so that if the decorator didn't commit, the record is unwritten
        transaction.rollback()
        self.assertEqual(Mod.objects.count(), 1)
        # Check that the record is in the DB
        obj = Mod.objects.all()[0]
        self.assertEqual(obj.fld, 18)

    def test_commit_manually_enforced(self):
        """
        Make sure that under commit_manually, even "read-only" transaction require closure
        (commit or rollback), and a transaction left pending is treated as an error.
        """
        @commit_manually
        def non_comitter():
            "Execute a managed transaction with read-only operations and fail to commit"
            Mod.objects.count()

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
            Mod.objects.count()
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
            Mod.objects.count()
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
            Mod.objects.count()
            transaction.commit()
            Mod.objects.count()

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
            cursor.execute("INSERT into transactions_regress_mod (fld) values (2)")
            transaction.rollback()
            cursor.execute("INSERT into transactions_regress_mod (fld) values (2)")

        reuse_cursor_ref()
        # Rollback so that if the decorator didn't commit, the record is unwritten
        transaction.rollback()
        self.assertEqual(Mod.objects.count(), 1)
        obj = Mod.objects.all()[0]
        self.assertEqual(obj.fld, 2)

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
            user = User.objects.create_user(username='system', password='iamr00t',
                                            email='root@SITENAME.com')
            # Redundant, just makes sure the user id was read back from DB
            Mod.objects.create(fld=user.pk)

        # Create a user
        create_system_user()

        with self.assertRaises(DatabaseError):
            # The second call to create_system_user should fail for violating
            # a unique constraint (it's trying to re-create the same user)
            create_system_user()

        # Try to read the database. If the last transaction was indeed closed,
        # this should cause no problems
        User.objects.all()[0]

    @override_settings(DEBUG=True)
    def test_failing_query_transaction_closed_debug(self):
        """
        Regression for #6669. Same test as above, with DEBUG=True.
        """
        self.test_failing_query_transaction_closed()

@skipIf(connection.vendor == 'sqlite'
        and connection.settings_dict['TEST_NAME'] in (None, '', ':memory:'),
        "Cannot establish two connections to an in-memory SQLite database.")
class TestNewConnection(IgnorePendingDeprecationWarningsMixin, TransactionTestCase):
    """
    Check that new connections don't have special behaviour.
    """

    available_apps = ['transactions_regress']

    def setUp(self):
        self._old_backend = connections[DEFAULT_DB_ALIAS]
        settings = self._old_backend.settings_dict.copy()
        new_backend = self._old_backend.__class__(settings, DEFAULT_DB_ALIAS)
        connections[DEFAULT_DB_ALIAS] = new_backend

    def tearDown(self):
        try:
            connections[DEFAULT_DB_ALIAS].abort()
            connections[DEFAULT_DB_ALIAS].close()
        finally:
            connections[DEFAULT_DB_ALIAS] = self._old_backend

    def test_commit(self):
        """
        Users are allowed to commit and rollback connections.
        """
        connection.set_autocommit(False)
        try:
            # The starting value is False, not None.
            self.assertIs(connection._dirty, False)
            list(Mod.objects.all())
            self.assertTrue(connection.is_dirty())
            connection.commit()
            self.assertFalse(connection.is_dirty())
            list(Mod.objects.all())
            self.assertTrue(connection.is_dirty())
            connection.rollback()
            self.assertFalse(connection.is_dirty())
        finally:
            connection.set_autocommit(True)

    def test_enter_exit_management(self):
        orig_dirty = connection._dirty
        connection.enter_transaction_management()
        connection.leave_transaction_management()
        self.assertEqual(orig_dirty, connection._dirty)


@skipUnless(connection.vendor == 'postgresql',
            "This test only valid for PostgreSQL")
class TestPostgresAutocommitAndIsolation(IgnorePendingDeprecationWarningsMixin, TransactionTestCase):
    """
    Tests to make sure psycopg2's autocommit mode and isolation level
    is restored after entering and leaving transaction management.
    Refs #16047, #18130.
    """

    available_apps = ['transactions_regress']

    def setUp(self):
        from psycopg2.extensions import (ISOLATION_LEVEL_AUTOCOMMIT,
                                         ISOLATION_LEVEL_SERIALIZABLE,
                                         TRANSACTION_STATUS_IDLE)
        self._autocommit = ISOLATION_LEVEL_AUTOCOMMIT
        self._serializable = ISOLATION_LEVEL_SERIALIZABLE
        self._idle = TRANSACTION_STATUS_IDLE

        # We want a clean backend with autocommit = True, so
        # first we need to do a bit of work to have that.
        self._old_backend = connections[DEFAULT_DB_ALIAS]
        settings = self._old_backend.settings_dict.copy()
        opts = settings['OPTIONS'].copy()
        opts['isolation_level'] = ISOLATION_LEVEL_SERIALIZABLE
        settings['OPTIONS'] = opts
        new_backend = self._old_backend.__class__(settings, DEFAULT_DB_ALIAS)
        connections[DEFAULT_DB_ALIAS] = new_backend

    def tearDown(self):
        try:
            connections[DEFAULT_DB_ALIAS].abort()
        finally:
            connections[DEFAULT_DB_ALIAS].close()
            connections[DEFAULT_DB_ALIAS] = self._old_backend

    def test_initial_autocommit_state(self):
        # Autocommit is activated when the connection is created.
        connection.cursor().close()
        self.assertTrue(connection.autocommit)

    def test_transaction_management(self):
        transaction.enter_transaction_management()
        self.assertFalse(connection.autocommit)
        self.assertEqual(connection.isolation_level, self._serializable)

        transaction.leave_transaction_management()
        self.assertTrue(connection.autocommit)

    def test_transaction_stacking(self):
        transaction.enter_transaction_management()
        self.assertFalse(connection.autocommit)
        self.assertEqual(connection.isolation_level, self._serializable)

        transaction.enter_transaction_management()
        self.assertFalse(connection.autocommit)
        self.assertEqual(connection.isolation_level, self._serializable)

        transaction.leave_transaction_management()
        self.assertFalse(connection.autocommit)
        self.assertEqual(connection.isolation_level, self._serializable)

        transaction.leave_transaction_management()
        self.assertTrue(connection.autocommit)

    def test_enter_autocommit(self):
        transaction.enter_transaction_management()
        self.assertFalse(connection.autocommit)
        self.assertEqual(connection.isolation_level, self._serializable)
        list(Mod.objects.all())
        self.assertTrue(transaction.is_dirty())
        # Enter autocommit mode again.
        transaction.enter_transaction_management(False)
        self.assertFalse(transaction.is_dirty())
        self.assertEqual(
            connection.connection.get_transaction_status(),
            self._idle)
        list(Mod.objects.all())
        self.assertFalse(transaction.is_dirty())
        transaction.leave_transaction_management()
        self.assertFalse(connection.autocommit)
        self.assertEqual(connection.isolation_level, self._serializable)
        transaction.leave_transaction_management()
        self.assertTrue(connection.autocommit)


class TestManyToManyAddTransaction(IgnorePendingDeprecationWarningsMixin, TransactionTestCase):

    available_apps = ['transactions_regress']

    def test_manyrelated_add_commit(self):
        "Test for https://code.djangoproject.com/ticket/16818"
        a = M2mA.objects.create()
        b = M2mB.objects.create(fld=10)
        a.others.add(b)

        # We're in a TransactionTestCase and have not changed transaction
        # behavior from default of "autocommit", so this rollback should not
        # actually do anything. If it does in fact undo our add, that's a bug
        # that the bulk insert was not auto-committed.
        transaction.rollback()
        self.assertEqual(a.others.count(), 1)


class SavepointTest(IgnorePendingDeprecationWarningsMixin, TransactionTestCase):

    available_apps = ['transactions_regress']

    @skipIf(connection.vendor == 'sqlite',
            "SQLite doesn't support savepoints in managed mode")
    @skipUnlessDBFeature('uses_savepoints')
    def test_savepoint_commit(self):
        @commit_manually
        def work():
            mod = Mod.objects.create(fld=1)
            pk = mod.pk
            sid = transaction.savepoint()
            Mod.objects.filter(pk=pk).update(fld=10)
            transaction.savepoint_commit(sid)
            mod2 = Mod.objects.get(pk=pk)
            transaction.commit()
            self.assertEqual(mod2.fld, 10)

        work()

    @skipIf(connection.vendor == 'sqlite',
            "SQLite doesn't support savepoints in managed mode")
    @skipUnlessDBFeature('uses_savepoints')
    def test_savepoint_rollback(self):
        # _mysql_storage_engine issues a query and as such can't be applied in
        # a skipIf decorator since that would execute the query on module load.
        if (connection.vendor == 'mysql' and
            connection.features._mysql_storage_engine == 'MyISAM'):
            raise SkipTest("MyISAM MySQL storage engine doesn't support savepoints")
        @commit_manually
        def work():
            mod = Mod.objects.create(fld=1)
            pk = mod.pk
            sid = transaction.savepoint()
            Mod.objects.filter(pk=pk).update(fld=20)
            transaction.savepoint_rollback(sid)
            mod2 = Mod.objects.get(pk=pk)
            transaction.commit()
            self.assertEqual(mod2.fld, 1)

        work()
