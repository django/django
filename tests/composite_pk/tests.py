import json
import unittest
from uuid import UUID

try:
    import yaml  # NOQA

    HAS_YAML = True
except ImportError:
    HAS_YAML = False

from django import forms
from django.core import serializers
from django.core.exceptions import FieldError
from django.db import IntegrityError, connection
from django.db.models import CompositePrimaryKey
from django.forms import modelform_factory
from django.test import TestCase

from .models import Comment, Post, Tenant, User


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = "__all__"


class CompositePKTests(TestCase):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create()
        cls.user = User.objects.create(
            tenant=cls.tenant,
            id=1,
            email="user0001@example.com",
        )
        cls.comment = Comment.objects.create(tenant=cls.tenant, id=1, user=cls.user)

    @staticmethod
    def get_primary_key_columns(table):
        with connection.cursor() as cursor:
            return connection.introspection.get_primary_key_columns(cursor, table)

    def test_pk_updated_if_field_updated(self):
        user = User.objects.get(pk=self.user.pk)
        self.assertEqual(user.pk, (self.tenant.id, self.user.id))
        self.assertIs(user._is_pk_set(), True)
        user.tenant_id = 9831
        self.assertEqual(user.pk, (9831, self.user.id))
        self.assertIs(user._is_pk_set(), True)
        user.id = 4321
        self.assertEqual(user.pk, (9831, 4321))
        self.assertIs(user._is_pk_set(), True)
        user.pk = (9132, 3521)
        self.assertEqual(user.tenant_id, 9132)
        self.assertEqual(user.id, 3521)
        self.assertIs(user._is_pk_set(), True)
        user.id = None
        self.assertEqual(user.pk, (9132, None))
        self.assertEqual(user.tenant_id, 9132)
        self.assertIsNone(user.id)
        self.assertIs(user._is_pk_set(), False)

    def test_hash(self):
        self.assertEqual(hash(User(pk=(1, 2))), hash((1, 2)))
        self.assertEqual(hash(User(tenant_id=2, id=3)), hash((2, 3)))
        msg = "Model instances without primary key value are unhashable"

        with self.assertRaisesMessage(TypeError, msg):
            hash(User())
        with self.assertRaisesMessage(TypeError, msg):
            hash(User(tenant_id=1))
        with self.assertRaisesMessage(TypeError, msg):
            hash(User(id=1))

    def test_pk_must_be_list_or_tuple(self):
        user = User.objects.get(pk=self.user.pk)
        test_cases = [
            "foo",
            1000,
            3.14,
            True,
            False,
        ]

        for pk in test_cases:
            with self.assertRaisesMessage(
                ValueError, "'pk' must be a list or a tuple."
            ):
                user.pk = pk

    def test_pk_must_have_2_elements(self):
        user = User.objects.get(pk=self.user.pk)
        test_cases = [
            (),
            [],
            (1000,),
            [1000],
            (1, 2, 3),
            [1, 2, 3],
        ]

        for pk in test_cases:
            with self.assertRaisesMessage(ValueError, "'pk' must have 2 elements."):
                user.pk = pk

    def test_composite_pk_in_fields(self):
        user_fields = {f.name for f in User._meta.get_fields()}
        self.assertEqual(user_fields, {"pk", "tenant", "id", "email", "comments"})

        comment_fields = {f.name for f in Comment._meta.get_fields()}
        self.assertEqual(
            comment_fields,
            {"pk", "tenant", "id", "user_id", "user", "text"},
        )

    def test_pk_field(self):
        pk = User._meta.get_field("pk")
        self.assertIsInstance(pk, CompositePrimaryKey)
        self.assertIs(User._meta.pk, pk)

    def test_error_on_user_pk_conflict(self):
        with self.assertRaises(IntegrityError):
            User.objects.create(tenant=self.tenant, id=self.user.id)

    def test_error_on_comment_pk_conflict(self):
        with self.assertRaises(IntegrityError):
            Comment.objects.create(tenant=self.tenant, id=self.comment.id, user_id=1)

    def test_get_primary_key_columns(self):
        self.assertEqual(
            self.get_primary_key_columns(User._meta.db_table),
            ["tenant_id", "id"],
        )
        self.assertEqual(
            self.get_primary_key_columns(Comment._meta.db_table),
            ["tenant_id", "comment_id"],
        )

    def test_in_bulk(self):
        """
        Test the .in_bulk() method of composite_pk models.
        """
        result = Comment.objects.in_bulk()
        self.assertEqual(result, {self.comment.pk: self.comment})

        result = Comment.objects.in_bulk([self.comment.pk])
        self.assertEqual(result, {self.comment.pk: self.comment})

    def test_iterator(self):
        """
        Test the .iterator() method of composite_pk models.
        """
        result = list(Comment.objects.iterator())
        self.assertEqual(result, [self.comment])

    def test_query(self):
        users = User.objects.values_list("pk").order_by("pk")
        self.assertNotIn('AS "pk"', str(users.query))

    def test_only(self):
        users = User.objects.only("pk")
        self.assertSequenceEqual(users, (self.user,))
        user = users[0]

        with self.assertNumQueries(0):
            self.assertEqual(user.pk, (self.user.tenant_id, self.user.id))
            self.assertEqual(user.tenant_id, self.user.tenant_id)
            self.assertEqual(user.id, self.user.id)
        with self.assertNumQueries(1):
            self.assertEqual(user.email, self.user.email)

    def test_model_forms(self):
        fields = ["tenant", "id", "user_id", "text"]
        self.assertEqual(list(CommentForm.base_fields), fields)

        form = modelform_factory(Comment, fields="__all__")
        self.assertEqual(list(form().fields), fields)

        with self.assertRaisesMessage(
            FieldError, "Unknown field(s) (pk) specified for Comment"
        ):
            self.assertIsNone(modelform_factory(Comment, fields=["pk"]))


class CompositePKFixturesTests(TestCase):
    fixtures = ["tenant"]

    def test_objects(self):
        tenant_1, tenant_2, tenant_3 = Tenant.objects.order_by("pk")
        self.assertEqual(tenant_1.id, 1)
        self.assertEqual(tenant_1.name, "Tenant 1")
        self.assertEqual(tenant_2.id, 2)
        self.assertEqual(tenant_2.name, "Tenant 2")
        self.assertEqual(tenant_3.id, 3)
        self.assertEqual(tenant_3.name, "Tenant 3")

        user_1, user_2, user_3, user_4 = User.objects.order_by("pk")
        self.assertEqual(user_1.id, 1)
        self.assertEqual(user_1.tenant_id, 1)
        self.assertEqual(user_1.pk, (user_1.tenant_id, user_1.id))
        self.assertEqual(user_1.email, "user0001@example.com")
        self.assertEqual(user_2.id, 2)
        self.assertEqual(user_2.tenant_id, 1)
        self.assertEqual(user_2.pk, (user_2.tenant_id, user_2.id))
        self.assertEqual(user_2.email, "user0002@example.com")
        self.assertEqual(user_3.id, 3)
        self.assertEqual(user_3.tenant_id, 2)
        self.assertEqual(user_3.pk, (user_3.tenant_id, user_3.id))
        self.assertEqual(user_3.email, "user0003@example.com")
        self.assertEqual(user_4.id, 4)
        self.assertEqual(user_4.tenant_id, 2)
        self.assertEqual(user_4.pk, (user_4.tenant_id, user_4.id))
        self.assertEqual(user_4.email, "user0004@example.com")

        post_1, post_2 = Post.objects.order_by("pk")
        self.assertEqual(post_1.id, UUID("11111111-1111-1111-1111-111111111111"))
        self.assertEqual(post_1.tenant_id, 2)
        self.assertEqual(post_1.pk, (post_1.tenant_id, post_1.id))
        self.assertEqual(post_2.id, UUID("ffffffff-ffff-ffff-ffff-ffffffffffff"))
        self.assertEqual(post_2.tenant_id, 2)
        self.assertEqual(post_2.pk, (post_2.tenant_id, post_2.id))

    def test_serialize_user_json(self):
        users = User.objects.filter(pk=(1, 1))
        result = serializers.serialize("json", users)
        self.assertEqual(
            json.loads(result),
            [
                {
                    "model": "composite_pk.user",
                    "pk": [1, 1],
                    "fields": {
                        "email": "user0001@example.com",
                        "id": 1,
                        "tenant": 1,
                    },
                }
            ],
        )

    def test_serialize_user_jsonl(self):
        users = User.objects.filter(pk=(1, 2))
        result = serializers.serialize("jsonl", users)
        self.assertEqual(
            json.loads(result),
            {
                "model": "composite_pk.user",
                "pk": [1, 2],
                "fields": {
                    "email": "user0002@example.com",
                    "id": 2,
                    "tenant": 1,
                },
            },
        )

    @unittest.skipUnless(HAS_YAML, "No yaml library detected")
    def test_serialize_user_yaml(self):
        users = User.objects.filter(pk=(2, 3))
        result = serializers.serialize("yaml", users)
        self.assertEqual(
            yaml.safe_load(result),
            [
                {
                    "model": "composite_pk.user",
                    "pk": [2, 3],
                    "fields": {
                        "email": "user0003@example.com",
                        "id": 3,
                        "tenant": 2,
                    },
                },
            ],
        )

    def test_serialize_user_python(self):
        users = User.objects.filter(pk=(2, 4))
        result = serializers.serialize("python", users)
        self.assertEqual(
            result,
            [
                {
                    "model": "composite_pk.user",
                    "pk": [2, 4],
                    "fields": {
                        "email": "user0004@example.com",
                        "id": 4,
                        "tenant": 2,
                    },
                },
            ],
        )

    def test_serialize_post_uuid(self):
        posts = Post.objects.filter(pk=(2, "11111111-1111-1111-1111-111111111111"))
        result = serializers.serialize("json", posts)
        self.assertEqual(
            json.loads(result),
            [
                {
                    "model": "composite_pk.post",
                    "pk": [2, "11111111-1111-1111-1111-111111111111"],
                    "fields": {
                        "id": "11111111-1111-1111-1111-111111111111",
                        "tenant": 2,
                    },
                },
            ],
        )
