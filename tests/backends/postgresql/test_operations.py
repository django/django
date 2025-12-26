import unittest
from unittest import mock

from django.core.management.color import no_style
from django.db import connection, models
from django.db.models.expressions import Col
from django.db.models.functions import Cast
from django.test import SimpleTestCase

from ..models import Author, Book, Person, Tag


@unittest.skipUnless(connection.vendor == "postgresql", "PostgreSQL tests.")
class PostgreSQLOperationsTests(SimpleTestCase):
    def test_sql_flush(self):
        self.assertEqual(
            connection.ops.sql_flush(
                no_style(),
                [Person._meta.db_table, Tag._meta.db_table],
            ),
            ['TRUNCATE "backends_person", "backends_tag";'],
        )

    def test_sql_flush_allow_cascade(self):
        self.assertEqual(
            connection.ops.sql_flush(
                no_style(),
                [Person._meta.db_table, Tag._meta.db_table],
                allow_cascade=True,
            ),
            ['TRUNCATE "backends_person", "backends_tag" CASCADE;'],
        )

    def test_sql_flush_sequences(self):
        self.assertEqual(
            connection.ops.sql_flush(
                no_style(),
                [Person._meta.db_table, Tag._meta.db_table],
                reset_sequences=True,
            ),
            ['TRUNCATE "backends_person", "backends_tag" RESTART IDENTITY;'],
        )

    def test_sql_flush_sequences_allow_cascade(self):
        self.assertEqual(
            connection.ops.sql_flush(
                no_style(),
                [Person._meta.db_table, Tag._meta.db_table],
                reset_sequences=True,
                allow_cascade=True,
            ),
            ['TRUNCATE "backends_person", "backends_tag" RESTART IDENTITY CASCADE;'],
        )

    def test_prepare_join_on_clause_same_type(self):
        author_table = Author._meta.db_table
        author_id_field = Author._meta.get_field("id")
        lhs_expr, rhs_expr = connection.ops.prepare_join_on_clause(
            author_table,
            author_id_field,
            author_table,
            author_id_field,
        )
        self.assertEqual(lhs_expr, Col(author_table, author_id_field))
        self.assertEqual(rhs_expr, Col(author_table, author_id_field))

    def test_prepare_join_on_clause_different_types(self):
        author_table = Author._meta.db_table
        author_id_field = Author._meta.get_field("id")
        book_table = Book._meta.db_table
        book_fk_field = Book._meta.get_field("author")
        lhs_expr, rhs_expr = connection.ops.prepare_join_on_clause(
            author_table,
            author_id_field,
            book_table,
            book_fk_field,
        )
        self.assertEqual(lhs_expr, Col(author_table, author_id_field))
        self.assertEqual(
            rhs_expr, Cast(Col(book_table, book_fk_field), author_id_field)
        )

    def test_bulk_batch_size(self):
        objects = range(2**16)
        max_query_params = 2**16 - 1
        first_name_field = Person._meta.get_field("first_name")
        last_name_field = Person._meta.get_field("last_name")
        composite_pk = models.CompositePrimaryKey("first_name", "last_name")
        composite_pk.fields = [first_name_field, last_name_field]

        self.assertEqual(connection.ops.bulk_batch_size([], objects), len(objects))

        # Without server-side binding.
        with mock.patch.object(
            type(connection.features),
            "max_query_params",
            new_callable=mock.PropertyMock,
            return_value=None,
        ):
            self.assertEqual(
                connection.ops.bulk_batch_size([first_name_field], objects),
                len(objects),
            )

        # With server-side binding.
        with mock.patch.object(
            type(connection.features),
            "max_query_params",
            new_callable=mock.PropertyMock,
            return_value=max_query_params,
        ):
            self.assertEqual(
                connection.ops.bulk_batch_size([first_name_field], objects),
                max_query_params,
            )
            self.assertEqual(
                connection.ops.bulk_batch_size(
                    [first_name_field, last_name_field], objects
                ),
                max_query_params // 2,
            )
            self.assertEqual(
                connection.ops.bulk_batch_size(
                    [composite_pk, first_name_field], objects
                ),
                max_query_params // 3,
            )
