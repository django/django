from django.db import connection
from django.db.models.query import MAX_GET_RESULTS
from django.db.models.query_utils import PathInfo
from django.db.models.sql import Query
from django.test import TestCase
from django.test.utils import CaptureQueriesContext, tag

from .models import Tenant, User, Comment


class BaseTestCase(TestCase):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create()
        cls.user = User.objects.create(tenant=cls.tenant, id=1)
        cls.comment = Comment.objects.create(tenant=cls.tenant, id=1, user=cls.user)


class CompositePKTests(BaseTestCase):
    def test_fields(self):
        self.assertIsInstance(self.tenant.pk, int)
        self.assertGreater(self.tenant.id, 0)
        self.assertEqual(self.tenant.pk, self.tenant.id)

        self.assertIsInstance(self.user.id, int)
        self.assertGreater(self.user.id, 0)
        self.assertEqual(self.user.tenant_id, self.tenant.id)
        self.assertEqual(self.user.pk, (self.user.tenant_id, self.user.id))

        self.assertIsInstance(self.comment.id, int)
        self.assertGreater(self.comment.id, 0)
        self.assertEqual(self.comment.user_id, self.user.id)
        self.assertEqual(self.comment.tenant_id, self.tenant.id)
        self.assertEqual(self.comment.pk, (self.comment.tenant_id, self.comment.id))


class CompositePKDeleteTests(BaseTestCase):
    """
    Test the .delete() method of composite_pk models.
    """

    def test_delete_tenant_by_pk(self):
        t = Tenant._meta.db_table
        u = User._meta.db_table
        c = Comment._meta.db_table

        with CaptureQueriesContext(connection) as context:
            result = Tenant.objects.filter(pk=self.tenant.pk).delete()

        self.assertEqual(
            result,
            (
                3,
                {
                    "composite_pk.Comment": 1,
                    "composite_pk.User": 1,
                    "composite_pk.Tenant": 1,
                },
            ),
        )

        self.assertFalse(Tenant.objects.filter(id=self.tenant.id).exists())
        self.assertFalse(User.objects.filter(id=self.user.id).exists())
        self.assertFalse(Comment.objects.filter(id=self.comment.id).exists())

        self.assertEqual(len(context.captured_queries), 6)
        self.assertEqual(
            context.captured_queries[0]["sql"],
            f'SELECT "{t}"."id" FROM "{t}" WHERE "{t}"."id" = {self.tenant.id}',
        )
        self.assertEqual(
            context.captured_queries[1]["sql"],
            f'SELECT "{u}"."tenant_id", "{u}"."id" '
            f'FROM "{u}" '
            f'WHERE "{u}"."tenant_id" IN ({self.tenant.id})',
        )
        self.assertEqual(
            context.captured_queries[2]["sql"],
            f'DELETE FROM "{c}" '
            f'WHERE ("{c}"."tenant_id" = {self.tenant.id} AND "{c}"."user_id" = {self.user.id})',
        )
        self.assertEqual(
            context.captured_queries[3]["sql"],
            f'DELETE FROM "{c}" WHERE "{c}"."tenant_id" IN ({self.tenant.id})',
        )
        self.assertEqual(
            context.captured_queries[4]["sql"],
            f'DELETE FROM "{u}" '
            f'WHERE ("{u}"."tenant_id" = {self.tenant.id} AND "{u}"."id" = {self.user.id})',
        )
        self.assertEqual(
            context.captured_queries[5]["sql"],
            f'DELETE FROM "{t}" WHERE "{t}"."id" IN ({self.tenant.id})',
        )

    def test_delete_user_by_id(self):
        u = User._meta.db_table
        c = Comment._meta.db_table

        with CaptureQueriesContext(connection) as context:
            result = User.objects.filter(id=self.user.id).delete()

        self.assertEqual(
            result, (2, {"composite_pk.User": 1, "composite_pk.Comment": 1})
        )

        self.assertTrue(Tenant.objects.filter(id=self.tenant.id).exists())
        self.assertFalse(User.objects.filter(id=self.user.id).exists())
        self.assertFalse(Comment.objects.filter(id=self.comment.id).exists())

        self.assertEqual(len(context.captured_queries), 3)
        self.assertEqual(
            context.captured_queries[0]["sql"],
            f'SELECT "{u}"."tenant_id", "{u}"."id" '
            f'FROM "{u}" '
            f'WHERE "{u}"."id" = {self.user.id}',
        )
        self.assertEqual(
            context.captured_queries[1]["sql"],
            f'DELETE FROM "{c}" '
            f'WHERE ("{c}"."tenant_id" = {self.tenant.id} AND "{c}"."user_id" = {self.user.id})',
        )
        self.assertEqual(
            context.captured_queries[2]["sql"],
            f'DELETE FROM "{u}" '
            f'WHERE ("{u}"."tenant_id" = {self.tenant.id} AND "{u}"."id" = {self.user.id})',
        )

    def test_delete_user_by_pk(self):
        u = User._meta.db_table
        c = Comment._meta.db_table

        with CaptureQueriesContext(connection) as context:
            result = User.objects.filter(pk=self.user.pk).delete()

        self.assertEqual(
            result, (2, {"composite_pk.User": 1, "composite_pk.Comment": 1})
        )

        self.assertTrue(Tenant.objects.filter(id=self.tenant.id).exists())
        self.assertFalse(User.objects.filter(id=self.user.id).exists())
        self.assertFalse(Comment.objects.filter(id=self.comment.id).exists())

        self.assertEqual(len(context.captured_queries), 3)
        self.assertEqual(
            context.captured_queries[0]["sql"],
            f'SELECT "{u}"."tenant_id", "{u}"."id" '
            f'FROM "{u}" '
            f'WHERE ("{u}"."tenant_id" = {self.tenant.id} AND "{u}"."id" = {self.user.id})',
        )
        self.assertEqual(
            context.captured_queries[1]["sql"],
            f'DELETE FROM "{c}" '
            f'WHERE ("{c}"."tenant_id" = {self.tenant.id} AND "{c}"."user_id" = {self.user.id})',
        )
        self.assertEqual(
            context.captured_queries[2]["sql"],
            f'DELETE FROM "{u}" '
            f'WHERE ("{u}"."tenant_id" = {self.tenant.id} AND "{u}"."id" = {self.user.id})',
        )


class CompositePKGetTests(BaseTestCase):
    """
    Test the .get() method of composite_pk models.
    """

    def test_get_tenant_by_pk(self):
        t = Tenant._meta.db_table
        test_cases = [
            {"id": self.tenant.id},
            {"pk": self.tenant.pk},
        ]

        for lookup in test_cases:
            with self.subTest(lookup=lookup):
                with CaptureQueriesContext(connection) as context:
                    obj = Tenant.objects.get(**lookup)

                self.assertEqual(obj, self.tenant)
                self.assertEqual(len(context.captured_queries), 1)
                self.assertEqual(
                    context.captured_queries[0]["sql"],
                    f'SELECT "{t}"."id" '
                    f'FROM "{t}" '
                    f'WHERE "{t}"."id" = {self.tenant.id} '
                    f"LIMIT {MAX_GET_RESULTS}",
                )

    def test_get_user_by_pk(self):
        u = User._meta.db_table
        test_cases = [
            {"pk": (self.tenant.id, self.user.id)},
            {"pk": self.user.pk},
        ]

        for lookup in test_cases:
            with self.subTest(lookup=lookup):
                with CaptureQueriesContext(connection) as context:
                    obj = User.objects.get(**lookup)

                self.assertEqual(obj, self.user)
                self.assertEqual(len(context.captured_queries), 1)
                self.assertEqual(
                    context.captured_queries[0]["sql"],
                    f'SELECT "{u}"."tenant_id", "{u}"."id" '
                    f'FROM "{u}" '
                    f'WHERE ("{u}"."tenant_id" = {self.tenant.id} AND "{u}"."id" = {self.user.id}) '
                    f"LIMIT {MAX_GET_RESULTS}",
                )

    def test_get_user_by_field(self):
        u = User._meta.db_table
        test_cases = [
            ({"id": self.user.id}, "id", self.user.id),
            ({"tenant": self.tenant}, "tenant_id", self.tenant.id),
            ({"tenant_id": self.tenant.id}, "tenant_id", self.tenant.id),
            ({"tenant__id": self.tenant.id}, "tenant_id", self.tenant.id),
            ({"tenant__pk": self.tenant.id}, "tenant_id", self.tenant.id),
        ]

        for lookup, column, value in test_cases:
            with self.subTest(lookup=lookup, column=column, value=value):
                with CaptureQueriesContext(connection) as context:
                    obj = User.objects.get(**lookup)

                self.assertEqual(obj, self.user)
                self.assertEqual(len(context.captured_queries), 1)
                self.assertEqual(
                    context.captured_queries[0]["sql"],
                    f'SELECT "{u}"."tenant_id", "{u}"."id" '
                    f'FROM "{u}" '
                    f'WHERE "{u}"."{column}" = {value} '
                    f"LIMIT {MAX_GET_RESULTS}",
                )

    def test_get_comment_by_pk(self):
        c = Comment._meta.db_table

        with CaptureQueriesContext(connection) as context:
            obj = Comment.objects.get(pk=(self.tenant.id, self.comment.id))

        self.assertEqual(obj, self.comment)
        self.assertEqual(len(context.captured_queries), 1)
        self.assertEqual(
            context.captured_queries[0]["sql"],
            f'SELECT "{c}"."tenant_id", "{c}"."id", "{c}"."user_id" '
            f'FROM "{c}" '
            f'WHERE ("{c}"."tenant_id" = {self.tenant.id} AND "{c}"."id" = {self.comment.id}) '
            f"LIMIT {MAX_GET_RESULTS}",
        )

    def test_get_comment_by_field(self):
        c = Comment._meta.db_table
        test_cases = [
            ({"id": self.comment.id}, "id", self.comment.id),
            ({"user_id": self.user.id}, "user_id", self.user.id),
            ({"user__id": self.user.id}, "user_id", self.user.id),
            ({"tenant": self.tenant}, "tenant_id", self.tenant.id),
            ({"tenant_id": self.tenant.id}, "tenant_id", self.tenant.id),
            ({"tenant__id": self.tenant.id}, "tenant_id", self.tenant.id),
            ({"tenant__pk": self.tenant.id}, "tenant_id", self.tenant.id),
        ]

        for lookup, column, value in test_cases:
            with self.subTest(lookup=lookup, column=column, value=value):
                with CaptureQueriesContext(connection) as context:
                    obj = Comment.objects.get(**lookup)

                self.assertEqual(obj, self.comment)
                self.assertEqual(len(context.captured_queries), 1)
                self.assertEqual(
                    context.captured_queries[0]["sql"],
                    f'SELECT "{c}"."tenant_id", "{c}"."id", "{c}"."user_id" '
                    f'FROM "{c}" '
                    f'WHERE "{c}"."{column}" = {value} '
                    f"LIMIT {MAX_GET_RESULTS}",
                )

    def test_get_comment_by_user(self):
        c = Comment._meta.db_table

        with CaptureQueriesContext(connection) as context:
            obj = Comment.objects.get(user=self.user)

        self.assertEqual(obj, self.comment)
        self.assertEqual(len(context.captured_queries), 1)
        self.assertEqual(
            context.captured_queries[0]["sql"],
            f'SELECT "{c}"."tenant_id", "{c}"."id", "{c}"."user_id" '
            f'FROM "{c}" '
            f'WHERE ("{c}"."tenant_id" = {self.tenant.id} AND "{c}"."user_id" = {self.user.id}) '
            f"LIMIT {MAX_GET_RESULTS}",
        )

    def test_get_comment_by_user_pk(self):
        c = Comment._meta.db_table
        u = User._meta.db_table

        with CaptureQueriesContext(connection) as context:
            obj = Comment.objects.get(user__pk=self.user.pk)

        self.assertEqual(obj, self.comment)
        self.assertEqual(len(context.captured_queries), 1)
        self.assertEqual(
            context.captured_queries[0]["sql"],
            f'SELECT "{c}"."tenant_id", "{c}"."id", "{c}"."user_id" '
            f'FROM "{c}" '
            f'INNER JOIN "{u}" ON ("{c}"."tenant_id" = "{u}"."tenant_id" AND "{c}"."user_id" = "{u}"."id") '
            f'WHERE ("{u}"."tenant_id" = {self.tenant.id} AND "{u}"."id" = {self.user.id}) '
            f"LIMIT {MAX_GET_RESULTS}",
        )


class CompositePKCreateTests(BaseTestCase):
    def test_create_user(self):
        u = User._meta.db_table
        test_cases = [
            ({"tenant": self.tenant, "id": 1111}, 1111),
            ({"pk": (self.tenant.id, 1112)}, 1112),
        ]

        for kwargs, value in test_cases:
            with self.subTest(kwargs=kwargs):
                with CaptureQueriesContext(connection) as context:
                    User.objects.create(**kwargs)

                self.assertEqual(len(context.captured_queries), 1)
                self.assertEqual(
                    context.captured_queries[0]["sql"],
                    f'INSERT INTO "{u}" ("tenant_id", "id") '
                    f"VALUES ({self.tenant.id}, {value})",
                )


class NamesToPathTests(TestCase):
    def test_id(self):
        query = Query(User)
        path, final_field, targets, rest = query.names_to_path(["id"], User._meta)

        self.assertEqual(path, [])
        self.assertEqual(final_field, User._meta.get_field("id"))
        self.assertEqual(targets, (User._meta.get_field("id"),))
        self.assertEqual(rest, [])

    def test_pk(self):
        query = Query(User)
        path, final_field, targets, rest = query.names_to_path(["pk"], User._meta)

        self.assertEqual(path, [])
        self.assertEqual(final_field, User._meta.get_field("_pk"))
        self.assertEqual(targets, (User._meta.get_field("_pk"),))
        self.assertEqual(rest, [])

    def test_tenant_id(self):
        query = Query(User)
        path, final_field, targets, rest = query.names_to_path(
            ["tenant", "id"], User._meta
        )

        self.assertEqual(
            path,
            [
                PathInfo(
                    from_opts=User._meta,
                    to_opts=Tenant._meta,
                    target_fields=(Tenant._meta.get_field("id"),),
                    join_field=User._meta.get_field("tenant"),
                    m2m=False,
                    direct=True,
                    filtered_relation=None,
                ),
            ],
        )
        self.assertEqual(final_field, Tenant._meta.get_field("id"))
        self.assertEqual(targets, (Tenant._meta.get_field("id"),))
        self.assertEqual(rest, [])

    def test_user_id(self):
        query = Query(Comment)
        path, final_field, targets, rest = query.names_to_path(
            ["user", "id"], Comment._meta
        )

        self.assertEqual(
            path,
            [
                PathInfo(
                    from_opts=Comment._meta,
                    to_opts=User._meta,
                    target_fields=(
                        User._meta.get_field("tenant"),
                        User._meta.get_field("id"),
                    ),
                    join_field=Comment._meta.get_field("user"),
                    m2m=False,
                    direct=True,
                    filtered_relation=None,
                ),
            ],
        )
        self.assertEqual(final_field, User._meta.get_field("id"))
        self.assertEqual(targets, (User._meta.get_field("id"),))
        self.assertEqual(rest, [])

    def test_user_tenant_id(self):
        query = Query(Comment)
        path, final_field, targets, rest = query.names_to_path(
            ["user", "tenant", "id"], Comment._meta
        )

        self.assertEqual(
            path,
            [
                PathInfo(
                    from_opts=Comment._meta,
                    to_opts=User._meta,
                    target_fields=(
                        User._meta.get_field("tenant"),
                        User._meta.get_field("id"),
                    ),
                    join_field=Comment._meta.get_field("user"),
                    m2m=False,
                    direct=True,
                    filtered_relation=None,
                ),
                PathInfo(
                    from_opts=User._meta,
                    to_opts=Tenant._meta,
                    target_fields=(Tenant._meta.get_field("id"),),
                    join_field=User._meta.get_field("tenant"),
                    m2m=False,
                    direct=True,
                    filtered_relation=None,
                ),
            ],
        )
        self.assertEqual(final_field, Tenant._meta.get_field("id"))
        self.assertEqual(targets, (Tenant._meta.get_field("id"),))
        self.assertEqual(rest, [])
