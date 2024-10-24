import re
from unittest import skipUnless

from django.db import connection
from django.test import TestCase

from .models import Comment, Tenant, User


class CompositeFKTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.tenant_1 = Tenant.objects.create()
        cls.tenant_2 = Tenant.objects.create()
        cls.tenant_3 = Tenant.objects.create()
        cls.user_1 = User.objects.create(tenant=cls.tenant_1)
        cls.user_2 = User.objects.create(tenant=cls.tenant_1)
        cls.user_3 = User.objects.create(tenant=cls.tenant_2)
        cls.user_4 = User.objects.create(tenant=cls.tenant_2)
        cls.comment_1 = Comment.objects.create(user=cls.user_1)
        cls.comment_2 = Comment.objects.create(user=cls.user_1)
        cls.comment_3 = Comment.objects.create(user=cls.user_2)
        cls.comment_4 = Comment.objects.create(user=cls.user_3)

    @staticmethod
    def get_constraints(table):
        with connection.cursor() as cursor:
            return connection.introspection.get_constraints(cursor, table)

    @staticmethod
    def get_table_description(table):
        with connection.cursor() as cursor:
            return connection.introspection.get_table_description(cursor, table)

    @skipUnless(connection.vendor == "postgresql", "PostgreSQL specific SQL")
    def test_get_constraints_postgresql(self):
        constraints = self.get_constraints("composite_fk_comment")
        keys = list(constraints.keys())

        fk_pattern = re.compile(
            r"composite_fk_comment_tenant_id_user_id_[\w]{8}_fk_composite"
        )
        fk_key = next(key for key in keys if fk_pattern.fullmatch(key))
        fk_constraint = constraints[fk_key]
        self.assertEqual(fk_constraint["columns"], ["tenant_id", "user_id"])
        self.assertEqual(
            fk_constraint["foreign_key"], ("composite_fk_user", "tenant_id", "id")
        )

        idx_pattern = re.compile(r"composite_fk_comment_tenant_id_user_id_[\w]{8}")
        idx_key = next(key for key in keys if idx_pattern.fullmatch(key))
        idx_constraint = constraints[idx_key]
        self.assertEqual(idx_constraint["columns"], ["tenant_id", "user_id"])
        self.assertTrue(idx_constraint["index"])
        self.assertEqual(idx_constraint["orders"], ["ASC", "ASC"])

    @skipUnless(connection.vendor == "mysql", "MySQL specific SQL")
    def test_get_constraints_mysql(self):
        constraints = self.get_constraints("composite_fk_comment")
        keys = list(constraints.keys())

        fk_pattern = re.compile(
            r"composite_fk_comment_tenant_id_user_id_[\w]{8}_fk_composite"
        )
        fk_key = next(key for key in keys if fk_pattern.fullmatch(key))
        fk_constraint = constraints[fk_key]
        self.assertEqual(fk_constraint["columns"], ["tenant_id", "user_id"])
        self.assertTrue(fk_constraint["index"])
        self.assertEqual(
            fk_constraint["foreign_key"], ("composite_fk_user", "tenant_id", "id")
        )

    @skipUnless(connection.vendor == "oracle", "Oracle specific SQL")
    def test_get_constraints_oracle(self):
        constraints = self.get_constraints("composite_fk_comment")
        keys = list(constraints.keys())

        fk_pattern = re.compile(r"composite_tenant_id_[\w]{8}_f")
        fk_key = next(
            key
            for key in keys
            if fk_pattern.fullmatch(key) and len(constraints[key]["columns"]) == 2
        )
        fk_constraint = constraints[fk_key]
        self.assertEqual(fk_constraint["columns"], ["tenant_id", "user_id"])
        self.assertEqual(
            fk_constraint["foreign_key"], ("composite_fk_user", "tenant_id", "id")
        )

        idx_pattern = re.compile(r"composite__tenant_id__[\w]{8}")
        idx_key = next(key for key in keys if idx_pattern.fullmatch(key))
        idx_constraint = constraints[idx_key]
        self.assertEqual(idx_constraint["columns"], ["tenant_id", "user_id"])
        self.assertTrue(idx_constraint["index"])
        self.assertEqual(idx_constraint["orders"], ["ASC", "ASC"])

    def test_table_description(self):
        table_description = self.get_table_description("composite_fk_comment")
        self.assertEqual(
            ["id", "tenant_id", "user_id"],
            [field_info.name for field_info in table_description],
        )

    def test_get_field(self):
        user = Comment._meta.get_field("user")
        user_id = Comment._meta.get_field("user_id")
        self.assertEqual(user.get_internal_type(), "ForeignKey")
        self.assertEqual(user_id.get_internal_type(), "IntegerField")

    def test_fields(self):
        # user_1
        self.assertSequenceEqual(
            self.user_1.comments.all(), (self.comment_1, self.comment_2)
        )
        # user_2
        self.assertSequenceEqual(self.user_2.comments.all(), (self.comment_3,))
        # user_3
        self.assertSequenceEqual(self.user_3.comments.all(), (self.comment_4,))
        # user_4
        self.assertSequenceEqual(self.user_4.comments.all(), ())
        # comment_1
        self.assertEqual(self.comment_1.user, self.user_1)
        self.assertEqual(self.comment_1.user_id, self.user_1.id)
        self.assertEqual(self.comment_1.tenant_id, self.tenant_1.id)
        self.assertEqual(self.comment_1.tenant, self.tenant_1)
        # comment_2
        self.assertEqual(self.comment_2.user, self.user_1)
        self.assertEqual(self.comment_2.user_id, self.user_1.id)
        self.assertEqual(self.comment_2.tenant_id, self.tenant_1.id)
        self.assertEqual(self.comment_2.tenant, self.tenant_1)
        # comment_3
        self.assertEqual(self.comment_3.user, self.user_2)
        self.assertEqual(self.comment_3.user_id, self.user_2.id)
        self.assertEqual(self.comment_3.tenant_id, self.tenant_1.id)
        self.assertEqual(self.comment_3.tenant, self.tenant_1)
        # comment_4
        self.assertEqual(self.comment_4.user, self.user_3)
        self.assertEqual(self.comment_4.user_id, self.user_3.id)
        self.assertEqual(self.comment_4.tenant_id, self.tenant_2.id)
        self.assertEqual(self.comment_4.tenant, self.tenant_2)
