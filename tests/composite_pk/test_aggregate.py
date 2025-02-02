from django.db.models import Count, Max, Q
from django.test import TestCase

from .models import Comment, Tenant, User


class CompositePKAggregateTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tenant_1 = Tenant.objects.create()
        cls.tenant_2 = Tenant.objects.create()
        cls.user_1 = User.objects.create(
            tenant=cls.tenant_1,
            id=1,
            email="user0001@example.com",
        )
        cls.user_2 = User.objects.create(
            tenant=cls.tenant_1,
            id=2,
            email="user0002@example.com",
        )
        cls.user_3 = User.objects.create(
            tenant=cls.tenant_2,
            id=3,
            email="user0003@example.com",
        )
        cls.comment_1 = Comment.objects.create(id=1, user=cls.user_2, text="foo")
        cls.comment_2 = Comment.objects.create(id=2, user=cls.user_1, text="bar")
        cls.comment_3 = Comment.objects.create(id=3, user=cls.user_1, text="foobar")
        cls.comment_4 = Comment.objects.create(id=4, user=cls.user_3, text="foobarbaz")
        cls.comment_5 = Comment.objects.create(id=5, user=cls.user_3, text="barbaz")
        cls.comment_6 = Comment.objects.create(id=6, user=cls.user_3, text="baz")

    def test_users_annotated_with_comments_id_count(self):
        user_1, user_2, user_3 = User.objects.annotate(Count("comments__id")).order_by(
            "pk"
        )

        self.assertEqual(user_1, self.user_1)
        self.assertEqual(user_1.comments__id__count, 2)
        self.assertEqual(user_2, self.user_2)
        self.assertEqual(user_2.comments__id__count, 1)
        self.assertEqual(user_3, self.user_3)
        self.assertEqual(user_3.comments__id__count, 3)

    def test_users_annotated_with_aliased_comments_id_count(self):
        user_1, user_2, user_3 = User.objects.annotate(
            comments_count=Count("comments__id")
        ).order_by("pk")

        self.assertEqual(user_1, self.user_1)
        self.assertEqual(user_1.comments_count, 2)
        self.assertEqual(user_2, self.user_2)
        self.assertEqual(user_2.comments_count, 1)
        self.assertEqual(user_3, self.user_3)
        self.assertEqual(user_3.comments_count, 3)

    def test_users_annotated_with_comments_count(self):
        user_1, user_2, user_3 = User.objects.annotate(Count("comments")).order_by("pk")

        self.assertEqual(user_1, self.user_1)
        self.assertEqual(user_1.comments__count, 2)
        self.assertEqual(user_2, self.user_2)
        self.assertEqual(user_2.comments__count, 1)
        self.assertEqual(user_3, self.user_3)
        self.assertEqual(user_3.comments__count, 3)

    def test_users_annotated_with_comments_count_filter(self):
        user_1, user_2, user_3 = User.objects.annotate(
            comments__count=Count(
                "comments", filter=Q(pk__in=[self.user_1.pk, self.user_2.pk])
            )
        ).order_by("pk")

        self.assertEqual(user_1, self.user_1)
        self.assertEqual(user_1.comments__count, 2)
        self.assertEqual(user_2, self.user_2)
        self.assertEqual(user_2.comments__count, 1)
        self.assertEqual(user_3, self.user_3)
        self.assertEqual(user_3.comments__count, 0)

    def test_count_distinct_not_supported(self):
        with self.assertRaisesMessage(
            ValueError, "COUNT(DISTINCT) doesn't support composite primary keys"
        ):
            self.assertIsNone(
                User.objects.annotate(comments__count=Count("comments", distinct=True))
            )

    def test_user_values_annotated_with_comments_id_count(self):
        self.assertSequenceEqual(
            User.objects.values("pk").annotate(Count("comments__id")).order_by("pk"),
            (
                {"pk": self.user_1.pk, "comments__id__count": 2},
                {"pk": self.user_2.pk, "comments__id__count": 1},
                {"pk": self.user_3.pk, "comments__id__count": 3},
            ),
        )

    def test_user_values_annotated_with_filtered_comments_id_count(self):
        self.assertSequenceEqual(
            User.objects.values("pk")
            .annotate(
                comments_count=Count(
                    "comments__id",
                    filter=Q(comments__text__icontains="foo"),
                )
            )
            .order_by("pk"),
            (
                {"pk": self.user_1.pk, "comments_count": 1},
                {"pk": self.user_2.pk, "comments_count": 1},
                {"pk": self.user_3.pk, "comments_count": 1},
            ),
        )

    def test_filter_and_count_users_by_comments_fields(self):
        users = User.objects.filter(comments__id__gt=2).order_by("pk")
        self.assertEqual(users.count(), 4)
        self.assertSequenceEqual(
            users, (self.user_1, self.user_3, self.user_3, self.user_3)
        )

        users = User.objects.filter(comments__text__icontains="foo").order_by("pk")
        self.assertEqual(users.count(), 3)
        self.assertSequenceEqual(users, (self.user_1, self.user_2, self.user_3))

        users = User.objects.filter(comments__text__icontains="baz").order_by("pk")
        self.assertEqual(users.count(), 3)
        self.assertSequenceEqual(users, (self.user_3, self.user_3, self.user_3))

    def test_order_by_comments_id_count(self):
        self.assertSequenceEqual(
            User.objects.annotate(comments_count=Count("comments__id")).order_by(
                "-comments_count"
            ),
            (self.user_3, self.user_1, self.user_2),
        )

    def test_max_pk(self):
        msg = "Max expression does not support composite primary keys."
        with self.assertRaisesMessage(ValueError, msg):
            Comment.objects.aggregate(Max("pk"))
