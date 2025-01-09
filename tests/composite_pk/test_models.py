from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.test import TestCase

from .models import Comment, Tenant, Token, User


class CompositePKModelsTests(TestCase):
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
        cls.comment_1 = Comment.objects.create(id=1, user=cls.user_1)
        cls.comment_2 = Comment.objects.create(id=2, user=cls.user_1)
        cls.comment_3 = Comment.objects.create(id=3, user=cls.user_2)
        cls.comment_4 = Comment.objects.create(id=4, user=cls.user_3)

    def test_fields(self):
        # tenant_1
        self.assertSequenceEqual(
            self.tenant_1.user_set.order_by("pk"),
            [self.user_1, self.user_2],
        )
        self.assertSequenceEqual(
            self.tenant_1.comments.order_by("pk"),
            [self.comment_1, self.comment_2, self.comment_3],
        )

        # tenant_2
        self.assertSequenceEqual(self.tenant_2.user_set.order_by("pk"), [self.user_3])
        self.assertSequenceEqual(
            self.tenant_2.comments.order_by("pk"), [self.comment_4]
        )

        # user_1
        self.assertEqual(self.user_1.id, 1)
        self.assertEqual(self.user_1.tenant_id, self.tenant_1.id)
        self.assertEqual(self.user_1.tenant, self.tenant_1)
        self.assertEqual(self.user_1.pk, (self.tenant_1.id, self.user_1.id))
        self.assertSequenceEqual(
            self.user_1.comments.order_by("pk"), [self.comment_1, self.comment_2]
        )

        # user_2
        self.assertEqual(self.user_2.id, 2)
        self.assertEqual(self.user_2.tenant_id, self.tenant_1.id)
        self.assertEqual(self.user_2.tenant, self.tenant_1)
        self.assertEqual(self.user_2.pk, (self.tenant_1.id, self.user_2.id))
        self.assertSequenceEqual(self.user_2.comments.order_by("pk"), [self.comment_3])

        # comment_1
        self.assertEqual(self.comment_1.id, 1)
        self.assertEqual(self.comment_1.user_id, self.user_1.id)
        self.assertEqual(self.comment_1.user, self.user_1)
        self.assertEqual(self.comment_1.tenant_id, self.tenant_1.id)
        self.assertEqual(self.comment_1.tenant, self.tenant_1)
        self.assertEqual(self.comment_1.pk, (self.tenant_1.id, self.user_1.id))

    def test_full_clean_success(self):
        test_cases = (
            # 1, 1234, {}
            ({"tenant": self.tenant_1, "id": 1234}, {}),
            ({"tenant_id": self.tenant_1.id, "id": 1234}, {}),
            ({"pk": (self.tenant_1.id, 1234)}, {}),
            # 1, 1, {"id"}
            ({"tenant": self.tenant_1, "id": 1}, {"id"}),
            ({"tenant_id": self.tenant_1.id, "id": 1}, {"id"}),
            ({"pk": (self.tenant_1.id, 1)}, {"id"}),
            # 1, 1, {"tenant", "id"}
            ({"tenant": self.tenant_1, "id": 1}, {"tenant", "id"}),
            ({"tenant_id": self.tenant_1.id, "id": 1}, {"tenant", "id"}),
            ({"pk": (self.tenant_1.id, 1)}, {"tenant", "id"}),
        )

        for kwargs, exclude in test_cases:
            with self.subTest(kwargs):
                kwargs["email"] = "user0004@example.com"
                User(**kwargs).full_clean(exclude=exclude)

    def test_full_clean_failure(self):
        e_tenant_and_id = "User with this Tenant and Id already exists."
        e_id = "User with this Id already exists."
        test_cases = (
            # 1, 1, {}
            ({"tenant": self.tenant_1, "id": 1}, {}, (e_tenant_and_id, e_id)),
            ({"tenant_id": self.tenant_1.id, "id": 1}, {}, (e_tenant_and_id, e_id)),
            ({"pk": (self.tenant_1.id, 1)}, {}, (e_tenant_and_id, e_id)),
            # 2, 1, {}
            ({"tenant": self.tenant_2, "id": 1}, {}, (e_id,)),
            ({"tenant_id": self.tenant_2.id, "id": 1}, {}, (e_id,)),
            ({"pk": (self.tenant_2.id, 1)}, {}, (e_id,)),
            # 1, 1, {"tenant"}
            ({"tenant": self.tenant_1, "id": 1}, {"tenant"}, (e_id,)),
            ({"tenant_id": self.tenant_1.id, "id": 1}, {"tenant"}, (e_id,)),
            ({"pk": (self.tenant_1.id, 1)}, {"tenant"}, (e_id,)),
        )

        for kwargs, exclude, messages in test_cases:
            with self.subTest(kwargs):
                with self.assertRaises(ValidationError) as ctx:
                    kwargs["email"] = "user0004@example.com"
                    User(**kwargs).full_clean(exclude=exclude)

                self.assertSequenceEqual(ctx.exception.messages, messages)

    def test_full_clean_update(self):
        with self.assertNumQueries(1):
            self.comment_1.full_clean()

    def test_field_conflicts(self):
        test_cases = (
            ({"pk": (1, 1), "id": 2}, (1, 1)),
            ({"id": 2, "pk": (1, 1)}, (1, 1)),
            ({"pk": (1, 1), "tenant_id": 2}, (1, 1)),
            ({"tenant_id": 2, "pk": (1, 1)}, (1, 1)),
            ({"pk": (2, 2), "tenant_id": 3, "id": 4}, (2, 2)),
            ({"tenant_id": 3, "id": 4, "pk": (2, 2)}, (2, 2)),
        )

        for kwargs, pk in test_cases:
            with self.subTest(kwargs=kwargs):
                user = User(**kwargs)
                self.assertEqual(user.pk, pk)

    def test_validate_unique(self):
        user = User.objects.get(pk=self.user_1.pk)
        user.id = None

        with self.assertRaises(ValidationError) as ctx:
            user.validate_unique()

        self.assertSequenceEqual(
            ctx.exception.messages, ("User with this Email already exists.",)
        )

    def test_permissions(self):
        token = ContentType.objects.get_for_model(Token)
        user = ContentType.objects.get_for_model(User)
        comment = ContentType.objects.get_for_model(Comment)
        self.assertEqual(4, token.permission_set.count())
        self.assertEqual(4, user.permission_set.count())
        self.assertEqual(4, comment.permission_set.count())
