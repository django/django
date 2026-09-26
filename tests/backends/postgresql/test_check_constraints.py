import unittest

from backends import models

from django.db import IntegrityError, connection, transaction
from django.test import TestCase, TransactionTestCase


@unittest.skipUnless(connection.vendor == "postgresql", "PostgreSQL tests")
class CheckDeferredConstraintTests(TransactionTestCase):
    available_apps = ["backends"]

    def test_deferred_constraint_remains_deferred(self):
        transaction_ = transaction.atomic()
        transaction_.__enter__()

        connection.check_constraints()

        # Creating an object with an invalid foreign key does not raise an
        # exception until the transaction commits.
        models.Book.objects.create(author_id=-1)

        with self.assertRaisesRegex(
            IntegrityError,
            expected_regex='"backends_book" violates foreign key constraint',
        ):
            transaction_.__exit__(None, None, None)


@unittest.skipUnless(connection.vendor == "postgresql", "PostgreSQL tests")
class CheckImmediateConstraintTests(TestCase):
    available_apps = ["backends"]

    def test_immediate_constraint_remains_immediate(self):
        try:
            from psycopg import sql
        except ModuleNotFoundError:
            from psycopg2 import sql

        # There is currently no way to create a model with an immediate
        # constraint through the ORM
        # (see https://github.com/django/new-features/issues/212).
        # Therefore, we must manually set the constraint to immediate.
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT conname FROM pg_constraint
                WHERE
                    contype = 'f'
                    AND conrelid::regclass::text = 'backends_book';
                """)
            (constraint_name,) = cursor.fetchone()
            cursor.execute(
                sql.SQL("SET CONSTRAINTS {} IMMEDIATE").format(
                    sql.Identifier(constraint_name)
                )
            )

        connection.check_constraints()

        # Creating an object with an invalid foreign key immediately raises an
        # exception.
        with self.assertRaisesRegex(
            IntegrityError,
            expected_regex='"backends_book" violates foreign key constraint',
        ):
            models.Book.objects.create(author_id=-1)
