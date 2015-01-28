from __future__ import unicode_literals

import threading
import time

from multiple_database.routers import TestRouter

from django.conf import settings
from django.db import connection, router, transaction
from django.db.utils import DEFAULT_DB_ALIAS, ConnectionHandler, DatabaseError
from django.test import (
    TransactionTestCase, override_settings, skipIfDBFeature,
    skipUnlessDBFeature,
)

from .models import Person


# We need to set settings.DEBUG to True so we can capture the output SQL
# to examine.
@override_settings(DEBUG=True)
class SelectForUpdateTests(TransactionTestCase):

    available_apps = ['select_for_update']

    def setUp(self):
        # This is executed in autocommit mode so that code in
        # run_select_for_update can see this data.
        self.person = Person.objects.create(name='Reinhardt')

        # We need another database connection in transaction to test that one
        # connection issuing a SELECT ... FOR UPDATE will block.
        new_connections = ConnectionHandler(settings.DATABASES)
        self.new_connection = new_connections[DEFAULT_DB_ALIAS]

    def tearDown(self):
        try:
            self.end_blocking_transaction()
        except (DatabaseError, AttributeError):
            pass
        self.new_connection.close()

    def start_blocking_transaction(self):
        self.new_connection.set_autocommit(False)
        # Start a blocking transaction. At some point,
        # end_blocking_transaction() should be called.
        self.cursor = self.new_connection.cursor()
        sql = 'SELECT * FROM %(db_table)s %(for_update)s;' % {
            'db_table': Person._meta.db_table,
            'for_update': self.new_connection.ops.for_update_sql(),
        }
        self.cursor.execute(sql, ())
        self.cursor.fetchone()

    def end_blocking_transaction(self):
        # Roll back the blocking transaction.
        self.new_connection.rollback()
        self.new_connection.set_autocommit(True)

    def has_for_update_sql(self, tested_connection, nowait=False):
        # Examine the SQL that was executed to determine whether it
        # contains the 'SELECT..FOR UPDATE' stanza.
        for_update_sql = tested_connection.ops.for_update_sql(nowait)
        sql = tested_connection.queries[-1]['sql']
        return bool(sql.find(for_update_sql) > -1)

    @skipUnlessDBFeature('has_select_for_update')
    def test_for_update_sql_generated(self):
        """
        Test that the backend's FOR UPDATE variant appears in
        generated SQL when select_for_update is invoked.
        """
        with transaction.atomic():
            list(Person.objects.all().select_for_update())
        self.assertTrue(self.has_for_update_sql(connection))

    @skipUnlessDBFeature('has_select_for_update_nowait')
    def test_for_update_sql_generated_nowait(self):
        """
        Test that the backend's FOR UPDATE NOWAIT variant appears in
        generated SQL when select_for_update is invoked.
        """
        with transaction.atomic():
            list(Person.objects.all().select_for_update(nowait=True))
        self.assertTrue(self.has_for_update_sql(connection, nowait=True))

    @skipUnlessDBFeature('has_select_for_update_nowait')
    def test_nowait_raises_error_on_block(self):
        """
        If nowait is specified, we expect an error to be raised rather
        than blocking.
        """
        self.start_blocking_transaction()
        status = []

        thread = threading.Thread(
            target=self.run_select_for_update,
            args=(status,),
            kwargs={'nowait': True},
        )

        thread.start()
        time.sleep(1)
        thread.join()
        self.end_blocking_transaction()
        self.assertIsInstance(status[-1], DatabaseError)

    @skipIfDBFeature('has_select_for_update_nowait')
    @skipUnlessDBFeature('has_select_for_update')
    def test_unsupported_nowait_raises_error(self):
        """
        If a SELECT...FOR UPDATE NOWAIT is run on a database backend
        that supports FOR UPDATE but not NOWAIT, then we should find
        that a DatabaseError is raised.
        """
        self.assertRaises(
            DatabaseError,
            list,
            Person.objects.all().select_for_update(nowait=True)
        )

    @skipUnlessDBFeature('has_select_for_update')
    def test_for_update_requires_transaction(self):
        """
        Test that a TransactionManagementError is raised
        when a select_for_update query is executed outside of a transaction.
        """
        with self.assertRaises(transaction.TransactionManagementError):
            list(Person.objects.all().select_for_update())

    @skipUnlessDBFeature('has_select_for_update')
    def test_for_update_requires_transaction_only_in_execution(self):
        """
        Test that no TransactionManagementError is raised
        when select_for_update is invoked outside of a transaction -
        only when the query is executed.
        """
        people = Person.objects.all().select_for_update()
        with self.assertRaises(transaction.TransactionManagementError):
            list(people)

    def run_select_for_update(self, status, nowait=False):
        """
        Utility method that runs a SELECT FOR UPDATE against all
        Person instances. After the select_for_update, it attempts
        to update the name of the only record, save, and commit.

        This function expects to run in a separate thread.
        """
        status.append('started')
        try:
            # We need to enter transaction management again, as this is done on
            # per-thread basis
            with transaction.atomic():
                people = list(
                    Person.objects.all().select_for_update(nowait=nowait)
                )
                people[0].name = 'Fred'
                people[0].save()
        except DatabaseError as e:
            status.append(e)
        finally:
            # This method is run in a separate thread. It uses its own
            # database connection. Close it without waiting for the GC.
            connection.close()

    @skipUnlessDBFeature('has_select_for_update')
    @skipUnlessDBFeature('supports_transactions')
    def test_block(self):
        """
        Check that a thread running a select_for_update that
        accesses rows being touched by a similar operation
        on another connection blocks correctly.
        """
        # First, let's start the transaction in our thread.
        self.start_blocking_transaction()

        # Now, try it again using the ORM's select_for_update
        # facility. Do this in a separate thread.
        status = []
        thread = threading.Thread(
            target=self.run_select_for_update, args=(status,)
        )

        # The thread should immediately block, but we'll sleep
        # for a bit to make sure.
        thread.start()
        sanity_count = 0
        while len(status) != 1 and sanity_count < 10:
            sanity_count += 1
            time.sleep(1)
        if sanity_count >= 10:
            raise ValueError('Thread did not run and block')

        # Check the person hasn't been updated. Since this isn't
        # using FOR UPDATE, it won't block.
        p = Person.objects.get(pk=self.person.pk)
        self.assertEqual('Reinhardt', p.name)

        # When we end our blocking transaction, our thread should
        # be able to continue.
        self.end_blocking_transaction()
        thread.join(5.0)

        # Check the thread has finished. Assuming it has, we should
        # find that it has updated the person's name.
        self.assertFalse(thread.isAlive())

        # We must commit the transaction to ensure that MySQL gets a fresh read,
        # since by default it runs in REPEATABLE READ mode
        transaction.commit()

        p = Person.objects.get(pk=self.person.pk)
        self.assertEqual('Fred', p.name)

    @skipUnlessDBFeature('has_select_for_update')
    def test_raw_lock_not_available(self):
        """
        Check that running a raw query which can't obtain a FOR UPDATE lock
        raises the correct exception
        """
        self.start_blocking_transaction()

        def raw(status):
            try:
                list(
                    Person.objects.raw(
                        'SELECT * FROM %s %s' % (
                            Person._meta.db_table,
                            connection.ops.for_update_sql(nowait=True)
                        )
                    )
                )
            except DatabaseError as e:
                status.append(e)
            finally:
                # This method is run in a separate thread. It uses its own
                # database connection. Close it without waiting for the GC.
                connection.close()

        status = []
        thread = threading.Thread(target=raw, kwargs={'status': status})
        thread.start()
        time.sleep(1)
        thread.join()
        self.end_blocking_transaction()
        self.assertIsInstance(status[-1], DatabaseError)

    @skipUnlessDBFeature('has_select_for_update')
    @override_settings(DATABASE_ROUTERS=[TestRouter()])
    def test_select_for_update_on_multidb(self):
        query = Person.objects.select_for_update()
        self.assertEqual(router.db_for_write(Person), query.db)

    @skipUnlessDBFeature('has_select_for_update')
    def test_select_for_update_with_get(self):
        with transaction.atomic():
            person = Person.objects.select_for_update().get(name='Reinhardt')
        self.assertEqual(person.name, 'Reinhardt')
