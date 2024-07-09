from uuid import UUID

from django.db.models import Count
from django.test import TestCase

from .models import Comment, Post, Tenant, User


class CompositePKGetTests(TestCase):
    """
    Test the .get(), .get_or_create() methods of composite_pk models.
    """

    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.tenant_1 = Tenant.objects.create()
        cls.tenant_2 = Tenant.objects.create()
        cls.user_1 = User.objects.create(
            tenant=cls.tenant_1, id=1, email="user0001@example.com"
        )
        cls.user_2 = User.objects.create(
            tenant=cls.tenant_1, id=2, email="user0002@example.com"
        )
        cls.user_3 = User.objects.create(
            tenant=cls.tenant_2, id=3, email="user0003@example.com"
        )
        cls.comment_1 = Comment.objects.create(id=1, user=cls.user_1)
        cls.post_1 = Post.objects.create(
            tenant=cls.tenant_1, id="748ae4e5-eed7-442d-a93d-43867eadee2b"
        )
        cls.post_2 = Post.objects.create(
            tenant=cls.tenant_1, id="b36cebfc-a9a5-48fd-baeb-2ad0fe63b260"
        )
        cls.post_3 = Post.objects.create(
            tenant=cls.tenant_2, id="aa3d4b88-6ae1-45be-890e-32dd7e71b790"
        )

    def test_get_user(self):
        test_cases = (
            {"pk": self.user_1.pk},
            {"pk": (self.tenant_1.id, self.user_1.id)},
            {"id": self.user_1.id},
        )

        for lookup in test_cases:
            with self.subTest(lookup=lookup):
                self.assertEqual(User.objects.get(**lookup), self.user_1)

    def test_get_comment(self):
        test_cases = (
            {"pk": self.comment_1.pk},
            {"pk": (self.tenant_1.id, self.comment_1.id)},
            {"id": self.comment_1.id},
            {"user": self.user_1},
            {"user_id": self.user_1.id},
            {"user__id": self.user_1.id},
            {"user__pk": self.user_1.pk},
            {"tenant": self.tenant_1},
            {"tenant_id": self.tenant_1.id},
            {"tenant__id": self.tenant_1.id},
            {"tenant__pk": self.tenant_1.pk},
        )

        for lookup in test_cases:
            with self.subTest(lookup=lookup):
                self.assertEqual(Comment.objects.get(**lookup), self.comment_1)

    def test_get_or_create_user(self):
        test_cases = (
            {
                "pk": self.user_1.pk,
                "defaults": {"email": "user9201@example.com"},
            },
            {
                "pk": (self.tenant_1.id, self.user_1.id),
                "defaults": {"email": "user9201@example.com"},
            },
            {
                "tenant": self.tenant_1,
                "id": self.user_1.id,
                "defaults": {"email": "user3512@example.com"},
            },
            {
                "tenant_id": self.tenant_1.id,
                "id": self.user_1.id,
                "defaults": {"email": "user8239@example.com"},
            },
        )

        for fields in test_cases:
            with self.subTest(fields=fields):
                count = User.objects.count()
                user, created = User.objects.get_or_create(**fields)
                self.assertFalse(created)
                self.assertEqual(user.id, self.user_1.id)
                self.assertEqual(user.pk, (self.tenant_1.id, self.user_1.id))
                self.assertEqual(user.tenant_id, self.tenant_1.id)
                self.assertEqual(user.email, self.user_1.email)
                self.assertEqual(count, User.objects.count())

    def test_lookup_errors(self):
        m_tuple = "'%s' lookup of 'pk' field must be a tuple or a list"
        m_2_elements = "'%s' lookup of 'pk' field must have 2 elements"
        m_tuple_collection = (
            "'in' lookup of 'pk' field must be a collection of tuples or lists"
        )
        m_2_elements_each = "'in' lookup of 'pk' field must have 2 elements each"
        test_cases = (
            ({"pk": 1}, m_tuple % "exact"),
            ({"pk": (1, 2, 3)}, m_2_elements % "exact"),
            ({"pk__exact": 1}, m_tuple % "exact"),
            ({"pk__exact": (1, 2, 3)}, m_2_elements % "exact"),
            ({"pk__in": 1}, m_tuple % "in"),
            ({"pk__in": (1, 2, 3)}, m_tuple_collection),
            ({"pk__in": ((1, 2, 3),)}, m_2_elements_each),
            ({"pk__gt": 1}, m_tuple % "gt"),
            ({"pk__gt": (1, 2, 3)}, m_2_elements % "gt"),
            ({"pk__gte": 1}, m_tuple % "gte"),
            ({"pk__gte": (1, 2, 3)}, m_2_elements % "gte"),
            ({"pk__lt": 1}, m_tuple % "lt"),
            ({"pk__lt": (1, 2, 3)}, m_2_elements % "lt"),
            ({"pk__lte": 1}, m_tuple % "lte"),
            ({"pk__lte": (1, 2, 3)}, m_2_elements % "lte"),
        )

        for kwargs, message in test_cases:
            with (
                self.subTest(kwargs=kwargs),
                self.assertRaisesMessage(ValueError, message),
            ):
                Comment.objects.get(**kwargs)

    def test_get_user_by_comments(self):
        self.assertEqual(User.objects.get(comments=self.comment_1), self.user_1)

    def test_get_user_annotated_with_comments_id_count(self):
        users = User.objects.annotate(comments_count=Count("comments__id"))
        test_cases = (
            (self.user_1.id, 1),
            (self.user_2.id, 0),
            (self.user_3.id, 0),
        )

        for user_id, count in test_cases:
            with self.subTest(user_id=user_id):
                user = users.get(id=user_id)
                self.assertEqual(user.comments_count, count)

    def test_values_list(self):
        self.assertSequenceEqual(
            User.objects.values_list("pk").order_by("pk"),
            (
                (self.user_1.pk,),
                (self.user_2.pk,),
                (self.user_3.pk,),
            ),
        )
        self.assertSequenceEqual(
            User.objects.values_list("pk", "email").order_by("pk"),
            (
                (self.user_1.pk, "user0001@example.com"),
                (self.user_2.pk, "user0002@example.com"),
                (self.user_3.pk, "user0003@example.com"),
            ),
        )
        self.assertSequenceEqual(
            User.objects.values_list("pk", "id").order_by("pk"),
            (
                (self.user_1.pk, self.user_1.id),
                (self.user_2.pk, self.user_2.id),
                (self.user_3.pk, self.user_3.id),
            ),
        )
        self.assertSequenceEqual(
            User.objects.values_list("pk", flat=True).order_by("pk"),
            (
                self.user_1.pk,
                self.user_2.pk,
                self.user_3.pk,
            ),
        )
        self.assertSequenceEqual(
            Post.objects.values_list("pk", flat=True).order_by("pk"),
            (
                (self.tenant_1.id, UUID("748ae4e5-eed7-442d-a93d-43867eadee2b")),
                (self.tenant_1.id, UUID("b36cebfc-a9a5-48fd-baeb-2ad0fe63b260")),
                (self.tenant_2.id, UUID("aa3d4b88-6ae1-45be-890e-32dd7e71b790")),
            ),
        )

    def test_values(self):
        self.assertSequenceEqual(
            User.objects.values("pk").order_by("pk"),
            (
                {"pk": self.user_1.pk},
                {"pk": self.user_2.pk},
                {"pk": self.user_3.pk},
            ),
        )
        self.assertSequenceEqual(
            User.objects.values("pk", "email").order_by("pk"),
            (
                {"pk": self.user_1.pk, "email": "user0001@example.com"},
                {"pk": self.user_2.pk, "email": "user0002@example.com"},
                {"pk": self.user_3.pk, "email": "user0003@example.com"},
            ),
        )
        self.assertSequenceEqual(
            User.objects.values("pk", "id").order_by("pk"),
            (
                {"pk": self.user_1.pk, "id": self.user_1.id},
                {"pk": self.user_2.pk, "id": self.user_2.id},
                {"pk": self.user_3.pk, "id": self.user_3.id},
            ),
        )
