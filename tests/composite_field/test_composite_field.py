from operator import itemgetter

from django.core.exceptions import FieldError
from django.db import connection, models
from django.db.models import Count, F, OuterRef, Q
from django.db.models.functions import Upper
from django.test import SimpleTestCase, TestCase, skipUnlessDBFeature
from django.test.utils import register_lookup

from .models import BugReport, Organization, Post, Project, Task, User, Workspace


class CompositeFieldOutputFieldTests(SimpleTestCase):
    def test_init_validation(self):
        msg = "'name' should be a Field instance, got str."
        with self.assertRaisesMessage(TypeError, msg):
            models.CompositeField(name="name", age=models.IntegerField())
        with self.assertRaises(ValueError):
            models.CompositeField(name=models.CharField())

    def test_fields(self):
        info = User.objects.values("email", "age").query.output_field
        email = User._meta.get_field("email")
        age = User._meta.get_field("age")

        self.assertEqual(
            list(info.get_fields()),
            [
                (("email",), email),
                (("age",), age),
            ],
        )
        self.assertIs(info.get_field("email"), email)
        with self.assertRaises(FieldError):
            info.get_field("missing")

    def test_nested_fields(self):
        number = models.IntegerField()
        key = models.TextField()
        value = models.TextField()
        output_field = models.CompositeField(
            number=number,
            item=models.CompositeField(
                key=key,
                value=value,
            ),
        )

        self.assertEqual(
            list(output_field.get_fields()),
            [
                (("number",), number),
                (("item", "key"), key),
                (("item", "value"), value),
            ],
        )
        self.assertIs(output_field.get_field("item__key"), key)
        self.assertIs(output_field.get_field("item__value"), value)

    def test_clone(self):
        output_field = models.CompositeField(
            number=models.IntegerField(),
            item=models.CompositeField(
                key=models.TextField(db_column="item_key"),
                value=models.TextField(),
            ),
        )

        clone = output_field.clone()

        self.assertIsNot(clone, output_field)
        self.assertEqual(
            [
                (path, type(field), field.db_column)
                for path, field in clone.get_fields()
            ],
            [
                (("number",), models.IntegerField, None),
                (("item", "key"), models.TextField, "item_key"),
                (("item", "value"), models.TextField, None),
            ],
        )
        for path, field in output_field.get_fields():
            self.assertIsNot(clone.get_field("__".join(path)), field)

    def test_empty_select(self):
        self.assertIsNone(models.CompositeField.from_select({}))


class CompositeSubqueryTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.acme = Organization.objects.create(name="Acme", slug="acme")
        cls.beta = Organization.objects.create(name="Beta", slug="beta")

        cls.ada = User.objects.create(
            name="Ada",
            email="ada@example.com",
            age=34,
            organization=cls.acme,
        )
        cls.bob = User.objects.create(
            name="Bob",
            email="bob@example.com",
            age=28,
            organization=cls.acme,
        )

        cls.core = Workspace.objects.create(
            organization=cls.acme, owner=cls.ada, name="Core"
        )
        cls.labs = Workspace.objects.create(
            organization=cls.beta, owner=cls.ada, name="Labs"
        )

        cls.auth = Project.objects.create(
            workspace=cls.core, owner=cls.ada, title="Authentication", code="AUTH"
        )
        cls.reports = Project.objects.create(
            workspace=cls.labs, owner=cls.ada, title="Reports", code="RPT"
        )

        cls.login = Task.objects.create(
            project=cls.auth,
            assignee=cls.bob,
            name="Login flow",
            status="open",
        )
        cls.export = Task.objects.create(
            project=cls.reports, assignee=None, name="Export CSV", status="blocked"
        )

        cls.crash_report = BugReport.objects.create(
            task=cls.login,
            reporter=cls.bob,
            description="Login crash",
            severity_level=3,
        )
        cls.missing_export_report = BugReport.objects.create(
            task=cls.export,
            reporter=None,
            description="Export missing rows",
            severity_level=2,
        )

        cls.welcome_post = Post.objects.create(
            user=cls.ada, title="Welcome", body="Hello"
        )
        cls.duplicate_welcome_post = Post.objects.create(
            user=cls.bob, title="Welcome", body="Hello"
        )


class CompositeFieldTests(CompositeSubqueryTestCase):

    def test_composite_subquery_alias_or_preserves_outer_rows(self):
        missing_project = Project.objects.filter(pk=-1).values("pk", "code")
        projects = (
            Project.objects.alias(project_info=missing_project)
            .filter(Q(pk=F("project_info__pk"), title="Authentication") | Q(code="RPT"))
            .values_list("code", flat=True)
        )

        self.assertEqual(list(projects), ["RPT"])

    def test_exclude_outer_field_comparison_with_empty_composite_subquery(self):
        missing_project = Project.objects.filter(pk=-1).values("pk", "code")
        projects = (
            Project.objects.alias(project_info=missing_project)
            .exclude(pk=F("project_info__pk"), title="Authentication")
            .order_by("pk")
            .values_list("code", flat=True)
        )

        self.assertEqual(list(projects), ["AUTH", "RPT"])

    def test_exclude_wrapped_field_from_empty_composite_subquery(self):
        missing_user = User.objects.filter(pk=-1).values("age", "email")
        users = (
            User.objects.alias(user_info=missing_user)
            .exclude(age=F("user_info__age") + 1)
            .order_by("pk")
            .values_list("name", flat=True)
        )

        self.assertEqual(list(users), ["Ada", "Bob"])

    def test_exclude_outer_field_comparison_with_composite_subquery(self):
        project_info = Project.objects.filter(pk=self.auth.pk).values("pk", "code")
        projects = (
            Project.objects.alias(project_info=project_info)
            .exclude(pk=F("project_info__pk"), title="Authentication")
            .order_by("pk")
            .values_list("code", flat=True)
        )

        self.assertEqual(list(projects), ["RPT"])

    def test_single_column_subquery_keeps_scalar_behavior(self):
        first_title = (
            Post.objects.filter(user=self.ada).order_by("pk").values("title")[:1]
        )
        profile = (
            User.objects.filter(pk=self.ada.pk)
            .annotate(first_title=first_title)
            .values("name", "first_title")
        )

        self.assertEqual(
            list(profile),
            [{"name": "Ada", "first_title": "Welcome"}],
        )
        self.assertNotIn("JOIN (", str(profile.query))

    def test_single_column_subquery_alias_allows_lookup_separator(self):
        first_title = (
            Post.objects.filter(user=self.ada).order_by("pk").values("title")[:1]
        )
        profile = (
            User.objects.filter(pk=self.ada.pk)
            .alias(**{"first__title": first_title})
            .annotate(first_title=F("first__title"))
            .values("name", "first_title")
        )

        self.assertEqual(
            list(profile),
            [{"name": "Ada", "first_title": "Welcome"}],
        )

    def test_composite_subquery_annotation_not_supported(self):
        first_post = (
            Post.objects.filter(user=self.ada)
            .order_by("pk")
            .values("title", "body")[:1]
        )
        profile = User.objects.filter(pk=self.ada.pk).annotate(info=first_post)

        msg = "Selecting a multi-column subquery as an annotation is not supported."
        with self.assertRaisesMessage(NotImplementedError, msg):
            list(profile)

    def test_composite_subquery_alias_whole_annotation_not_supported(self):
        first_post = (
            Post.objects.filter(user=self.ada)
            .order_by("pk")
            .values("title", "body")[:1]
        )
        profile = (
            User.objects.filter(pk=self.ada.pk)
            .alias(info=first_post)
            .annotate(info=F("info"))
        )

        msg = "Selecting a multi-column subquery as an annotation is not supported."
        with self.assertRaisesMessage(NotImplementedError, msg):
            list(profile)

    def test_composite_subquery_alias_whole_expression_not_supported(self):
        first_post = (
            Post.objects.filter(user=self.ada)
            .order_by("pk")
            .values("title", "body")[:1]
        )

        msg = "Upper expression does not support composite expressions."
        with self.assertRaisesMessage(ValueError, msg):
            User.objects.alias(info=first_post).annotate(value=Upper(F("info")))

    def test_composite_subquery_alias_rejects_lookup_separator(self):
        first_post = (
            Post.objects.filter(user=self.ada)
            .order_by("pk")
            .values("title", "body")[:1]
        )

        msg = (
            "Multi-column subquery alias 'first__post' cannot contain the lookup "
            "separator '__'."
        )
        with self.assertRaisesMessage(ValueError, msg):
            User.objects.alias(**{"first__post": first_post})

    def test_composite_subquery_alias_direct_fields(self):
        first_post = (
            Post.objects.filter(user=self.ada)
            .order_by("pk")
            .values("title", "body")[:1]
        )

        profile = (
            User.objects.filter(pk=self.ada.pk)
            .alias(first_post=first_post)
            .values("name", "first_post__title", "first_post__body")
        )

        self.assertEqual(
            list(profile),
            [
                {
                    "name": "Ada",
                    "first_post__title": "Welcome",
                    "first_post__body": "Hello",
                }
            ],
        )

    def test_composite_subquery_alias_filter(self):
        project = self.auth
        highest_priority_bug = (
            BugReport.objects.filter(task__project=project)
            .order_by("-severity_level", "pk")
            .values("description", "severity_level")[:1]
        )

        projects = (
            Project.objects.filter(pk=project.pk)
            .alias(priority_bug=highest_priority_bug)
            .filter(priority_bug__severity_level__gte=3)
            .values(
                "code",
                "priority_bug__description",
                "priority_bug__severity_level",
            )
        )

        self.assertEqual(
            list(projects),
            [
                {
                    "code": "AUTH",
                    "priority_bug__description": "Login crash",
                    "priority_bug__severity_level": 3,
                }
            ],
        )

    def test_composite_subquery_alias_outer_field_comparison(self):
        ranked_posts = Post.objects.annotate(
            rank=models.Case(
                models.When(user=self.ada, then=2),
                default=1,
                output_field=models.IntegerField(),
            )
        ).values("pk", "rank")
        posts = (
            Post.objects.alias(ranked=ranked_posts)
            .filter(pk__in=F("ranked__pk"))
            .annotate(rank=F("ranked__rank"))
            .order_by("-ranked__rank", "pk")
            .values_list("pk", "rank")
        )

        self.assertQuerySetEqual(
            posts,
            [
                (self.welcome_post.pk, 2),
                (self.duplicate_welcome_post.pk, 1),
            ],
        )

    def test_composite_subquery_alias_preserves_outer_row_when_inner_is_empty(self):
        project = self.auth
        critical_bug = (
            BugReport.objects.filter(
                task__project=project,
                severity_level__gte=4,
            )
            .order_by("-severity_level", "pk")
            .values("description", "severity_level")[:1]
        )

        projects = (
            Project.objects.filter(pk=project.pk)
            .alias(critical_bug=critical_bug)
            .values(
                "code",
                "critical_bug__description",
                "critical_bug__severity_level",
            )
        )
        self.assertEqual(
            list(projects),
            [
                {
                    "code": "AUTH",
                    "critical_bug__description": (
                        ""
                        if connection.features.interprets_empty_strings_as_nulls
                        else None
                    ),
                    "critical_bug__severity_level": None,
                }
            ],
        )

    def test_composite_subquery_alias_implicit_exact_filter(self):
        first_post = (
            Post.objects.filter(user=self.ada)
            .order_by("pk")
            .values("title", "body")[:1]
        )
        profile = User.objects.filter(pk=self.ada.pk).alias(first_post=first_post)

        self.assertEqual(
            list(
                profile.filter(first_post__title="Welcome").values(
                    "name", "first_post__title"
                )
            ),
            [{"name": "Ada", "first_post__title": "Welcome"}],
        )
        self.assertEqual(
            list(profile.filter(first_post__title="Missing post")),
            [],
        )

    def test_composite_subquery_alias_reuses_join(self):
        project = self.auth
        highest_priority_bug = (
            BugReport.objects.filter(task__project=project)
            .order_by("-severity_level", "pk")
            .values("description", "severity_level")[:1]
        )
        projects = (
            Project.objects.filter(pk=project.pk)
            .alias(priority_bug=highest_priority_bug)
            .filter(priority_bug__severity_level__gte=3)
            .values(
                "priority_bug__description",
                "priority_bug__severity_level",
            )
        )

        sql = str(projects.query)
        self.assertEqual(
            sql.lower().count(BugReport._meta.db_table.lower()),
            1,
        )

    def test_composite_subquery_alias_inner_ordering(self):
        project = self.auth
        BugReport.objects.create(
            task=self.login,
            reporter=self.bob,
            description="Account takeover",
            severity_level=5,
        )
        highest_priority_bug = (
            BugReport.objects.filter(task__project=project)
            .order_by("-severity_level", "pk")
            .values("description", "severity_level")[:1]
        )
        projects = (
            Project.objects.filter(pk=project.pk)
            .alias(priority_bug=highest_priority_bug)
            .values(
                "code",
                "priority_bug__description",
                "priority_bug__severity_level",
            )
        )

        self.assertQuerySetEqual(
            projects,
            [5],
            transform=itemgetter("priority_bug__severity_level"),
        )

    def test_composite_subquery_alias_outer_ordering(self):
        project = self.auth
        BugReport.objects.create(
            task=self.login,
            reporter=self.bob,
            description="Minor alignment issue",
            severity_level=1,
        )
        project_bugs = BugReport.objects.filter(task__project=project).values(
            "description", "severity_level"
        )
        projects_with_ordering_column = (
            Project.objects.filter(pk=project.pk)
            .alias(project_bug=project_bugs)
            .order_by("-project_bug__severity_level")
            .values(
                "code",
                "project_bug__description",
                "project_bug__severity_level",
            )
        )

        self.assertQuerySetEqual(
            projects_with_ordering_column,
            [3, 1],
            transform=itemgetter("project_bug__severity_level"),
        )

        projects_without_ordering_column = (
            Project.objects.filter(pk=project.pk)
            .alias(project_bug=project_bugs)
            .order_by("-project_bug__severity_level")
            .values(
                "code",
                "project_bug__description",
            )
        )

        self.assertQuerySetEqual(
            projects_without_ordering_column,
            ["Login crash", "Minor alignment issue"],
            transform=itemgetter("project_bug__description"),
        )

        # Keep the derived-table join used for ordering even when none of its
        # columns are selected.
        projects_without_derived_columns = (
            Project.objects.filter(pk=project.pk)
            .alias(project_bug=project_bugs)
            .order_by("-project_bug__severity_level")
            .values("code")
        )
        self.assertQuerySetEqual(
            projects_without_derived_columns,
            ["AUTH", "AUTH"],
            transform=itemgetter("code"),
        )

    def test_composite_subquery_alias_tuple_ordering(self):
        BugReport.objects.bulk_create(
            [
                BugReport(
                    task=self.login,
                    reporter=self.bob,
                    description="Account takeover",
                    severity_level=3,
                ),
                BugReport(
                    task=self.login,
                    reporter=self.bob,
                    description="Minor alignment issue",
                    severity_level=1,
                ),
            ]
        )
        project_bugs = BugReport.objects.filter(task__project=self.auth).values(
            "severity_level", "description"
        )
        projects = Project.objects.filter(pk=self.auth.pk).alias(
            project_bug=project_bugs
        )
        expected = [
            (1, "Minor alignment issue"),
            (3, "Account takeover"),
            (3, "Login crash"),
        ]

        for ordering in ("project_bug", F("project_bug")):
            with self.subTest(ordering=ordering):
                self.assertSequenceEqual(
                    list(
                        projects.order_by(ordering).values_list(
                            "project_bug__severity_level",
                            "project_bug__description",
                        )
                    ),
                    expected,
                )

    def test_composite_subquery_alias_preserves_distinct_select_list(self):
        organization = self.acme
        Post.objects.create(
            user=self.bob,
            title="Welcome",
            body="Updated hello",
        )
        post_templates = (
            Post.objects.filter(user__organization=organization)
            .values("title", "body")
            .distinct()
        )
        organizations = (
            Organization.objects.filter(pk=organization.pk)
            .alias(post_template=post_templates)
            .values("slug", "post_template__title")
        )

        self.assertQuerySetEqual(
            organizations,
            ["Welcome", "Welcome"],
            transform=itemgetter("post_template__title"),
            ordered=False,
        )

    def test_composite_subquery_alias_relabels_when_nested(self):
        project = self.auth
        priority_bug = (
            BugReport.objects.filter(task__project=project)
            .order_by("-severity_level", "pk")
            .values("description", "severity_level")[:1]
        )
        matching_projects = (
            Project.objects.filter(pk=project.pk)
            .alias(priority_bug=priority_bug)
            .filter(priority_bug__severity_level__gte=3)
            .values("pk")
        )
        projects = Project.objects.filter(pk__in=matching_projects).values_list(
            "code", flat=True
        )

        self.assertEqual(list(projects), ["AUTH"])

    def test_composite_subquery_alias_supports_multiple_aliases(self):
        project = self.auth
        priority_bug = (
            BugReport.objects.filter(task__project=project)
            .order_by("-severity_level", "pk")
            .values("description", "severity_level")[:1]
        )
        owner_info = User.objects.filter(pk=project.owner_id).values("name", "email")[
            :1
        ]
        projects = (
            Project.objects.filter(pk=project.pk)
            .alias(priority_bug=priority_bug, owner_info=owner_info)
            .values(
                "code",
                "priority_bug__description",
                "owner_info__name",
                "owner_info__email",
            )
        )

        self.assertEqual(
            list(projects),
            [
                {
                    "code": "AUTH",
                    "priority_bug__description": "Login crash",
                    "owner_info__name": "Ada",
                    "owner_info__email": "ada@example.com",
                }
            ],
        )

    def test_composite_subquery_alias_reuses_join_after_alias_collision(self):
        first_post = (
            Post.objects.filter(user=self.ada)
            .order_by("pk")
            .values("title", "body")[:1]
        )
        alias = User._meta.db_table
        profile = (
            User.objects.filter(pk=self.ada.pk)
            .alias(**{alias: first_post})
            .values(f"{alias}__title", f"{alias}__body")
        )

        sql = str(profile.query)
        self.assertEqual(
            sql.lower().count(Post._meta.db_table.lower()),
            1,
        )

    def test_composite_subquery_alias_does_not_replace_generated_alias(self):
        self.ada.manager = self.bob
        self.ada.save(update_fields=["manager"])
        self.bob.manager = self.ada
        self.bob.save(update_fields=["manager"])
        first_post = (
            Post.objects.filter(user=self.ada)
            .order_by("pk")
            .values("title", "body")[:1]
        )
        users = (
            User.objects.filter(manager__manager__name="Ada")
            .alias(T2=first_post)
            .filter(T2__title="Welcome")
            .values_list("name", flat=True)
        )

        self.assertEqual(list(users), ["Ada"])

    def test_composite_subquery_alias_rejects_invalid_field(self):
        first_post = Post.objects.filter(user=self.ada).values("title", "body")[:1]

        with self.assertRaises(FieldError):
            User.objects.filter(pk=self.ada.pk).alias(first_post=first_post).values(
                "first_post__does_not_exist"
            )

    def test_composite_subquery_alias_preserves_normal_field_resolution(self):
        first_post = Post.objects.filter(user=self.ada).values("title", "body")[:1]
        profile = (
            User.objects.filter(pk=self.ada.pk)
            .alias(first_post=first_post)
            .annotate(organization_slug=F("organization__slug"))
            .values("name", "organization_slug")
        )

        self.assertEqual(
            list(profile),
            [{"name": "Ada", "organization_slug": "acme"}],
        )

    def test_composite_subquery_alias_preserves_grouped_select_list(self):
        organization = self.acme
        Task.objects.create(
            project=self.auth,
            assignee=self.bob,
            name="Password reset",
            status="open",
        )
        Task.objects.create(
            project=self.auth,
            assignee=None,
            name="Two-factor rollout",
            status="blocked",
        )
        task_summary = (
            Task.objects.filter(project__workspace__organization=organization)
            .values("status")
            .annotate(total=Count("pk"))
        )
        organizations = (
            Organization.objects.filter(pk=organization.pk)
            .alias(task_summary=task_summary)
            .order_by("task_summary__status")
            .values(
                "slug",
                "task_summary__status",
                "task_summary__total",
            )
        )

        self.assertQuerySetEqual(
            organizations,
            [
                ("blocked", 1),
                ("open", 2),
            ],
            transform=itemgetter(
                "task_summary__status",
                "task_summary__total",
            ),
        )

    def test_composite_subquery_alias_direct_nested_projected_field(self):
        post_info = Post.objects.filter(pk=self.welcome_post.pk).values(
            "user__email", "title"
        )[:1]
        profile = (
            User.objects.filter(pk=self.ada.pk)
            .alias(post_info=post_info)
            .values("name", "post_info__user__email")
        )

        self.assertEqual(
            list(profile),
            [{"name": "Ada", "post_info__user__email": "ada@example.com"}],
        )

    def test_composite_subquery_alias_direct_and_nested_projected_fields(self):
        post_info = Post.objects.filter(pk=self.welcome_post.pk).values(
            "user", "user__email", "title"
        )[:1]
        profile = (
            User.objects.filter(pk=self.ada.pk)
            .alias(post_info=post_info)
            .values("post_info__user", "post_info__user__email")
        )

        self.assertEqual(
            list(profile),
            [
                {
                    "post_info__user": self.ada.pk,
                    "post_info__user__email": "ada@example.com",
                }
            ],
        )

    def test_composite_subquery_alias_values_without_fields(self):
        user_info = (
            User.objects.filter(pk=self.ada.pk)
            .annotate(post_count=Count("posts"))
            .values()
        )
        organization = (
            Organization.objects.filter(pk=self.acme.pk)
            .alias(user_info=user_info)
            .values("user_info__name", "user_info__post_count")
        )

        self.assertEqual(
            list(organization),
            [
                {
                    "user_info__name": "Ada",
                    "user_info__post_count": 1,
                }
            ],
        )

    def test_composite_subquery_alias_nested_derived_columns(self):
        post_info = Post.objects.filter(pk=self.welcome_post.pk).values(
            "title", "body"
        )[:1]
        user_info = (
            User.objects.filter(pk=self.ada.pk)
            .alias(post_info=post_info)
            .values("post_info__title", "post_info__body")
        )
        organization = (
            Organization.objects.filter(pk=self.acme.pk)
            .alias(user_info=user_info)
            .values(
                "user_info__post_info__title",
                "user_info__post_info__body",
            )
        )

        self.assertEqual(
            list(organization),
            [
                {
                    "user_info__post_info__title": "Welcome",
                    "user_info__post_info__body": "Hello",
                }
            ],
        )

    def test_composite_subquery_alias_rejects_unprojected_relation_traversal(self):
        post_info = Post.objects.filter(pk=self.welcome_post.pk).values(
            "user", "title"
        )[:1]

        with self.assertRaises(FieldError):
            User.objects.filter(pk=self.ada.pk).alias(post_info=post_info).values(
                "post_info__user__email"
            )

    def test_composite_subquery_alias_rejects_correlated_inner_query(self):
        priority_bug = BugReport.objects.filter(task__project=OuterRef("pk")).values(
            "description", "severity_level"
        )[:1]
        with self.assertRaisesMessage(
            NotImplementedError,
            "Correlated multi-column subquery aliases are not supported.",
        ):
            projects = Project.objects.alias(priority_bug=priority_bug).values(
                "code", "priority_bug__description"
            )
            list(projects)

    def test_composite_subquery_alias_update_rejects_reference(self):
        project_info = Project.objects.filter(pk=self.auth.pk).values(
            "code",
            "title",
        )
        msg = "Joined field references are not permitted in this query"

        for reference in ("project_info", "project_info__code"):
            with self.subTest(reference=reference):
                with self.assertRaisesMessage(FieldError, msg):
                    Project.objects.alias(project_info=project_info).update(
                        code=F(reference)
                    )

    def test_composite_subquery_alias_column_transform(self):
        post_info = Post.objects.filter(pk=self.welcome_post.pk).values(
            "title",
            "body",
        )

        with register_lookup(models.CharField, Upper):
            titles = (
                User.objects.filter(pk=self.ada.pk)
                .alias(post_info=post_info)
                .annotate(upper_title=F("post_info__title__upper"))
                .values_list("upper_title", flat=True)
            )

        self.assertEqual(list(titles), ["WELCOME"])


class CompositeSubqueryTupleLookupTests(CompositeSubqueryTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.higher_priority_bug = BugReport.objects.create(
            task=cls.login,
            reporter=cls.bob,
            description="Account takeover",
            severity_level=4,
        )

    def bug_tuple_subquery(self, bug_report):
        return BugReport.objects.filter(pk=bug_report.pk).values(
            "severity_level", "description"
        )[:1]

    def projects_with_priority_bug(self, *, empty=False):
        bug_reports = BugReport.objects.filter(pk=self.crash_report.pk)
        if empty:
            bug_reports = bug_reports.filter(description="Does not exist")
        priority_bug = bug_reports.values("severity_level", "description")[:1]
        return Project.objects.filter(pk=self.auth.pk).alias(priority_bug=priority_bug)

    def test_exact(self):
        projects = self.projects_with_priority_bug()

        self.assertEqual(
            list(
                projects.filter(priority_bug=(3, "Login crash")).values_list(
                    "code", flat=True
                )
            ),
            ["AUTH"],
        )
        self.assertEqual(
            list(
                projects.filter(priority_bug=(3, "Export missing rows")).values_list(
                    "code", flat=True
                )
            ),
            [],
        )

    def test_exact_subquery(self):
        projects = self.projects_with_priority_bug()
        matching_bug = self.bug_tuple_subquery(self.crash_report)
        nonmatching_bug = self.bug_tuple_subquery(self.missing_export_report)

        self.assertEqual(
            list(
                projects.filter(priority_bug=matching_bug).values_list(
                    "code", flat=True
                )
            ),
            ["AUTH"],
        )
        self.assertEqual(
            list(
                projects.filter(priority_bug=nonmatching_bug).values_list(
                    "code", flat=True
                )
            ),
            [],
        )

    def test_in(self):
        projects = self.projects_with_priority_bug()

        self.assertEqual(
            list(
                projects.filter(
                    priority_bug__in=[
                        (2, "Export missing rows"),
                        (3, "Login crash"),
                    ]
                ).values_list("code", flat=True)
            ),
            ["AUTH"],
        )
        self.assertEqual(
            list(
                projects.filter(
                    priority_bug__in=[
                        (2, "Login crash"),
                        (3, "Export missing rows"),
                    ]
                ).values_list("code", flat=True)
            ),
            [],
        )

    def test_isnull(self):
        projects = self.projects_with_priority_bug()
        projects_without_bug = self.projects_with_priority_bug(empty=True)

        self.assertEqual(
            list(
                projects.filter(priority_bug__isnull=False).values_list(
                    "code", flat=True
                )
            ),
            ["AUTH"],
        )
        self.assertEqual(
            list(
                projects.filter(priority_bug__isnull=True).values_list(
                    "code", flat=True
                )
            ),
            [],
        )
        self.assertEqual(
            list(
                projects_without_bug.filter(priority_bug__isnull=True).values_list(
                    "code", flat=True
                )
            ),
            ["AUTH"],
        )
        self.assertEqual(
            list(
                projects_without_bug.filter(priority_bug__isnull=False).values_list(
                    "code", flat=True
                )
            ),
            [],
        )

    def test_greater_than(self):
        projects = self.projects_with_priority_bug()

        self.assertEqual(
            list(
                projects.filter(priority_bug__gt=(2, "Anything")).values_list(
                    "code", flat=True
                )
            ),
            ["AUTH"],
        )
        self.assertEqual(
            list(
                projects.filter(priority_bug__gt=(4, "Anything")).values_list(
                    "code", flat=True
                )
            ),
            [],
        )

    def test_greater_than_or_equal(self):
        projects = self.projects_with_priority_bug()

        self.assertEqual(
            list(
                projects.filter(priority_bug__gte=(3, "Login crash")).values_list(
                    "code", flat=True
                )
            ),
            ["AUTH"],
        )
        self.assertEqual(
            list(
                projects.filter(priority_bug__gte=(4, "Anything")).values_list(
                    "code", flat=True
                )
            ),
            [],
        )

    def test_less_than(self):
        projects = self.projects_with_priority_bug()

        self.assertEqual(
            list(
                projects.filter(priority_bug__lt=(4, "Anything")).values_list(
                    "code", flat=True
                )
            ),
            ["AUTH"],
        )
        self.assertEqual(
            list(
                projects.filter(priority_bug__lt=(2, "Anything")).values_list(
                    "code", flat=True
                )
            ),
            [],
        )

    def test_less_than_or_equal(self):
        projects = self.projects_with_priority_bug()

        self.assertEqual(
            list(
                projects.filter(priority_bug__lte=(3, "Login crash")).values_list(
                    "code", flat=True
                )
            ),
            ["AUTH"],
        )
        self.assertEqual(
            list(
                projects.filter(priority_bug__lte=(2, "Anything")).values_list(
                    "code", flat=True
                )
            ),
            [],
        )

    @skipUnlessDBFeature("supports_tuple_comparison_against_subquery")
    def test_comparison_subqueries(self):
        lower_bug = self.missing_export_report
        equal_bug = self.crash_report
        higher_bug = self.higher_priority_bug
        test_cases = (
            ("gt", lower_bug, equal_bug),
            ("gte", equal_bug, higher_bug),
            ("lt", higher_bug, equal_bug),
            ("lte", equal_bug, lower_bug),
        )

        for lookup, matching_bug, nonmatching_bug in test_cases:
            with self.subTest(lookup=lookup):
                projects = self.projects_with_priority_bug()
                self.assertEqual(
                    list(
                        projects.filter(
                            **{
                                f"priority_bug__{lookup}": self.bug_tuple_subquery(
                                    matching_bug
                                )
                            }
                        ).values_list("code", flat=True)
                    ),
                    ["AUTH"],
                )
                self.assertEqual(
                    list(
                        projects.filter(
                            **{
                                f"priority_bug__{lookup}": self.bug_tuple_subquery(
                                    nonmatching_bug
                                )
                            }
                        ).values_list("code", flat=True)
                    ),
                    [],
                )

    def test_in_empty_list(self):
        projects = self.projects_with_priority_bug()

        self.assertEqual(
            list(projects.filter(priority_bug__in=[]).values_list("code", flat=True)),
            [],
        )

    def test_exact_rejects_incorrect_number_of_values(self):
        projects = self.projects_with_priority_bug()

        with self.assertRaisesMessage(
            ValueError,
            "'exact' lookup of ('severity_level', 'description') must have "
            "2 elements",
        ):
            projects.filter(priority_bug=(3,))

    def test_in_rejects_incorrect_number_of_values(self):
        projects = self.projects_with_priority_bug()

        with self.assertRaisesMessage(
            ValueError,
            "'in' lookup of ('severity_level', 'description') must have "
            "2 elements each",
        ):
            projects.filter(priority_bug__in=[(3,)])

    def test_in_subquery(self):
        projects = self.projects_with_priority_bug()
        matching_bugs = BugReport.objects.filter(pk=self.crash_report.pk).values(
            "severity_level", "description"
        )
        nonmatching_bugs = BugReport.objects.filter(
            pk=self.missing_export_report.pk
        ).values("severity_level", "description")

        self.assertEqual(
            list(
                projects.filter(priority_bug__in=matching_bugs).values_list(
                    "code", flat=True
                )
            ),
            ["AUTH"],
        )
        self.assertEqual(
            list(
                projects.filter(priority_bug__in=nonmatching_bugs).values_list(
                    "code", flat=True
                )
            ),
            [],
        )

    def test_exclude_exact(self):
        projects = self.projects_with_priority_bug()

        self.assertEqual(
            list(
                projects.exclude(priority_bug=(3, "Login crash")).values_list(
                    "code", flat=True
                )
            ),
            [],
        )
        self.assertEqual(
            list(
                projects.exclude(priority_bug=(3, "Export missing rows")).values_list(
                    "code", flat=True
                )
            ),
            ["AUTH"],
        )

    def test_exclude_in(self):
        projects = self.projects_with_priority_bug()

        self.assertEqual(
            list(
                projects.exclude(
                    priority_bug__in=[
                        (2, "Export missing rows"),
                        (3, "Login crash"),
                    ]
                ).values_list("code", flat=True)
            ),
            [],
        )
        self.assertEqual(
            list(
                projects.exclude(
                    priority_bug__in=[
                        (2, "Login crash"),
                        (3, "Export missing rows"),
                    ]
                ).values_list("code", flat=True)
            ),
            ["AUTH"],
        )

    def test_or_condition(self):
        projects = self.projects_with_priority_bug()

        self.assertEqual(
            list(
                projects.filter(
                    Q(priority_bug=(3, "Export missing rows"))
                    | Q(priority_bug=(3, "Login crash"))
                ).values_list("code", flat=True)
            ),
            ["AUTH"],
        )
        self.assertEqual(
            list(
                projects.filter(
                    Q(priority_bug=(2, "Login crash"))
                    | Q(priority_bug=(3, "Export missing rows"))
                ).values_list("code", flat=True)
            ),
            [],
        )

    def test_or_combined_querysets_reuses_join(self):
        projects = self.projects_with_priority_bug()
        results = (
            projects.filter(priority_bug=(3, "Login crash"))
            | projects.filter(priority_bug=(2, "Export missing rows"))
        ).values_list("code", flat=True)
        sql, _ = results.query.sql_with_params()

        self.assertEqual(sql.count("JOIN (SELECT"), 1)
        self.assertSequenceEqual(list(results), ["AUTH"])

    def test_or_combined_querysets_keeps_different_joins(self):
        login_bug = self.bug_tuple_subquery(self.crash_report)
        export_bug = self.bug_tuple_subquery(self.missing_export_report)
        login_projects = (
            Project.objects.filter(pk=self.auth.pk)
            .alias(priority_bug=login_bug)
            .filter(priority_bug=(3, "Login crash"))
        )
        export_projects = (
            Project.objects.filter(pk=self.auth.pk)
            .alias(priority_bug=export_bug)
            .filter(priority_bug=(2, "Export missing rows"))
        )

        results = (login_projects | export_projects).values_list("code", flat=True)
        sql, _ = results.query.sql_with_params()

        self.assertEqual(sql.count("JOIN (SELECT"), 2)
        self.assertSequenceEqual(list(results), ["AUTH"])

    def test_and_condition(self):
        projects = self.projects_with_priority_bug()

        self.assertEqual(
            list(
                projects.filter(
                    Q(priority_bug=(3, "Login crash"))
                    & Q(
                        priority_bug__in=[
                            (2, "Export missing rows"),
                            (3, "Login crash"),
                        ]
                    )
                ).values_list("code", flat=True)
            ),
            ["AUTH"],
        )
        self.assertEqual(
            list(
                projects.filter(
                    Q(priority_bug=(3, "Login crash"))
                    & Q(priority_bug__in=[(2, "Export missing rows")])
                ).values_list("code", flat=True)
            ),
            [],
        )

    def test_exclude_component_when_inner_is_empty(self):
        projects = self.projects_with_priority_bug(empty=True)

        self.assertEqual(
            list(
                projects.exclude(priority_bug__severity_level=3).values_list(
                    "code", flat=True
                )
            ),
            ["AUTH"],
        )

    def test_exclude_exact_when_inner_is_empty(self):
        projects = self.projects_with_priority_bug(empty=True)

        self.assertEqual(
            list(
                projects.exclude(priority_bug=(3, "Login crash")).values_list(
                    "code", flat=True
                )
            ),
            ["AUTH"],
        )

    def test_exclude_in_when_inner_is_empty(self):
        projects = self.projects_with_priority_bug(empty=True)

        self.assertEqual(
            list(
                projects.exclude(priority_bug__in=[(3, "Login crash")]).values_list(
                    "code", flat=True
                )
            ),
            ["AUTH"],
        )
