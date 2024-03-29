import unittest

from django.db import connection
from django.db.models.query_utils import PathInfo
from django.db.models.sql import Query
from django.test import TestCase

from .models import Comment, Tenant, User


def get_constraints(table):
    with connection.cursor() as cursor:
        return connection.introspection.get_constraints(cursor, table)


class CompositePKTests(TestCase):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create()
        cls.user = User.objects.create(tenant=cls.tenant, id=1)
        cls.comment = Comment.objects.create(tenant=cls.tenant, id=1, user=cls.user)

    def test_fields(self):
        self.assertIsInstance(self.tenant.pk, int)
        self.assertGreater(self.tenant.id, 0)
        self.assertEqual(self.tenant.pk, self.tenant.id)

        self.assertIsInstance(self.user.id, int)
        self.assertGreater(self.user.id, 0)
        self.assertEqual(self.user.tenant_id, self.tenant.id)
        self.assertEqual(self.user.pk, (self.user.tenant_id, self.user.id))
        self.assertEqual(self.user.composite_pk, self.user.pk)

        self.assertIsInstance(self.comment.id, int)
        self.assertGreater(self.comment.id, 0)
        self.assertEqual(self.comment.user_id, self.user.id)
        self.assertEqual(self.comment.tenant_id, self.tenant.id)
        self.assertEqual(self.comment.pk, (self.comment.tenant_id, self.comment.id))
        self.assertEqual(self.comment.composite_pk, self.comment.pk)

    def test_pk_updated_if_field_updated(self):
        user = User.objects.get(pk=self.user.pk)
        self.assertEqual(user.pk, (self.tenant.id, self.user.id))
        user.tenant_id = 9831
        self.assertEqual(user.pk, (9831, self.user.id))
        user.id = 4321
        self.assertEqual(user.pk, (9831, 4321))
        user.pk = (9132, 3521)
        self.assertEqual(user.tenant_id, 9132)
        self.assertEqual(user.id, 3521)

    def test_composite_pk_in_fields(self):
        user_fields = {f.name for f in User._meta.get_fields()}
        self.assertEqual(user_fields, {"id", "tenant", "composite_pk"})

        comment_fields = {f.name for f in Comment._meta.get_fields()}
        self.assertEqual(
            comment_fields, {"id", "tenant", "user_id", "user", "composite_pk"}
        )

    def test_error_on_pk_conflict(self):
        with self.assertRaises(Exception):
            User.objects.create(tenant=self.tenant, id=self.user.id)
        with self.assertRaises(Exception):
            Comment.objects.create(tenant=self.tenant, id=self.comment.id)

    @unittest.skipUnless(connection.vendor == "postgresql", "PostgreSQL specific test")
    def test_pk_constraints_in_postgresql(self):
        user_constraints = get_constraints(User._meta.db_table)
        user_pk = user_constraints["composite_pk_user_pkey"]
        self.assertEqual(user_pk["columns"], ["tenant_id", "id"])
        self.assertTrue(user_pk["primary_key"])

        comment_constraints = get_constraints(Comment._meta.db_table)
        comment_pk = comment_constraints["composite_pk_comment_pkey"]
        self.assertEqual(comment_pk["columns"], ["tenant_id", "id"])
        self.assertTrue(comment_pk["primary_key"])

    @unittest.skipUnless(connection.vendor == "sqlite", "SQLite specific test")
    def test_pk_constraints_in_sqlite(self):
        user_constraints = get_constraints(User._meta.db_table)
        user_pk = user_constraints["__primary__"]
        self.assertEqual(user_pk["columns"], ["tenant_id", "id"])
        self.assertTrue(user_pk["primary_key"])

        comment_constraints = get_constraints(Comment._meta.db_table)
        comment_pk = comment_constraints["__primary__"]
        self.assertEqual(comment_pk["columns"], ["tenant_id", "id"])
        self.assertTrue(comment_pk["primary_key"])

    def test_comments_in_bulk(self):
        result = Comment.objects.in_bulk()
        self.assertEqual(result, {self.comment.pk: self.comment})

        result = Comment.objects.in_bulk([self.comment.pk])
        self.assertEqual(result, {self.comment.pk: self.comment})


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
        self.assertEqual(final_field, User._meta.get_field("composite_pk"))
        self.assertEqual(targets, (User._meta.get_field("composite_pk"),))
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
