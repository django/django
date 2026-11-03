from django.db.models import F
from django.test import TestCase

from .models import Comment, Tenant, User


class CompositePKOrderByTests(TestCase):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.tenant_1 = Tenant.objects.create()
        cls.tenant_2 = Tenant.objects.create()
        cls.tenant_3 = Tenant.objects.create()
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
        cls.comment_1 = Comment.objects.create(id=1, user=cls.user_1)
        cls.comment_2 = Comment.objects.create(id=2, user=cls.user_1)
        cls.comment_3 = Comment.objects.create(id=3, user=cls.user_2)
        cls.comment_4 = Comment.objects.create(id=4, user=cls.user_3)
        cls.comment_5 = Comment.objects.create(id=5, user=cls.user_1)

    def test_order_comments_by_pk_asc(self):
        self.assertSequenceEqual(
            Comment.objects.order_by("pk"),
            (
                self.comment_1,  # (1, 1)
                self.comment_2,  # (1, 2)
                self.comment_3,  # (1, 3)
                self.comment_5,  # (1, 5)
                self.comment_4,  # (2, 4)
            ),
        )

    def test_order_comments_by_pk_desc(self):
        self.assertSequenceEqual(
            Comment.objects.order_by("-pk"),
            (
                self.comment_4,  # (2, 4)
                self.comment_5,  # (1, 5)
                self.comment_3,  # (1, 3)
                self.comment_2,  # (1, 2)
                self.comment_1,  # (1, 1)
            ),
        )

    def test_order_comments_by_pk_expr(self):
        self.assertQuerySetEqual(
            Comment.objects.order_by("pk"),
            Comment.objects.order_by(F("pk")),
        )
        self.assertQuerySetEqual(
            Comment.objects.order_by("-pk"),
            Comment.objects.order_by(F("pk").desc()),
        )
        self.assertQuerySetEqual(
            Comment.objects.order_by("-pk"),
            Comment.objects.order_by(F("pk").desc(nulls_last=True)),
        )

    def test_alias_totally_ordered(self):
        self.assertIs(
            Comment.objects.alias(my_pk=F("pk")).order_by("my_pk").totally_ordered,
            True,
        )

    def test_order_combined_comments_by_pk(self):
        for combinator in ("union", "intersection", "difference"):
            with self.subTest(combinator=combinator):
                qs = getattr(
                    Comment.objects.filter(id__in=[1, 3, 4, 5]),
                    combinator,
                )(Comment.objects.filter(id__in=[3, 4, 5]))
                expected = {
                    "union": [
                        self.comment_1,
                        self.comment_3,
                        self.comment_5,
                        self.comment_4,
                    ],
                    "intersection": [self.comment_3, self.comment_5, self.comment_4],
                    "difference": [self.comment_1],
                }[combinator]
                self.assertSequenceEqual(qs.order_by("pk"), expected)
                self.assertSequenceEqual(qs.order_by("-pk"), expected[::-1])
                self.assertSequenceEqual(qs.order_by(F("pk")), expected)
                self.assertSequenceEqual(qs.order_by(F("pk").desc()), expected[::-1])

    def test_combined_comments_first_and_last(self):
        qs = Comment.objects.filter(user=self.user_3).union(
            Comment.objects.filter(user=self.user_1)
        )
        self.assertEqual(qs.first(), self.comment_1)
        self.assertEqual(qs.last(), self.comment_4)

    def test_order_combined_comments_values_by_pk(self):
        qs = Comment.objects.filter(user=self.user_3).union(
            Comment.objects.filter(user=self.user_1)
        )
        self.assertSequenceEqual(
            qs.values_list("pk", flat=True).order_by("pk"),
            [
                self.comment_1.pk,
                self.comment_2.pk,
                self.comment_5.pk,
                self.comment_4.pk,
            ],
        )
        self.assertSequenceEqual(
            qs.values_list("pk", "id").order_by("-pk"),
            [
                (self.comment_4.pk, 4),
                (self.comment_5.pk, 5),
                (self.comment_2.pk, 2),
                (self.comment_1.pk, 1),
            ],
        )

    def test_order_combined_comments_by_pk_and_field(self):
        qs = Comment.objects.filter(user=self.user_1).union(
            Comment.objects.filter(user=self.user_3)
        )
        self.assertSequenceEqual(
            qs.order_by("tenant", "-id"),
            [self.comment_5, self.comment_2, self.comment_1, self.comment_4],
        )
