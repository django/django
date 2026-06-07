from django.core.exceptions import FieldError
from django.db.models import (
    CharField,
    CompositeField,
    Count,
    EmailField,
    F,
    IntegerField,
)
from django.db.models.expressions import Subquery
from django.test import TestCase

from .models import (
    BugReport,
    Post,
    Project,
    Task,
    User,
    Workspace,
)


class CompositeFieldTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        users = User.objects.bulk_create(
            [
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
            ]
        )

        cls.user1, cls.user2, cls.user3 = users

        cls.posts = Post.objects.bulk_create(
            [
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
            ]
        )
        cls.workspace = Workspace.objects.create(
            owner=cls.user1,
            name="Core Platform Engine",
        )

        cls.project = Project.objects.create(
            workspace=cls.workspace,
            title="ORM Infrastructure Modernization",
        )

        cls.task = Task.objects.create(
            project=cls.project,
            name="Fix custom composite field compiler unrolling loop",
        )

        cls.bug_report = BugReport.objects.create(
            task=cls.task,
            description="AST traversal fails when looking up fields past 3 levels deep",
            severity_level=5,
        )

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

    def test_composite_with_nested_fields(self):
        composite_field = CompositeField(
            user=CompositeField(id=IntegerField(), email=EmailField()),
            title=CharField(),
            body=CharField(),
        )

        subquery = Subquery(
            Post.objects.filter(user__pk=self.user1.pk).values(
                "user__email",
                "title",
                "body",
                "user__id",
            ),
            output_field=composite_field,
        )

        qs = User.objects.alias(some=subquery).values(
            "some__title",
            "some__body",
            "some__user__email",
            "some__user__id",
        )
        self.assertEqual(qs.count(), 9)

    def test_composite_invalid_subfield_raises_error(self):
        composite_field = CompositeField(email=EmailField(), name=CharField())
        subquery = Subquery(
            User.objects.filter(pk=self.user1.pk).values("email"),
            output_field=composite_field,
        )

        with self.assertRaises(FieldError):
            list(User.objects.alias(info=subquery).values("info__typo"))

    def test_composite_aggregation_and_ordering(self):
        composite_field = CompositeField(
            user=CompositeField(email=EmailField(), age=IntegerField()),
            title=CharField(),
        )
        subquery = Subquery(
            Post.objects.filter(user__pk=self.user1.pk).values("user__email"),
            output_field=composite_field,
        )

        qs_ordered = User.objects.alias(some=subquery).order_by(
            F("some__user__email").desc()
        )

        self.assertEqual(qs_ordered.count(), 9)

        qs_agg = User.objects.annotate(some=subquery).aggregate(
            total=Count("some__user__email")
        )

        self.assertEqual(qs_agg["total"], 9)

    def test_composite_rhs_with_f_expression(self):
        composite_field = CompositeField(email=EmailField(), age=IntegerField())
        subquery = Subquery(
            User.objects.filter(pk=self.user1.pk).values("email"),
            output_field=composite_field,
        )

        qs = User.objects.alias(info=subquery).filter(email=F("info__email"))

        self.assertTrue(qs.filter(pk=self.user1.pk).exists())

    def test_composite_nested_lookup_five_levels(self):
        composite_field = CompositeField(
            task=CompositeField(
                name=CharField(),
                project=CompositeField(
                    title=CharField(),
                    workspace=CompositeField(
                        name=CharField(),
                        owner=CompositeField(
                            email=EmailField(),
                            first_name=CharField(),
                        ),
                    ),
                ),
            ),
        )

        subquery = Subquery(
            BugReport.objects.filter(
                pk=self.bug_report.pk,
            ).values(
                "task__name",
                "task__project__title",
                "task__project__workspace__name",
                "task__project__workspace__owner__email",
                "task__project__workspace__owner__first_name",
            ),
            output_field=composite_field,
        )

        qs = User.objects.alias(ticket=subquery).values(
            "ticket__task__project__workspace__owner__email",
            "ticket__task__project__workspace__owner__first_name",
        )

        print(qs)

        self.assertEqual(qs.count(), 3)
