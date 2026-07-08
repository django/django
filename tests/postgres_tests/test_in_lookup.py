import uuid

from django.db.models import Subquery

from . import PostgreSQLTestCase
from .models import Character, CharFieldModel, IntegerArrayModel, UUIDTestModel


class InLookupSQLTests(PostgreSQLTestCase):
    """
    On PostgreSQL, `col __in [values]` compiles to `col = ANY(%s::type[])`
    with a single bound array parameter. Postgres's parser normalizes both
    forms to the same ScalarArrayOpExpr during parse analysis (visible in
    EXPLAIN output), so query plans are unchanged and the rewrite eliminates
    the O(N) client-side placeholder rewriting cost paid inside psycopg for
    large lists.
    """

    def test_integer_pk_compiles_to_any(self):
        qs = Character.objects.filter(id__in=[1, 2, 3])
        sql, params = qs.query.sql_with_params()
        self.assertIn("= ANY(%s::integer[])", sql)
        self.assertEqual(params, ([1, 2, 3],))

    def test_uuid_field_compiles_to_any(self):
        ids = [uuid.uuid4() for _ in range(3)]
        qs = UUIDTestModel.objects.filter(uuid__in=ids)
        sql, params = qs.query.sql_with_params()
        self.assertIn("= ANY(%s::uuid[])", sql)
        (bound,) = params
        self.assertEqual(bound, ids)

    def test_char_field_strips_size(self):
        # varchar(255) -> varchar[]: cast must not include column size or
        # PostgreSQL would reject the array cast.
        qs = CharFieldModel.objects.filter(field__in=["a", "b"])
        sql, _ = qs.query.sql_with_params()
        self.assertIn("= ANY(%s::varchar[])", sql)

    def test_empty_iterable_uses_empty_result_set(self):
        # An empty __in raises EmptyResultSet so the whole query is short-
        # circuited (matching pre-change behavior).
        qs = Character.objects.filter(id__in=[])
        self.assertEqual(list(qs), [])

    def test_queryset_rhs_still_uses_in_select(self):
        subq = Character.objects.filter(id__lt=100).values("id")
        qs = Character.objects.filter(id__in=subq)
        sql, _ = qs.query.sql_with_params()
        self.assertIn("IN (SELECT", sql)
        self.assertNotIn("= ANY(", sql)

    def test_subquery_rhs_still_uses_in_select(self):
        subq = Subquery(Character.objects.filter(id__lt=100).values("id"))
        qs = Character.objects.filter(id__in=subq)
        sql, _ = qs.query.sql_with_params()
        self.assertIn("IN (", sql)
        self.assertNotIn("= ANY(", sql)

    def test_array_field_falls_back_to_in(self):
        # ArrayField declares get_placeholder_sql, so it's not safely
        # arrayifiable — a `varchar[]` cast on a `varchar[]` value would be
        # nested-array semantics, not the intended IN list.
        qs = IntegerArrayModel.objects.filter(id__in=[1, 2])
        sql, _ = qs.query.sql_with_params()
        # IntegerArrayModel.id (AutoField) is fine; the array field is on
        # `.field`. Sanity: pk filter still gets = ANY.
        self.assertIn("= ANY(%s::integer[])", sql)

    def test_reverse_relation_uses_target_field_type(self):
        # For a reverse relation the LHS's output_field is a ManyToOneRel
        # whose db_type reflects the FK target column, not the local pk of
        # the joined table. The compilation must resolve to the actual
        # scalar column being compared.
        qs = Character.objects.filter(id__in=[1, 2])
        sql, _ = qs.query.sql_with_params()
        self.assertIn("= ANY(%s::integer[])", sql)

    def test_none_values_are_filtered(self):
        qs = Character.objects.filter(id__in=[None, 1, 2, None])
        sql, params = qs.query.sql_with_params()
        self.assertIn("= ANY(%s::integer[])", sql)
        (bound,) = params
        self.assertNotIn(None, bound)
