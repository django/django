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
