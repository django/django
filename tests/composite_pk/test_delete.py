from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from .models import Comment, Tenant, User


class CompositePKDeleteTests(TestCase):
    """
    Test the .delete() method of composite_pk models.
    """

    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create()
        cls.user = User.objects.create(tenant=cls.tenant, id=1)
        cls.comment = Comment.objects.create(tenant=cls.tenant, id=1, user=cls.user)

    def test_delete_tenant_by_pk(self):
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
        if connection.vendor in ("sqlite", "postgresql"):
            t = Tenant._meta.db_table
            u = User._meta.db_table
            c = Comment._meta.db_table

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
                f'WHERE ("{c}"."tenant_id" = {self.tenant.id} '
                f'AND "{c}"."user_id" = {self.user.id})',
            )
            self.assertEqual(
                context.captured_queries[3]["sql"],
                f'DELETE FROM "{c}" WHERE "{c}"."tenant_id" IN ({self.tenant.id})',
            )
            self.assertEqual(
                context.captured_queries[4]["sql"],
                f'DELETE FROM "{u}" '
                f'WHERE ("{u}"."tenant_id" = {self.tenant.id} '
                f'AND "{u}"."id" = {self.user.id})',
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
        if connection.vendor in ("sqlite", "postgresql"):
            self.assertEqual(
                context.captured_queries[0]["sql"],
                f'SELECT "{u}"."tenant_id", "{u}"."id" '
                f'FROM "{u}" '
                f'WHERE "{u}"."id" = {self.user.id}',
            )
            self.assertEqual(
                context.captured_queries[1]["sql"],
                f'DELETE FROM "{c}" '
                f'WHERE ("{c}"."tenant_id" = {self.tenant.id} '
                f'AND "{c}"."user_id" = {self.user.id})',
            )
            self.assertEqual(
                context.captured_queries[2]["sql"],
                f'DELETE FROM "{u}" '
                f'WHERE ("{u}"."tenant_id" = {self.tenant.id} '
                f'AND "{u}"."id" = {self.user.id})',
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
        if connection.vendor in ("sqlite", "postgresql"):
            self.assertEqual(
                context.captured_queries[0]["sql"],
                f'SELECT "{u}"."tenant_id", "{u}"."id" '
                f'FROM "{u}" '
                f'WHERE ("{u}"."tenant_id" = {self.tenant.id} '
                f'AND "{u}"."id" = {self.user.id})',
            )
            self.assertEqual(
                context.captured_queries[1]["sql"],
                f'DELETE FROM "{c}" '
                f'WHERE ("{c}"."tenant_id" = {self.tenant.id} '
                f'AND "{c}"."user_id" = {self.user.id})',
            )
            self.assertEqual(
                context.captured_queries[2]["sql"],
                f'DELETE FROM "{u}" '
                f'WHERE ("{u}"."tenant_id" = {self.tenant.id} '
                f'AND "{u}"."id" = {self.user.id})',
            )

    def test_delete_comments_by_user(self):
        c = Comment._meta.db_table
        user = User.objects.create(pk=(self.tenant.id, 8259))
        comment_1 = Comment.objects.create(pk=(self.tenant.id, 1923), user=user)
        comment_2 = Comment.objects.create(pk=(self.tenant.id, 8123), user=user)
        comment_3 = Comment.objects.create(pk=(self.tenant.id, 8219), user=user)

        with CaptureQueriesContext(connection) as context:
            result = Comment.objects.filter(user=user).delete()

        self.assertEqual(result, (3, {"composite_pk.Comment": 3}))

        self.assertFalse(Comment.objects.filter(id=comment_1.id).exists())
        self.assertFalse(Comment.objects.filter(id=comment_2.id).exists())
        self.assertFalse(Comment.objects.filter(id=comment_3.id).exists())

        self.assertEqual(len(context.captured_queries), 1)
        if connection.vendor in ("sqlite", "postgresql"):
            self.assertEqual(
                context.captured_queries[0]["sql"],
                f'DELETE FROM "{c}" '
                f'WHERE ("{c}"."tenant_id" = {self.tenant.id} '
                f'AND "{c}"."user_id" = 8259)',
            )
