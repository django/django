from django.db import connection
from django.db.models.query import MAX_GET_RESULTS
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from .models import Comment, Tenant, User


class CompositePKGetTests(TestCase):
    """
    Test the .get(), .get_or_create() methods of composite_pk models.
    """

    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create()
        cls.user = User.objects.create(tenant=cls.tenant, id=1)
        cls.comment = Comment.objects.create(tenant=cls.tenant, id=1, user=cls.user)

    def test_get_tenant_by_pk(self):
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
                if connection.vendor in ("sqlite", "postgresql"):
                    t = Tenant._meta.db_table
                    self.assertEqual(
                        context.captured_queries[0]["sql"],
                        f'SELECT "{t}"."id" '
                        f'FROM "{t}" '
                        f'WHERE "{t}"."id" = {self.tenant.id} '
                        f"LIMIT {MAX_GET_RESULTS}",
                    )

    def test_get_user_by_pk(self):
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
                if connection.vendor in ("sqlite", "postgresql"):
                    u = User._meta.db_table
                    self.assertEqual(
                        context.captured_queries[0]["sql"],
                        f'SELECT "{u}"."tenant_id", "{u}"."id" '
                        f'FROM "{u}" '
                        f'WHERE ("{u}"."tenant_id" = {self.tenant.id} '
                        f'AND "{u}"."id" = {self.user.id}) '
                        f"LIMIT {MAX_GET_RESULTS}",
                    )

    def test_get_user_by_field(self):
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
                if connection.vendor in ("sqlite", "postgresql"):
                    u = User._meta.db_table
                    self.assertEqual(
                        context.captured_queries[0]["sql"],
                        f'SELECT "{u}"."tenant_id", "{u}"."id" '
                        f'FROM "{u}" '
                        f'WHERE "{u}"."{column}" = {value} '
                        f"LIMIT {MAX_GET_RESULTS}",
                    )

    def test_get_comment_by_pk(self):
        with CaptureQueriesContext(connection) as context:
            obj = Comment.objects.get(pk=(self.tenant.id, self.comment.id))

        self.assertEqual(obj, self.comment)
        self.assertEqual(len(context.captured_queries), 1)
        if connection.vendor in ("sqlite", "postgresql"):
            c = Comment._meta.db_table
            self.assertEqual(
                context.captured_queries[0]["sql"],
                f'SELECT "{c}"."tenant_id", "{c}"."id", "{c}"."user_id" '
                f'FROM "{c}" '
                f'WHERE ("{c}"."tenant_id" = {self.tenant.id} '
                f'AND "{c}"."id" = {self.comment.id}) '
                f"LIMIT {MAX_GET_RESULTS}",
            )

    def test_get_comment_by_field(self):
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
                if connection.vendor in ("sqlite", "postgresql"):
                    c = Comment._meta.db_table
                    self.assertEqual(
                        context.captured_queries[0]["sql"],
                        f'SELECT "{c}"."tenant_id", "{c}"."id", "{c}"."user_id" '
                        f'FROM "{c}" '
                        f'WHERE "{c}"."{column}" = {value} '
                        f"LIMIT {MAX_GET_RESULTS}",
                    )

    def test_get_comment_by_user(self):
        with CaptureQueriesContext(connection) as context:
            obj = Comment.objects.get(user=self.user)

        self.assertEqual(obj, self.comment)
        self.assertEqual(len(context.captured_queries), 1)
        if connection.vendor in ("sqlite", "postgresql"):
            c = Comment._meta.db_table
            self.assertEqual(
                context.captured_queries[0]["sql"],
                f'SELECT "{c}"."tenant_id", "{c}"."id", "{c}"."user_id" '
                f'FROM "{c}" '
                f'WHERE ("{c}"."tenant_id" = {self.tenant.id} '
                f'AND "{c}"."user_id" = {self.user.id}) '
                f"LIMIT {MAX_GET_RESULTS}",
            )

    def test_get_comment_by_user_pk(self):
        with CaptureQueriesContext(connection) as context:
            obj = Comment.objects.get(user__pk=self.user.pk)

        self.assertEqual(obj, self.comment)
        self.assertEqual(len(context.captured_queries), 1)
        if connection.vendor in ("sqlite", "postgresql"):
            c = Comment._meta.db_table
            u = User._meta.db_table
            self.assertEqual(
                context.captured_queries[0]["sql"],
                f'SELECT "{c}"."tenant_id", "{c}"."id", "{c}"."user_id" '
                f'FROM "{c}" '
                f'INNER JOIN "{u}" ON ("{c}"."tenant_id" = "{u}"."tenant_id" '
                f'AND "{c}"."user_id" = "{u}"."id") '
                f'WHERE ("{u}"."tenant_id" = {self.tenant.id} '
                f'AND "{u}"."id" = {self.user.id}) '
                f"LIMIT {MAX_GET_RESULTS}",
            )

    def test_get_comment_by_pk_only_pk(self):
        with CaptureQueriesContext(connection) as context:
            obj = Comment.objects.only("pk").get(pk=self.comment.pk)

        self.assertEqual(obj, self.comment)
        self.assertEqual(len(context.captured_queries), 1)
        if connection.vendor in ("sqlite", "postgresql"):
            c = Comment._meta.db_table
            self.assertEqual(
                context.captured_queries[0]["sql"],
                f'SELECT "{c}"."tenant_id", "{c}"."id" '
                f'FROM "{c}" '
                f'WHERE ("{c}"."tenant_id" = {self.tenant.id} '
                f'AND "{c}"."id" = {self.user.id}) '
                f"LIMIT {MAX_GET_RESULTS}",
            )

    def test_get_or_create_user_by_pk(self):
        user, created = User.objects.get_or_create(pk=self.user.pk)

        self.assertFalse(created)
        self.assertEqual(1, User.objects.all().count())
        self.assertEqual(user, self.user)

    def test_lookup_errors(self):
        with self.assertRaisesMessage(
            ValueError, "The right-hand side of the 'exact' lookup must be an iterable"
        ):
            Comment.objects.get(pk=1)
        with self.assertRaisesMessage(
            ValueError,
            "The left-hand side and right-hand side of the 'exact' "
            "lookup must have the same number of elements",
        ):
            Comment.objects.get(pk=(1, 2, 3))
        with self.assertRaisesMessage(
            ValueError, "The right-hand side of the 'in' lookup must be an iterable"
        ):
            Comment.objects.get(pk__in=1)
        with self.assertRaisesMessage(
            ValueError,
            "The right-hand side of the 'in' lookup must be an iterable "
            "of iterables",
        ):
            Comment.objects.get(pk__in=(1, 2, 3))
        with self.assertRaisesMessage(
            ValueError,
            "The left-hand side and right-hand side of the 'in' lookup must "
            "have the same number of elements",
        ):
            Comment.objects.get(pk__in=((1, 2, 3),))
