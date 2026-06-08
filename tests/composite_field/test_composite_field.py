from django.core.exceptions import FieldError
from django.db.models import (
    Case,
    CharField,
    CompositeField,
    Count,
    EmailField,
    F,
    IntegerField,
    Value,
    When,
)
from django.db.models.expressions import Subquery
from django.db.models.functions import Cast, Concat, Length, Lower
from django.test import TestCase

from .expressions import JsonEachFunc
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

        # print(qs)

        self.assertEqual(qs.count(), 3)

    def test_composite_subfields_in_db_functions(self):
        composite_field = CompositeField(
            email=EmailField(),
            first_name=CharField(),
        )
        subquery = Subquery(
            User.objects.filter(pk=self.user1.pk).values("email", "first_name"),
            output_field=composite_field,
        )

        qs = (
            User.objects.alias(info=subquery)
            .annotate(
                lower_email=Lower("info__email"), name_length=Length("info__first_name")
            )
            .values("lower_email", "name_length")
        )

        result = qs.first()
        self.assertEqual(result["lower_email"], self.user1.email.lower())
        self.assertEqual(result["name_length"], len(self.user1.first_name))

    def test_composite_in_conditional_expression(self):
        composite_field = CompositeField(
            email=EmailField(),
            first_name=CharField(),
        )
        subquery = Subquery(
            User.objects.filter(pk=self.user1.pk).values("email", "first_name"),
            output_field=composite_field,
        )

        qs = (
            User.objects.alias(info=subquery)
            .annotate(
                is_john=Case(
                    When(info__first_name="John", then=Value("Yes")),
                    default=Value("No"),
                    output_field=CharField(),
                )
            )
            .filter(pk=self.user1.pk)
        )

        self.assertEqual(qs.first().is_john, "Yes")

    def test_composite_subfield_in_lookup(self):
        composite_field = CompositeField(
            user=CompositeField(id=IntegerField(), email=EmailField()),
            title=CharField(),
        )
        subquery = Subquery(
            Post.objects.filter(user__pk=self.user1.pk).values("user__id", "title"),
            output_field=composite_field,
        )

        allowed_ids = [self.user3.pk, self.user2.pk]
        qs = (
            User.objects.alias(post_info=subquery)
            .filter(post_info__user__id__in=allowed_ids)
            .values("id")
        )

        self.assertEqual(len(qs), 0)

    def test_composite_subquery_returning_empty_resolves_to_none(self):
        composite_field = CompositeField(email=EmailField())

        empty_subquery = Subquery(
            User.objects.filter(pk=999999).values("email"),
            output_field=composite_field,
        )

        qs = (
            User.objects.alias(info=empty_subquery)
            .annotate(extracted_email=F("info__email"))
            .values("extracted_email")
        )

        self.assertIsNone(qs.first())

    def test_composite_subfield_explicit_cast(self):
        composite_field = CompositeField(severity_level=IntegerField())
        subquery = Subquery(
            BugReport.objects.filter(pk=self.bug_report.pk).values("severity_level"),
            output_field=composite_field,
        )

        qs = (
            User.objects.alias(report=subquery)
            .annotate(
                severity_str=Cast("report__severity_level", output_field=CharField())
            )
            .values("severity_str")
        )

        self.assertEqual(
            qs.first()["severity_str"], str(self.bug_report.severity_level)
        )

    def test_composite_field_alongside_json_function(self):
        composite_field = CompositeField(title=CharField())
        subquery = Subquery(
            Post.objects.filter(pk=self.posts[0].pk).values("title"),
            output_field=composite_field,
        )

        qs = User.objects.alias(
            post_info=subquery, json_data=JsonEachFunc(Value('{"meta": "data"}'))
        ).filter(post_info__title=self.posts[0].title)

        self.assertTrue(qs.exists())

    def test_composite_subfield_string_lookups(self):
        composite_field = CompositeField(
            title=CharField(),
            body=CharField(),
        )
        subquery = Subquery(
            Post.objects.filter(pk=self.posts[0].pk).values("title", "body"),
            output_field=composite_field,
        )

        qs = (
            User.objects.filter(pk=self.user1.pk)
            .alias(post_info=subquery)
            .filter(
                post_info__title__contains="first", post_info__body__startswith="body"
            )
        )

        self.assertEqual(qs.count(), 1)

    def test_composite_subfield_range_and_comparison(self):
        composite_field = CompositeField(
            description=CharField(),
            severity_level=IntegerField(),
        )
        subquery = Subquery(
            BugReport.objects.filter(pk=self.bug_report.pk).values(
                "description", "severity_level"
            ),
            output_field=composite_field,
        )

        qs_gt = (
            User.objects.filter(pk=self.user1.pk)
            .alias(report=subquery)
            .filter(report__severity_level__gt=3)
        )
        qs_range = (
            User.objects.filter(pk=self.user1.pk)
            .alias(report=subquery)
            .filter(report__severity_level__range=(1, 10))
        )

        self.assertEqual(qs_gt.count(), 1)
        self.assertEqual(qs_range.count(), 1)

    def test_composite_subfield_isnull(self):
        composite_field = CompositeField(
            email=EmailField(),
            first_name=CharField(),
        )
        subquery = Subquery(
            User.objects.filter(pk=self.user1.pk).values("email", "first_name"),
            output_field=composite_field,
        )

        qs = (
            User.objects.filter(pk=self.user1.pk)
            .alias(info=subquery)
            .filter(
                info__email__isnull=False,
                info__first_name__isnull=False,
            )
        )

        self.assertEqual(qs.count(), 1)

    def test_composite_subfield_concatenation(self):
        composite_field = CompositeField(
            email=EmailField(),
            first_name=CharField(),
        )
        subquery = Subquery(
            User.objects.filter(pk=self.user1.pk).values("email", "first_name"),
            output_field=composite_field,
        )

        qs = (
            User.objects.filter(pk=self.user1.pk)
            .alias(info=subquery)
            .annotate(greeting=Concat(Value("Hello, "), "info__first_name"))
            .values("greeting")
        )

        self.assertEqual(qs.first()["greeting"], f"Hello, {self.user1.first_name}")

    def test_composite_subfield_arithmetic(self):
        composite_field = CompositeField(
            description=CharField(),
            severity_level=IntegerField(),
        )
        subquery = Subquery(
            BugReport.objects.filter(pk=self.bug_report.pk).values(
                "description", "severity_level"
            ),
            output_field=composite_field,
        )

        qs = (
            User.objects.filter(pk=self.user1.pk)
            .alias(report=subquery)
            .annotate(adjusted_severity=F("report__severity_level") + 2)
            .values("adjusted_severity")
        )

        self.assertEqual(qs.first()["adjusted_severity"], 7)
