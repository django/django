from django.test import TransactionTestCase
from django.db import connection, transaction, IntegrityError, DEFAULT_DB_ALIAS
from django.conf import settings

from models import Reporter

PGSQL = 'psycopg2' in settings.DATABASES[DEFAULT_DB_ALIAS]['ENGINE']
MYSQL = 'mysql' in settings.DATABASES[DEFAULT_DB_ALIAS]['ENGINE']

class TransactionTests(TransactionTestCase):

    if not MYSQL:

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

        def execute_bad_sql(self):
            cursor = connection.cursor()
            cursor.execute("INSERT INTO transactions_reporter (first_name, last_name) VALUES ('Douglas', 'Adams');")
            transaction.set_dirty()

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

        def test_manually_managed(self):
            """
            You can manually manage transactions if you really want to, but you
            have to remember to commit/rollback.
            """
            manually_managed = transaction.commit_manually(self.manually_managed)
            manually_managed()
            self.assertEqual(Reporter.objects.count(), 1)

        def test_manually_managed_mistake(self):
            """
            If you forget, you'll get bad errors.
            """
            manually_managed_mistake = transaction.commit_manually(
                self.manually_managed_mistake
            )
            self.assertRaises(transaction.TransactionManagementError,
                manually_managed_mistake)

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

    if PGSQL:

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
