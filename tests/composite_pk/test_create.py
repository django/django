from django.db import IntegrityError
from django.test import TestCase, skipUnlessDBFeature

from .models import Post, Tenant, User


class CompositePKCreateTests(TestCase):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create(id=1)
        cls.user = User.objects.create(
            tenant=cls.tenant,
            id=1,
            email="user0001@example.com",
        )

    def test_create_user(self):
        test_cases = (
            {"tenant": self.tenant, "id": 2412, "email": "user2412@example.com"},
            {"tenant_id": self.tenant.id, "id": 5316, "email": "user5316@example.com"},
            {"pk": (self.tenant.id, 7424), "email": "user7424@example.com"},
        )

        for fields in test_cases:
            with self.subTest(fields=fields):
                count = User.objects.count()
                user = User(**fields)
                obj = User.objects.create(**fields)
                self.assertEqual(obj.tenant_id, self.tenant.id)
                self.assertEqual(obj.id, user.id)
                self.assertEqual(obj.pk, (self.tenant.id, user.id))
                self.assertEqual(obj.email, user.email)
                self.assertEqual(count + 1, User.objects.count())

    def test_save_user(self):
        test_cases = (
            {"tenant": self.tenant, "id": 9241, "email": "user9241@example.com"},
            {"tenant_id": self.tenant.id, "id": 5132, "email": "user5132@example.com"},
            {"pk": (self.tenant.id, 3014), "email": "user3014@example.com"},
        )

        for fields in test_cases:
            with self.subTest(fields=fields):
                count = User.objects.count()
                user = User(**fields)
                self.assertIsNotNone(user.id)
                self.assertIsNotNone(user.email)
                user.save()
                self.assertEqual(user.tenant_id, self.tenant.id)
                self.assertEqual(user.tenant, self.tenant)
                self.assertIsNotNone(user.id)
                self.assertEqual(user.pk, (self.tenant.id, user.id))
                self.assertEqual(user.email, fields["email"])
                self.assertEqual(user.email, f"user{user.id}@example.com")
                self.assertEqual(count + 1, User.objects.count())

    def test_bulk_create_users(self):
        objs = [
            User(tenant=self.tenant, id=8291, email="user8291@example.com"),
            User(tenant_id=self.tenant.id, id=4021, email="user4021@example.com"),
            User(pk=(self.tenant.id, 8214), email="user8214@example.com"),
        ]

        obj_1, obj_2, obj_3 = User.objects.bulk_create(objs)

        self.assertEqual(obj_1.tenant_id, self.tenant.id)
        self.assertEqual(obj_1.id, 8291)
        self.assertEqual(obj_1.pk, (obj_1.tenant_id, obj_1.id))
        self.assertEqual(obj_1.email, "user8291@example.com")
        self.assertEqual(obj_2.tenant_id, self.tenant.id)
        self.assertEqual(obj_2.id, 4021)
        self.assertEqual(obj_2.pk, (obj_2.tenant_id, obj_2.id))
        self.assertEqual(obj_2.email, "user4021@example.com")
        self.assertEqual(obj_3.tenant_id, self.tenant.id)
        self.assertEqual(obj_3.id, 8214)
        self.assertEqual(obj_3.pk, (obj_3.tenant_id, obj_3.id))
        self.assertEqual(obj_3.email, "user8214@example.com")

    @skipUnlessDBFeature(
        "supports_update_conflicts",
        "supports_update_conflicts_with_target",
    )
    def test_bulk_create_user_with_pk_field_in_update_fields(self):
        objs = [User(tenant=self.tenant, id=8291, email="user8291@example.com")]
        msg = "bulk_create() cannot be used with primary keys in update_fields."
        with self.assertRaisesMessage(ValueError, msg):
            User.objects.bulk_create(
                objs,
                update_conflicts=True,
                update_fields=["tenant_id"],
                unique_fields=["id", "tenant_id"],
            )

    def test_get_or_create_user(self):
        test_cases = (
            {
                "pk": (self.tenant.id, 8314),
                "defaults": {"email": "user8314@example.com"},
            },
            {
                "tenant": self.tenant,
                "id": 3142,
                "defaults": {"email": "user3142@example.com"},
            },
            {
                "tenant_id": self.tenant.id,
                "id": 4218,
                "defaults": {"email": "user4218@example.com"},
            },
        )

        for fields in test_cases:
            with self.subTest(fields=fields):
                count = User.objects.count()
                user, created = User.objects.get_or_create(**fields)
                self.assertIs(created, True)
                self.assertIsNotNone(user.id)
                self.assertEqual(user.pk, (self.tenant.id, user.id))
                self.assertEqual(user.tenant_id, self.tenant.id)
                self.assertEqual(user.email, fields["defaults"]["email"])
                self.assertEqual(user.email, f"user{user.id}@example.com")
                self.assertEqual(count + 1, User.objects.count())

    def test_update_or_create_user(self):
        test_cases = (
            {
                "pk": (self.tenant.id, 2931),
                "defaults": {"email": "user2931@example.com"},
            },
            {
                "tenant": self.tenant,
                "id": 6428,
                "defaults": {"email": "user6428@example.com"},
            },
            {
                "tenant_id": self.tenant.id,
                "id": 5278,
                "defaults": {"email": "user5278@example.com"},
            },
        )

        for fields in test_cases:
            with self.subTest(fields=fields):
                count = User.objects.count()
                user, created = User.objects.update_or_create(**fields)
                self.assertIs(created, True)
                self.assertIsNotNone(user.id)
                self.assertEqual(user.pk, (self.tenant.id, user.id))
                self.assertEqual(user.tenant_id, self.tenant.id)
                self.assertEqual(user.email, fields["defaults"]["email"])
                self.assertEqual(user.email, f"user{user.id}@example.com")
                self.assertEqual(count + 1, User.objects.count())

    def test_save_default_pk_not_set(self):
        with self.assertNumQueries(1):
            Post().save()

    def test_save_default_pk_set(self):
        post = Post.objects.create()
        with self.assertRaises(IntegrityError):
            Post(tenant_id=post.tenant_id, id=post.id).save()
