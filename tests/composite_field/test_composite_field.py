from django.test import TestCase

from django.db.models import (
    CompositeField,
    EmailField,
    CharField
)
from django.db.models.expressions import Subquery, OuterRef

from .models import User, Post


class CompositeFieldTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        users = User.objects.bulk_create([
            User(
                email="user001@mail.com",
                first_name="John",
            ),
            User(
                email="user002@mail.com",
                first_name="Bob",
            ),
            User(
                email="user003@mail.com",
                first_name="Mike",
            ),
        ])

        cls.user1, cls.user2, cls.user3 = users

        cls.posts = Post.objects.bulk_create([
            Post(
                user=cls.user1,
                title="user1 first post title",
                body="body of first post",
            ),
            Post(
                user=cls.user1,
                title="user1 second post title",
                body="body of second post",
            ),
            Post(
                user=cls.user1,
                title="user1 third post title",
                body="body of third post",
            ),
            Post(
                user=cls.user2,
                title="user2 first post title",
                body="body of first post",
            ),
            Post(
                user=cls.user2,
                title="user2 second post title",
                body="body of second post",
            ),
            Post(
                user=cls.user2,
                title="user2 third post title",
                body="body of third post",
            ),
            Post(
                user=cls.user3,
                title="user3 first post title",
                body="body of first post",
            ),
            Post(
                user=cls.user3,
                title="user3 second post title",
                body="body of second post",
            ),
            Post(
                user=cls.user3,
                title="user3 third post title",
                body="body of third post",
            ),
        ])
    
    def test_composite_subquery_email_lookup(self):
        composite_field = CompositeField(
            email=EmailField(),
            first_name=CharField(),
        )

        subquery = Subquery(
            User.objects.filter(pk=self.user1.pk).values(
                "email",
                "first_name",
            ),
            output_field=composite_field,
        )

        qs = User.objects.alias(info=subquery).filter(
            info__email=self.user1.email,
        )

        self.assertEqual(qs.count(), 3)