from collections import namedtuple
from uuid import UUID

from django.test import TestCase

from .models import Post, Tenant, User


class CompositePKValuesTests(TestCase):
    USER_1_EMAIL = "user0001@example.com"
    USER_2_EMAIL = "user0002@example.com"
    USER_3_EMAIL = "user0003@example.com"
    POST_1_ID = "77777777-7777-7777-7777-777777777777"
    POST_2_ID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
    POST_3_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.tenant_1 = Tenant.objects.create()
        cls.tenant_2 = Tenant.objects.create()
        cls.user_1 = User.objects.create(
            tenant=cls.tenant_1, id=1, email=cls.USER_1_EMAIL
        )
        cls.user_2 = User.objects.create(
            tenant=cls.tenant_1, id=2, email=cls.USER_2_EMAIL
        )
        cls.user_3 = User.objects.create(
            tenant=cls.tenant_2, id=3, email=cls.USER_3_EMAIL
        )
        cls.post_1 = Post.objects.create(tenant=cls.tenant_1, id=cls.POST_1_ID)
        cls.post_2 = Post.objects.create(tenant=cls.tenant_1, id=cls.POST_2_ID)
        cls.post_3 = Post.objects.create(tenant=cls.tenant_2, id=cls.POST_3_ID)

    def test_values_list(self):
        with self.subTest('User.objects.values_list("pk")'):
            self.assertSequenceEqual(
                User.objects.values_list("pk").order_by("pk"),
                (
                    (self.user_1.pk,),
                    (self.user_2.pk,),
                    (self.user_3.pk,),
                ),
            )
        with self.subTest('User.objects.values_list("pk", "email")'):
            self.assertSequenceEqual(
                User.objects.values_list("pk", "email").order_by("pk"),
                (
                    (self.user_1.pk, self.USER_1_EMAIL),
                    (self.user_2.pk, self.USER_2_EMAIL),
                    (self.user_3.pk, self.USER_3_EMAIL),
                ),
            )
        with self.subTest('User.objects.values_list("pk", "id")'):
            self.assertSequenceEqual(
                User.objects.values_list("pk", "id").order_by("pk"),
                (
                    (self.user_1.pk, self.user_1.id),
                    (self.user_2.pk, self.user_2.id),
                    (self.user_3.pk, self.user_3.id),
                ),
            )
        with self.subTest('User.objects.values_list("pk", "tenant_id", "id")'):
            self.assertSequenceEqual(
                User.objects.values_list("pk", "tenant_id", "id").order_by("pk"),
                (
                    (self.user_1.pk, self.user_1.tenant_id, self.user_1.id),
                    (self.user_2.pk, self.user_2.tenant_id, self.user_2.id),
                    (self.user_3.pk, self.user_3.tenant_id, self.user_3.id),
                ),
            )
        with self.subTest('User.objects.values_list("pk", flat=True)'):
            self.assertSequenceEqual(
                User.objects.values_list("pk", flat=True).order_by("pk"),
                (
                    self.user_1.pk,
                    self.user_2.pk,
                    self.user_3.pk,
                ),
            )
        with self.subTest('Post.objects.values_list("pk", flat=True)'):
            self.assertSequenceEqual(
                Post.objects.values_list("pk", flat=True).order_by("pk"),
                (
                    (self.tenant_1.id, UUID(self.POST_1_ID)),
                    (self.tenant_1.id, UUID(self.POST_2_ID)),
                    (self.tenant_2.id, UUID(self.POST_3_ID)),
                ),
            )
        with self.subTest('Post.objects.values_list("pk")'):
            self.assertSequenceEqual(
                Post.objects.values_list("pk").order_by("pk"),
                (
                    ((self.tenant_1.id, UUID(self.POST_1_ID)),),
                    ((self.tenant_1.id, UUID(self.POST_2_ID)),),
                    ((self.tenant_2.id, UUID(self.POST_3_ID)),),
                ),
            )
        with self.subTest('Post.objects.values_list("pk", "id")'):
            self.assertSequenceEqual(
                Post.objects.values_list("pk", "id").order_by("pk"),
                (
                    ((self.tenant_1.id, UUID(self.POST_1_ID)), UUID(self.POST_1_ID)),
                    ((self.tenant_1.id, UUID(self.POST_2_ID)), UUID(self.POST_2_ID)),
                    ((self.tenant_2.id, UUID(self.POST_3_ID)), UUID(self.POST_3_ID)),
                ),
            )
        with self.subTest('Post.objects.values_list("id", "pk")'):
            self.assertSequenceEqual(
                Post.objects.values_list("id", "pk").order_by("pk"),
                (
                    (UUID(self.POST_1_ID), (self.tenant_1.id, UUID(self.POST_1_ID))),
                    (UUID(self.POST_2_ID), (self.tenant_1.id, UUID(self.POST_2_ID))),
                    (UUID(self.POST_3_ID), (self.tenant_2.id, UUID(self.POST_3_ID))),
                ),
            )
        with self.subTest('User.objects.values_list("pk", named=True)'):
            Row = namedtuple("Row", ["pk"])
            self.assertSequenceEqual(
                User.objects.values_list("pk", named=True).order_by("pk"),
                (
                    Row(pk=self.user_1.pk),
                    Row(pk=self.user_2.pk),
                    Row(pk=self.user_3.pk),
                ),
            )
        with self.subTest('User.objects.values_list("pk", "pk")'):
            self.assertSequenceEqual(
                User.objects.values_list("pk", "pk").order_by("pk"),
                (
                    (self.user_1.pk, self.user_1.pk),
                    (self.user_2.pk, self.user_2.pk),
                    (self.user_3.pk, self.user_3.pk),
                ),
            )
        with self.subTest('User.objects.values_list("pk", "id", "pk", "id")'):
            self.assertSequenceEqual(
                User.objects.values_list("pk", "id", "pk", "id").order_by("pk"),
                (
                    (self.user_1.pk, self.user_1.id, self.user_1.pk, self.user_1.id),
                    (self.user_2.pk, self.user_2.id, self.user_2.pk, self.user_2.id),
                    (self.user_3.pk, self.user_3.id, self.user_3.pk, self.user_3.id),
                ),
            )

    def test_values(self):
        with self.subTest('User.objects.values("pk")'):
            self.assertSequenceEqual(
                User.objects.values("pk").order_by("pk"),
                (
                    {"pk": self.user_1.pk},
                    {"pk": self.user_2.pk},
                    {"pk": self.user_3.pk},
                ),
            )
        with self.subTest('User.objects.values("pk", "email")'):
            self.assertSequenceEqual(
                User.objects.values("pk", "email").order_by("pk"),
                (
                    {"pk": self.user_1.pk, "email": self.USER_1_EMAIL},
                    {"pk": self.user_2.pk, "email": self.USER_2_EMAIL},
                    {"pk": self.user_3.pk, "email": self.USER_3_EMAIL},
                ),
            )
        with self.subTest('User.objects.values("pk", "id")'):
            self.assertSequenceEqual(
                User.objects.values("pk", "id").order_by("pk"),
                (
                    {"pk": self.user_1.pk, "id": self.user_1.id},
                    {"pk": self.user_2.pk, "id": self.user_2.id},
                    {"pk": self.user_3.pk, "id": self.user_3.id},
                ),
            )
        with self.subTest('User.objects.values("pk", "tenant_id", "id")'):
            self.assertSequenceEqual(
                User.objects.values("pk", "tenant_id", "id").order_by("pk"),
                (
                    {
                        "pk": self.user_1.pk,
                        "tenant_id": self.user_1.tenant_id,
                        "id": self.user_1.id,
                    },
                    {
                        "pk": self.user_2.pk,
                        "tenant_id": self.user_2.tenant_id,
                        "id": self.user_2.id,
                    },
                    {
                        "pk": self.user_3.pk,
                        "tenant_id": self.user_3.tenant_id,
                        "id": self.user_3.id,
                    },
                ),
            )
        with self.subTest('User.objects.values("pk", "pk")'):
            self.assertSequenceEqual(
                User.objects.values("pk", "pk").order_by("pk"),
                (
                    {"pk": self.user_1.pk},
                    {"pk": self.user_2.pk},
                    {"pk": self.user_3.pk},
                ),
            )
        with self.subTest('User.objects.values("pk", "id", "pk", "id")'):
            self.assertSequenceEqual(
                User.objects.values("pk", "id", "pk", "id").order_by("pk"),
                (
                    {"pk": self.user_1.pk, "id": self.user_1.id},
                    {"pk": self.user_2.pk, "id": self.user_2.id},
                    {"pk": self.user_3.pk, "id": self.user_3.id},
                ),
            )
