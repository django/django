from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from .models import Comment, Tenant, User


class CompositePKFilterTests(TestCase):
    """
    Test the .filter() method of composite_pk models.
    """

    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create()
        cls.user = User.objects.create(tenant=cls.tenant, id=1)
        cls.comment = Comment.objects.create(tenant=cls.tenant, id=1, user=cls.user)

    def test_filter_and_count_user_by_pk(self):
        test_cases = [
            {"pk": self.user.pk},
            {"pk": (self.tenant.id, self.user.id)},
        ]

        for lookup in test_cases:
            with self.subTest(lookup=lookup):
                with CaptureQueriesContext(connection) as context:
                    result = User.objects.filter(**lookup).count()

                self.assertEqual(result, 1)
                self.assertEqual(len(context.captured_queries), 1)
                if connection.vendor in ("sqlite", "postgresql"):
                    u = User._meta.db_table
                    self.assertEqual(
                        context.captured_queries[0]["sql"],
                        'SELECT COUNT(*) AS "__count" '
                        f'FROM "{u}" '
                        f'WHERE ("{u}"."tenant_id" = {self.tenant.id} '
                        f'AND "{u}"."id" = {self.user.id})',
                    )

    def test_filter_comments_by_user_and_order_by_pk_asc(self):
        user = User.objects.create(pk=(self.tenant.id, 2491))
        comment_1 = Comment.objects.create(pk=(self.tenant.id, 9471), user=user)
        comment_2 = Comment.objects.create(pk=(self.tenant.id, 5128), user=user)
        comment_3 = Comment.objects.create(pk=(self.tenant.id, 4823), user=user)

        with CaptureQueriesContext(connection) as context:
            result = list(Comment.objects.filter(user=user).order_by("pk"))

        self.assertEqual(result, [comment_3, comment_2, comment_1])
        self.assertEqual(len(context.captured_queries), 1)
        if connection.vendor in ("sqlite", "postgresql"):
            c = Comment._meta.db_table
            self.assertEqual(
                context.captured_queries[0]["sql"],
                f'SELECT "{c}"."tenant_id", "{c}"."id", "{c}"."user_id" '
                f'FROM "{c}" '
                f'WHERE ("{c}"."tenant_id" = {self.tenant.id} '
                f'AND "{c}"."user_id" = 2491) '
                f'ORDER BY "{c}"."tenant_id", "{c}"."id" ASC',
            )

    def test_filter_comments_by_user_and_order_by_pk_desc(self):
        user = User.objects.create(pk=(self.tenant.id, 8316))
        comment_1 = Comment.objects.create(pk=(self.tenant.id, 3571), user=user)
        comment_2 = Comment.objects.create(pk=(self.tenant.id, 7234), user=user)
        comment_3 = Comment.objects.create(pk=(self.tenant.id, 1035), user=user)

        with CaptureQueriesContext(connection) as context:
            result = list(Comment.objects.filter(user=user).order_by("-pk"))

        self.assertEqual(result, [comment_2, comment_1, comment_3])
        self.assertEqual(len(context.captured_queries), 1)
        if connection.vendor in ("sqlite", "postgresql"):
            c = Comment._meta.db_table
            self.assertEqual(
                context.captured_queries[0]["sql"],
                f'SELECT "{c}"."tenant_id", "{c}"."id", "{c}"."user_id" '
                f'FROM "{c}" '
                f'WHERE ("{c}"."tenant_id" = {self.tenant.id} '
                f'AND "{c}"."user_id" = 8316) '
                f'ORDER BY "{c}"."tenant_id", "{c}"."id" DESC',
            )
