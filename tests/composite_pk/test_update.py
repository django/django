from django.core.exceptions import FieldError
from django.db import connection
from django.db.models import F
from django.test import TestCase

from .models import Comment, Tenant, TimeStamped, Token, User


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
        with self.assertNumQueries(1) as ctx:
            user.save()
        sql = ctx[0]["sql"]
        self.assertEqual(sql.count(connection.ops.quote_name("tenant_id")), 1)
        self.assertEqual(sql.count(connection.ops.quote_name("id")), 1)
        user.refresh_from_db()
        self.assertEqual(user.email, email)
        user = User.objects.get(pk=self.user_1.pk)
        self.assertEqual(user.email, email)
        self.assertEqual(count, User.objects.count())

    def test_update_fields_deferred(self):
        c = Comment.objects.defer("text", "user_id").get(pk=self.comment_1.pk)
        c.text = "Hello"

        with self.assertNumQueries(1) as ctx:
            c.save()

        sql = ctx[0]["sql"]
        self.assertEqual(sql.count(connection.ops.quote_name("tenant_id")), 1)
        self.assertEqual(sql.count(connection.ops.quote_name("comment_id")), 1)

        c = Comment.objects.get(pk=self.comment_1.pk)
        self.assertEqual(c.text, "Hello")

    def test_update_fields_pk_field(self):
        msg = (
            "The following fields do not exist in this model, are m2m fields, "
            "primary keys, or are non-concrete fields: id"
        )
        with self.assertRaisesMessage(ValueError, msg):
            self.user_1.save(update_fields=["id"])

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

    def test_bulk_update_primary_key_fields(self):
        message = "bulk_update() cannot be used with primary key fields."
        with self.assertRaisesMessage(ValueError, message):
            Comment.objects.bulk_update([self.comment_1, self.comment_2], ["id"])

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

    def test_update_or_create_with_pre_save_pk_field(self):
        t = TimeStamped.objects.create(id=1)
        self.assertEqual(TimeStamped.objects.count(), 1)
        t, created = TimeStamped.objects.update_or_create(
            pk=t.pk, defaults={"text": "new text"}
        )
        self.assertIs(created, False)
        self.assertEqual(TimeStamped.objects.count(), 1)
        self.assertEqual(t.text, "new text")

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

    def test_cant_update_pk_field(self):
        qs = Comment.objects.filter(user__email=self.user_1.email)
        msg = "Composite primary key fields must be updated individually."
        with self.assertRaisesMessage(FieldError, msg):
            qs.update(pk=(1, 10))

    def test_update_value_not_composite(self):
        msg = (
            "Composite primary keys expressions are not allowed in this "
            "query (text=F('pk'))."
        )
        with self.assertRaisesMessage(FieldError, msg):
            Comment.objects.update(text=F("pk"))
