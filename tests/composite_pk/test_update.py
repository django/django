import unittest

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from .models import Comment, Tenant, User


class CompositePKUpdateTests(TestCase):
    """
    Test the .update(), .save(), .bulk_update(), .update_or_create() methods of
    composite_pk models.
    """

    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create()
        cls.user = User.objects.create(tenant=cls.tenant, id=1)
        cls.comment = Comment.objects.create(tenant=cls.tenant, id=1, user=cls.user)

    def test_update_user(self):
        with CaptureQueriesContext(connection) as context:
            result = User.objects.filter(pk=self.user.pk).update(id=8341)

        self.assertEqual(result, 1)
        self.assertFalse(User.objects.filter(pk=self.user.pk).exists())
        self.assertEqual(User.objects.all().count(), 1)
        user = User.objects.get(pk=(self.tenant.id, 8341))
        self.assertEqual(user.tenant, self.tenant)
        self.assertEqual(user.tenant_id, self.tenant.id)
        self.assertEqual(user.id, 8341)
        self.assertEqual(len(context.captured_queries), 1)
        if connection.vendor in ("sqlite", "postgresql"):
            u = User._meta.db_table
            self.assertEqual(
                context.captured_queries[0]["sql"],
                f'UPDATE "{u}" '
                'SET "id" = 8341 '
                f'WHERE ("{u}"."tenant_id" = {self.tenant.id} '
                f'AND "{u}"."id" = {self.user.id})',
            )

    def test_save_comment(self):
        comment = Comment.objects.get(pk=self.comment.pk)
        comment.user = User.objects.create(tenant=self.tenant, id=8214)

        with CaptureQueriesContext(connection) as context:
            comment.save()

        self.assertEqual(Comment.objects.all().count(), 1)
        self.assertEqual(len(context.captured_queries), 1)
        if connection.vendor in ("sqlite", "postgresql"):
            c = Comment._meta.db_table
            self.assertEqual(
                context.captured_queries[0]["sql"],
                f'UPDATE "{c}" '
                f'SET "tenant_id" = {self.tenant.id}, "id" = {self.comment.id}, '
                f'"user_id" = 8214 '
                f'WHERE ("{c}"."tenant_id" = {self.tenant.id} '
                f'AND "{c}"."id" = {self.comment.id})',
            )

    @unittest.skipUnless(connection.vendor == "sqlite", "SQLite specific test")
    def test_bulk_update_comments_in_sqlite(self):
        user_1 = User.objects.create(pk=(self.tenant.id, 1352))
        user_2 = User.objects.create(pk=(self.tenant.id, 9314))
        comment_1 = Comment.objects.create(pk=(self.tenant.id, 1934), user=user_1)
        comment_2 = Comment.objects.create(pk=(self.tenant.id, 8314), user=user_1)
        comment_3 = Comment.objects.create(pk=(self.tenant.id, 9214), user=user_1)
        comment_1.user = user_2
        comment_2.user = user_2
        comment_3.user = user_2

        with CaptureQueriesContext(connection) as context:
            result = Comment.objects.bulk_update(
                [comment_1, comment_2, comment_3], ["user_id"]
            )

        self.assertEqual(result, 3)
        self.assertEqual(len(context.captured_queries), 1)
        c = Comment._meta.db_table
        self.assertEqual(
            context.captured_queries[0]["sql"],
            f'UPDATE "{c}" '
            f'SET "user_id" = CASE '
            f'WHEN (("{c}"."tenant_id" = {self.tenant.id} AND "{c}"."id" = 1934)) '
            f"THEN 9314 "
            f'WHEN (("{c}"."tenant_id" = {self.tenant.id} AND "{c}"."id" = 8314)) '
            f"THEN 9314 "
            f'WHEN (("{c}"."tenant_id" = {self.tenant.id} AND "{c}"."id" = 9214)) '
            f"THEN 9314 ELSE NULL END "
            f'WHERE (("{c}"."tenant_id" = {self.tenant.id} AND "{c}"."id" = 1934) '
            f'OR ("{c}"."tenant_id" = {self.tenant.id} AND "{c}"."id" = 8314) '
            f'OR ("{c}"."tenant_id" = {self.tenant.id} AND "{c}"."id" = 9214))',
        )

    def test_update_or_create_user_by_pk(self):
        user, created = User.objects.update_or_create(pk=self.user.pk)

        self.assertFalse(created)
        self.assertEqual(1, User.objects.all().count())
        self.assertEqual(user.pk, self.user.pk)
        self.assertEqual(user.tenant_id, self.tenant.id)
        self.assertEqual(user.id, self.user.id)
