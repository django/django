from django.test import TestCase

from .models import Comment, Tenant, Token, User


class CompositePKUpdateTests(TestCase):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.tenant_1 = Tenant.objects.create(name="A")
        cls.tenant_2 = Tenant.objects.create(name="B")
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
        cls.token_1 = Token.objects.create(id=1, tenant=cls.tenant_1)
        cls.token_2 = Token.objects.create(id=2, tenant=cls.tenant_2)
        cls.token_3 = Token.objects.create(id=3, tenant=cls.tenant_1)
        cls.token_4 = Token.objects.create(id=4, tenant=cls.tenant_2)

    def test_update_user(self):
        email = "user9315@example.com"
        result = User.objects.filter(pk=self.user_1.pk).update(email=email)
        self.assertEqual(result, 1)
        user = User.objects.get(pk=self.user_1.pk)
        self.assertEqual(user.email, email)

    def test_save_user(self):
        count = User.objects.count()
        email = "user9314@example.com"
        user = User.objects.get(pk=self.user_1.pk)
        user.email = email
        user.save()
        user.refresh_from_db()
        self.assertEqual(user.email, email)
        user = User.objects.get(pk=self.user_1.pk)
        self.assertEqual(user.email, email)
        self.assertEqual(count, User.objects.count())

    def test_bulk_update_comments(self):
        comment_1 = Comment.objects.get(pk=self.comment_1.pk)
        comment_2 = Comment.objects.get(pk=self.comment_2.pk)
        comment_3 = Comment.objects.get(pk=self.comment_3.pk)
        comment_1.text = "foo"
        comment_2.text = "bar"
        comment_3.text = "baz"

        result = Comment.objects.bulk_update(
            [comment_1, comment_2, comment_3], ["text"]
        )

        self.assertEqual(result, 3)
        comment_1 = Comment.objects.get(pk=self.comment_1.pk)
        comment_2 = Comment.objects.get(pk=self.comment_2.pk)
        comment_3 = Comment.objects.get(pk=self.comment_3.pk)
        self.assertEqual(comment_1.text, "foo")
        self.assertEqual(comment_2.text, "bar")
        self.assertEqual(comment_3.text, "baz")

    def test_update_or_create_user(self):
        test_cases = (
            {
                "pk": self.user_1.pk,
                "defaults": {"email": "user3914@example.com"},
            },
            {
                "pk": (self.tenant_1.id, self.user_1.id),
                "defaults": {"email": "user9375@example.com"},
            },
            {
                "tenant": self.tenant_1,
                "id": self.user_1.id,
                "defaults": {"email": "user3517@example.com"},
            },
            {
                "tenant_id": self.tenant_1.id,
                "id": self.user_1.id,
                "defaults": {"email": "user8391@example.com"},
            },
        )

        for fields in test_cases:
            with self.subTest(fields=fields):
                count = User.objects.count()
                user, created = User.objects.update_or_create(**fields)
                self.assertIs(created, False)
                self.assertEqual(user.id, self.user_1.id)
                self.assertEqual(user.pk, (self.tenant_1.id, self.user_1.id))
                self.assertEqual(user.tenant_id, self.tenant_1.id)
                self.assertEqual(user.email, fields["defaults"]["email"])
                self.assertEqual(count, User.objects.count())

    def test_update_comment_by_user_email(self):
        result = Comment.objects.filter(user__email=self.user_1.email).update(
            text="foo"
        )

        self.assertEqual(result, 2)
        comment_1 = Comment.objects.get(pk=self.comment_1.pk)
        comment_2 = Comment.objects.get(pk=self.comment_2.pk)
        self.assertEqual(comment_1.text, "foo")
        self.assertEqual(comment_2.text, "foo")

    def test_update_token_by_tenant_name(self):
        result = Token.objects.filter(tenant__name="A").update(secret="bar")

        self.assertEqual(result, 2)
        token_1 = Token.objects.get(pk=self.token_1.pk)
        self.assertEqual(token_1.secret, "bar")
        token_3 = Token.objects.get(pk=self.token_3.pk)
        self.assertEqual(token_3.secret, "bar")

    def test_cant_update_to_unsaved_object(self):
        msg = (
            "Unsaved model instance <User: User object ((None, None))> cannot be used "
            "in an ORM query."
        )

        with self.assertRaisesMessage(ValueError, msg):
            Comment.objects.update(user=User())
