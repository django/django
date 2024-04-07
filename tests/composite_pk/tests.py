import unittest

from django.db import IntegrityError, connection
from django.db.models import CompositePrimaryKey
from django.test import TestCase

from .models import Comment, Tenant, User


class CompositePKTests(TestCase):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create()
        cls.user = User.objects.create(tenant=cls.tenant, id=1)
        cls.comment = Comment.objects.create(tenant=cls.tenant, id=1, user=cls.user)

    @staticmethod
    def get_constraints(table):
        with connection.cursor() as cursor:
            return connection.introspection.get_constraints(cursor, table)

    def test_pk_updated_if_field_updated(self):
        meta = User._meta
        user = User.objects.get(pk=self.user.pk)
        self.assertEqual(user.pk, (self.tenant.id, self.user.id))
        self.assertTrue(meta.pk.is_set(user.pk))
        user.tenant_id = 9831
        self.assertEqual(user.pk, (9831, self.user.id))
        self.assertTrue(meta.pk.is_set(user.pk))
        user.id = 4321
        self.assertEqual(user.pk, (9831, 4321))
        self.assertTrue(meta.pk.is_set(user.pk))
        user.pk = (9132, 3521)
        self.assertEqual(user.tenant_id, 9132)
        self.assertEqual(user.id, 3521)
        self.assertTrue(meta.pk.is_set(user.pk))
        user.id = None
        self.assertFalse(meta.pk.is_set(user.pk))

    def test_composite_pk_in_fields(self):
        user_fields = {f.name for f in User._meta.get_fields()}
        self.assertEqual(user_fields, {"pk", "tenant", "id", "email", "comments"})

        comment_fields = {f.name for f in Comment._meta.get_fields()}
        self.assertEqual(
            comment_fields,
            {"pk", "tenant", "id", "user_id", "user", "text"},
        )

    def test_pk_field(self):
        pk = User._meta.get_field("pk")
        self.assertIsInstance(pk, CompositePrimaryKey)
        self.assertIs(User._meta.pk, pk)

    def test_error_on_user_pk_conflict(self):
        with self.assertRaises(IntegrityError):
            User.objects.create(tenant=self.tenant, id=self.user.id)

    def test_error_on_comment_pk_conflict(self):
        with self.assertRaises(IntegrityError):
            Comment.objects.create(tenant=self.tenant, id=self.comment.id)

    @unittest.skipUnless(connection.vendor == "postgresql", "PostgreSQL specific test")
    def test_pk_constraints_in_postgresql(self):
        user_constraints = self.get_constraints(User._meta.db_table)
        user_pk = user_constraints["composite_pk_user_pkey"]
        self.assertEqual(user_pk["columns"], ["tenant_id", "id"])
        self.assertTrue(user_pk["primary_key"])

        comment_constraints = self.get_constraints(Comment._meta.db_table)
        comment_pk = comment_constraints["composite_pk_comment_pkey"]
        self.assertEqual(comment_pk["columns"], ["tenant_id", "comment_id"])
        self.assertTrue(comment_pk["primary_key"])

    @unittest.skipUnless(connection.vendor == "sqlite", "SQLite specific test")
    def test_pk_constraints_in_sqlite(self):
        user_constraints = self.get_constraints(User._meta.db_table)
        user_pk = user_constraints["__primary__"]
        self.assertEqual(user_pk["columns"], ["tenant_id", "id"])
        self.assertTrue(user_pk["primary_key"])

        comment_constraints = self.get_constraints(Comment._meta.db_table)
        comment_pk = comment_constraints["__primary__"]
        self.assertEqual(comment_pk["columns"], ["tenant_id", "comment_id"])
        self.assertTrue(comment_pk["primary_key"])

    def test_in_bulk(self):
        """
        Test the .in_bulk() method of composite_pk models.
        """
        result = Comment.objects.in_bulk()
        self.assertEqual(result, {self.comment.pk: self.comment})

        result = Comment.objects.in_bulk([self.comment.pk])
        self.assertEqual(result, {self.comment.pk: self.comment})

    def test_iterator(self):
        """
        Test the .iterator() method of composite_pk models.
        """
        result = list(Comment.objects.iterator())
        self.assertEqual(result, [self.comment])
