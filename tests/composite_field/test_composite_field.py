from django.core.exceptions import FieldError
from django.db.models import (
    Avg,
    Case,
    CharField,
    CompositeField,
    Count,
    EmailField,
    F,
    IntegerField,
    Max,
    Min,
    OuterRef,
    Q,
    Sum,
    Value,
    When,
)
from django.db.models.expressions import Exists, Subquery
from django.db.models.functions import Cast, Coalesce, Concat, Length, Lower
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

        qs_agg = User.objects.alias(some=subquery).aggregate(
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

    def test_composite_annotate_before_values(self):
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
            .annotate(author_info=subquery)
            .values("author_info__email", "author_info__first_name")
        )

        result = qs.first()
        self.assertEqual(result["author_info__email"], self.user1.email)
        self.assertEqual(result["author_info__first_name"], self.user1.first_name)

    def test_composite_annotate_then_transform(self):
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
            .annotate(post_data=subquery)
            .annotate(lowercased_title=Lower("post_data__title"))
            .values("lowercased_title", "post_data__body")
        )

        result = qs.first()
        self.assertEqual(result["lowercased_title"], self.posts[0].title.lower())
        self.assertEqual(result["post_data__body"], self.posts[0].body)

    def test_composite_subquery_with_outerref(self):
        composite_field = CompositeField(
            title=CharField(),
            body=CharField(),
        )

        subquery = Subquery(
            Post.objects.filter(
                user=OuterRef("pk"),
            ).values(
                "title",
                "body",
            )[:1],
            output_field=composite_field,
        )
        qs = User.objects.annotate(post_info=subquery).values(
            "post_info__title",
            "post_info__body",
        )

        self.assertEqual(qs[0]["post_info__title"], "user1 first post title")

    def test_multiple_composite_aliases(self):
        composite_field1 = CompositeField(email=EmailField(), first_name=CharField())
        composite_field2 = CompositeField(title=CharField(), body=CharField())
        sub1 = Subquery(
            User.objects.filter(pk=self.user1.pk).values("email", "first_name"),
            output_field=composite_field1,
        )
        sub2 = Subquery(
            Post.objects.filter(pk=self.posts[0].pk).values("title", "body"),
            output_field=composite_field2,
        )
        qs = User.objects.alias(info1=sub1, info2=sub2).values(
            "info1__email", "info2__title"
        )
        result = qs.first()
        self.assertEqual(result["info1__email"], self.user1.email)
        self.assertEqual(result["info2__title"], self.posts[0].title)

    def test_composite_alias_exclude(self):
        composite_field = CompositeField(email=EmailField(), first_name=CharField())
        sub = Subquery(
            User.objects.filter(pk=self.user1.pk).values("email", "first_name"),
            output_field=composite_field,
        )
        qs = User.objects.alias(info=sub).exclude(info__email=self.user1.email)
        self.assertEqual(qs.count(), 0)

        qs2 = User.objects.alias(info=sub).exclude(info__email="nonexistent@mail.com")
        self.assertEqual(qs2.count(), 3)
        self.assertEqual(
            list(qs2.order_by("pk").values_list("email", flat=True)),
            ["user001@mail.com", "user002@mail.com", "user003@mail.com"],
        )

    def test_composite_values_list(self):
        composite_field = CompositeField(email=EmailField(), first_name=CharField())
        sub = Subquery(
            User.objects.filter(pk=self.user1.pk).values("email", "first_name"),
            output_field=composite_field,
        )
        qs_flat = User.objects.alias(info=sub).values_list("info__email", flat=True)
        self.assertEqual(list(qs_flat), [self.user1.email] * 3)

        qs_normal = User.objects.alias(info=sub).values_list(
            "info__email", "info__first_name"
        )
        self.assertEqual(
            list(qs_normal), [(self.user1.email, self.user1.first_name)] * 3
        )

    def test_composite_aggregation_math(self):
        composite_field = CompositeField(severity_level=IntegerField())
        sub = Subquery(
            BugReport.objects.filter(pk=self.bug_report.pk).values("severity_level"),
            output_field=composite_field,
        )
        res = User.objects.alias(report=sub).aggregate(
            total_severity=Sum("report__severity_level"),
            avg_severity=Avg("report__severity_level"),
        )
        self.assertEqual(res["total_severity"], self.bug_report.severity_level * 3)
        self.assertEqual(res["avg_severity"], self.bug_report.severity_level)

    def test_composite_q_or(self):
        composite_field = CompositeField(email=EmailField(), first_name=CharField())
        sub = Subquery(
            User.objects.filter(pk=self.user1.pk).values("email", "first_name"),
            output_field=composite_field,
        )
        qs = User.objects.alias(info=sub).filter(
            Q(info__email=self.user1.email) | Q(first_name="Bob")
        )
        self.assertEqual(qs.count(), 3)
        self.assertCountEqual(
            qs.values_list("email", flat=True),
            ["user001@mail.com", "user002@mail.com", "user003@mail.com"],
        )

    def test_composite_referenced_in_nested_subquery(self):
        composite_field = CompositeField(email=EmailField(), first_name=CharField())
        sub_outer = Subquery(
            User.objects.filter(pk=self.user1.pk).values("email", "first_name"),
            output_field=composite_field,
        )
        sub_inner = Subquery(
            User.objects.filter(email=OuterRef("info__email")).values("pk")[:1]
        )
        qs = (
            User.objects.alias(info=sub_outer)
            .annotate(inner_user_id=sub_inner)
            .filter(pk=self.user1.pk)
        )
        self.assertEqual(qs.first().inner_user_id, self.user1.pk)

    def test_correlated_composite_alias(self):
        composite_field = CompositeField(title=CharField(), body=CharField())
        subquery = Subquery(
            Post.objects.filter(user=OuterRef("pk")).values("title", "body")[:1],
            output_field=composite_field,
        )
        qs = (
            User.objects.alias(post_info=subquery)
            .annotate(post_title=F("post_info__title"))
            .filter(post_title__isnull=False)
            .order_by("pk")
        )
        self.assertEqual(qs.count(), 3)
        self.assertEqual(qs[0].post_title, "user1 first post title")
        self.assertEqual(qs[1].post_title, "user2 first post title")
        self.assertEqual(qs[2].post_title, "user3 first post title")

    def test_composite_distinct(self):
        composite_field = CompositeField(email=EmailField(), first_name=CharField())
        sub = Subquery(
            User.objects.filter(pk=self.user1.pk).values("email", "first_name"),
            output_field=composite_field,
        )
        qs = (
            User.objects.alias(info=sub)
            .values(
                "info__email",
                "info__first_name",
            )
            .distinct()
        )
        self.assertEqual(
            list(qs),
            [
                {
                    "info__email": self.user1.email,
                    "info__first_name": self.user1.first_name,
                }
            ],
        )

    def test_composite_order_by_string(self):
        composite_field = CompositeField(
            user=CompositeField(email=EmailField()),
            title=CharField(),
        )
        subquery = Subquery(
            Post.objects.filter(
                user__pk=OuterRef("pk"),
            ).values(
                "user__email", "title"
            )[:1],
            output_field=composite_field,
        )
        qs = (
            User.objects.alias(some=subquery)
            .order_by("-some__user__email")
            .values_list("email", flat=True)
        )
        self.assertEqual(
            list(qs), ["user003@mail.com", "user002@mail.com", "user001@mail.com"]
        )

    def test_composite_subquery_email_lookup_values(self):
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
            .filter(info__email=self.user1.email)
            .order_by("pk")
            .values("email", "first_name")
        )
        result = list(qs)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]["email"], self.user1.email)
        self.assertEqual(result[0]["first_name"], self.user1.first_name)
        self.assertEqual(result[1]["email"], self.user2.email)
        self.assertEqual(result[2]["email"], self.user3.email)

    def test_composite_exists_filter(self):
        composite_field = CompositeField(email=EmailField(), first_name=CharField())
        subquery = Subquery(
            User.objects.filter(pk=OuterRef("pk")).values("email", "first_name")[:1],
            output_field=composite_field,
        )
        inner_qs = User.objects.alias(info=subquery).filter(
            info__email=OuterRef("email")
        )
        qs = User.objects.filter(Exists(inner_qs)).order_by("pk")
        self.assertEqual(qs.count(), 3)
        self.assertEqual(qs.first().email, self.user1.email)

    def test_two_composites_cross_reference(self):
        composite_field1 = CompositeField(email=EmailField(), first_name=CharField())
        composite_field2 = CompositeField(email=EmailField(), first_name=CharField())
        sub1 = Subquery(
            User.objects.filter(pk=self.user1.pk).values("email", "first_name"),
            output_field=composite_field1,
        )
        sub2 = Subquery(
            User.objects.filter(pk=self.user1.pk).values("email", "first_name"),
            output_field=composite_field2,
        )
        qs = User.objects.alias(a=sub1, b=sub2).filter(a__email=F("b__email"))
        self.assertEqual(qs.count(), 3)

        qs_mismatch = User.objects.alias(a=sub1, b=sub2).filter(
            a__email=F("b__first_name")
        )
        self.assertEqual(qs_mismatch.count(), 0)

    def test_composite_subfield_coalesce(self):
        composite_field = CompositeField(email=EmailField(), first_name=CharField())
        subquery = Subquery(
            User.objects.filter(pk=self.user1.pk).values("email", "first_name"),
            output_field=composite_field,
        )
        qs = (
            User.objects.filter(pk=self.user1.pk)
            .alias(info=subquery)
            .annotate(safe_email=Coalesce("info__email", Value("fallback@example.com")))
            .values("safe_email")
        )
        self.assertEqual(qs.first()["safe_email"], self.user1.email)

        empty_composite = CompositeField(email=EmailField())
        empty_sub = Subquery(
            User.objects.filter(pk=999999).values("email"),
            output_field=empty_composite,
        )
        qs_empty = (
            User.objects.filter(pk=self.user1.pk)
            .alias(info=empty_sub)
            .annotate(safe_email=Coalesce("info__email", Value("fallback@example.com")))
            .values("safe_email")
        )
        self.assertEqual(qs_empty.first()["safe_email"], "fallback@example.com")

    def test_composite_aggregation_max_min(self):
        composite_field = CompositeField(
            severity_level=IntegerField(),
            description=CharField(),
        )
        sub = Subquery(
            BugReport.objects.filter(pk=self.bug_report.pk).values(
                "severity_level", "description"
            ),
            output_field=composite_field,
        )
        res = User.objects.alias(report=sub).aggregate(
            max_sev=Max("report__severity_level"),
            min_sev=Min("report__severity_level"),
        )
        self.assertEqual(res["max_sev"], self.bug_report.severity_level)
        self.assertEqual(res["min_sev"], self.bug_report.severity_level)

    def test_composite_negated_q(self):
        composite_field = CompositeField(email=EmailField(), first_name=CharField())
        sub = Subquery(
            User.objects.filter(pk=self.user1.pk).values("email", "first_name"),
            output_field=composite_field,
        )
        qs = User.objects.alias(info=sub).filter(~Q(info__email=self.user1.email))
        self.assertEqual(qs.count(), 0)

        qs2 = User.objects.alias(info=sub).filter(
            ~Q(info__email="nonexistent@mail.com")
        )
        self.assertEqual(qs2.count(), 3)

    def test_composite_annotation_filter_combined(self):
        composite_field = CompositeField(
            email=EmailField(),
            age=IntegerField(),
        )
        subquery = Subquery(
            User.objects.filter(pk=self.user1.pk).values("email", "age"),
            output_field=composite_field,
        )
        qs = (
            User.objects.alias(info=subquery)
            .annotate(
                user_age=F("info__age"),
                user_email=F("info__email"),
            )
            .filter(user_age=self.user1.age)
            .order_by("pk")
        )
        self.assertEqual(qs.count(), 3)
        first = qs.first()
        self.assertEqual(first.user_email, self.user1.email)
        self.assertEqual(first.user_age, self.user1.age)

    def test_composite_subfield_as_subquery_filter_rhs(self):
        composite_field = CompositeField(email=EmailField(), first_name=CharField())
        sub = Subquery(
            User.objects.filter(pk=self.user1.pk).values("email", "first_name"),
            output_field=composite_field,
        )
        qs = User.objects.alias(info=sub).filter(email=F("info__email")).order_by("pk")
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().pk, self.user1.pk)

    def test_composite_union(self):
        composite_field = CompositeField(email=EmailField(), first_name=CharField())
        sub1 = Subquery(
            User.objects.filter(pk=self.user1.pk).values("email", "first_name"),
            output_field=composite_field,
        )
        sub2 = Subquery(
            User.objects.filter(pk=self.user2.pk).values("email", "first_name"),
            output_field=composite_field,
        )
        qs1 = (
            User.objects.filter(pk=self.user1.pk)
            .alias(info=sub1)
            .annotate(resolved_email=F("info__email"))
            .values("resolved_email")
        )
        qs2 = (
            User.objects.filter(pk=self.user2.pk)
            .alias(info=sub2)
            .annotate(resolved_email=F("info__email"))
            .values("resolved_email")
        )
        combined = qs1.union(qs2)
        result_emails = sorted(r["resolved_email"] for r in combined)
        self.assertEqual(result_emails, sorted([self.user1.email, self.user2.email]))

    def test_composite_intersection(self):
        composite_field = CompositeField(email=EmailField(), first_name=CharField())
        sub = Subquery(
            User.objects.filter(pk=self.user1.pk).values("email", "first_name"),
            output_field=composite_field,
        )
        qs1 = (
            User.objects.filter(pk=self.user1.pk)
            .alias(info=sub)
            .annotate(resolved_email=F("info__email"))
            .values("resolved_email")
        )
        qs2 = (
            User.objects.filter(pk=self.user1.pk)
            .alias(info=sub)
            .annotate(resolved_email=F("info__email"))
            .values("resolved_email")
        )
        combined = qs1.intersection(qs2)
        result = list(combined)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["resolved_email"], self.user1.email)

    def test_composite_deconstruct_round_trip(self):
        original = CompositeField(
            email=EmailField(),
            first_name=CharField(),
            severity_level=IntegerField(),
        )
        name, path, args, kwargs = original.deconstruct()
        self.assertEqual(path, "django.db.models.CompositeField")
        self.assertIn("email", args)
        self.assertIn("first_name", args)
        self.assertIn("severity_level", args)
        self.assertIsInstance(args["email"], EmailField)
        self.assertIsInstance(args["first_name"], CharField)
        self.assertIsInstance(args["severity_level"], IntegerField)

    def test_composite_deconstruct_nested(self):
        inner = CompositeField(email=EmailField(), age=IntegerField())
        outer = CompositeField(user=inner, title=CharField())
        name, path, args, kwargs = outer.deconstruct()
        self.assertIn("user", args)
        self.assertIn("title", args)
        self.assertIsInstance(args["user"], CompositeField)
        _, _, inner_args, _ = args["user"].deconstruct()
        self.assertIn("email", inner_args)
        self.assertIn("age", inner_args)

    def test_composite_only_and_defer_are_safe(self):
        composite_field = CompositeField(email=EmailField(), first_name=CharField())
        sub = Subquery(
            User.objects.filter(pk=self.user1.pk).values("email", "first_name"),
            output_field=composite_field,
        )
        qs_only = (
            User.objects.alias(info=sub)
            .filter(info__email=self.user1.email)
            .only("email")
        )
        self.assertEqual(qs_only.count(), 3)
        first = qs_only.first()
        self.assertEqual(first.email, self.user1.email)

        qs_defer = (
            User.objects.alias(info=sub)
            .filter(info__email=self.user1.email)
            .defer("first_name")
        )
        self.assertEqual(qs_defer.count(), 3)
        first = qs_defer.first()
        self.assertEqual(first.email, self.user1.email)

    def test_composite_select_related_noop(self):
        composite_field = CompositeField(title=CharField(), body=CharField())
        sub = Subquery(
            Post.objects.filter(pk=self.posts[0].pk).values("title", "body"),
            output_field=composite_field,
        )
        qs = (
            Post.objects.alias(post_info=sub)
            .filter(post_info__title=self.posts[0].title)
            .select_related("user")
        )
        self.assertTrue(qs.exists())
        post = qs.first()
        self.assertEqual(post.user.email, self.user1.email)

    def test_composite_prefetch_related_noop(self):
        composite_field = CompositeField(email=EmailField(), first_name=CharField())
        sub = Subquery(
            User.objects.filter(pk=self.user1.pk).values("email", "first_name"),
            output_field=composite_field,
        )
        qs = (
            User.objects.alias(info=sub)
            .filter(info__email=self.user1.email)
            .prefetch_related("posts")
        )
        self.assertEqual(qs.count(), 3)
        user = qs.get(pk=self.user1.pk)
        self.assertEqual(user.posts.count(), 3)
