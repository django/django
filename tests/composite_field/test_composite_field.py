from django.core.exceptions import FieldError
from django.db import NotSupportedError
from django.db.models import Count, F, OuterRef
from django.test import TestCase

from .models import BugReport, Organization, Post, Project, Task, User
from .utils import create_composite_test_data


class CompositeFieldTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.data = create_composite_test_data()

    def setUp(self):
        self.user1 = self.data.users.ada

    def test_composite_subquery_alias_direct_fields(self):
        first_post = (
            Post.objects.filter(user=self.user1)
            .order_by("pk")
            .values("title", "body")[:1]
        )

        profile = (
            User.objects.filter(pk=self.user1.pk)
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
        project = self.data.projects.auth
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

    def test_composite_subquery_alias_preserves_outer_row_when_inner_is_empty(self):
        project = self.data.projects.auth
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
                    "critical_bug__description": None,
                    "critical_bug__severity_level": None,
                }
            ],
        )

    def test_composite_subquery_alias_implicit_exact_filter(self):
        first_post = (
            Post.objects.filter(user=self.user1)
            .order_by("pk")
            .values("title", "body")[:1]
        )
        profile = User.objects.filter(pk=self.user1.pk).alias(first_post=first_post)

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
        project = self.data.projects.auth
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
        self.assertEqual(sql.count(BugReport._meta.db_table), 1)

    def test_composite_subquery_alias_inner_ordering(self):
        project = self.data.projects.auth
        BugReport.objects.create(
            task=self.data.tasks.login,
            reporter=self.data.users.cy,
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

        self.assertEqual(
            list(projects),
            [
                {
                    "code": "AUTH",
                    "priority_bug__description": "Account takeover",
                    "priority_bug__severity_level": 5,
                }
            ],
        )

    def test_composite_subquery_alias_outer_ordering(self):
        project = self.data.projects.auth
        BugReport.objects.create(
            task=self.data.tasks.login,
            reporter=self.data.users.bob,
            description="Minor alignment issue",
            severity_level=1,
        )
        project_bugs = BugReport.objects.filter(task__project=project).values(
            "description", "severity_level"
        )
        projects_1 = (
            Project.objects.filter(pk=project.pk)
            .alias(project_bug=project_bugs)
            .order_by("-project_bug__severity_level")
            .values(
                "code",
                "project_bug__description",
                "project_bug__severity_level",
            )
        )

        self.assertEqual(
            list(projects_1),
            [
                {
                    "code": "AUTH",
                    "project_bug__description": "Login crash",
                    "project_bug__severity_level": 3,
                },
                {
                    "code": "AUTH",
                    "project_bug__description": "Minor alignment issue",
                    "project_bug__severity_level": 1,
                },
            ],
        )

        projects_2 = (
            Project.objects.filter(pk=project.pk)
            .alias(project_bug=project_bugs)
            .order_by("-project_bug__severity_level")
            .values(
                "code",
                "project_bug__description",
            )
        )

        self.assertEqual(
            list(projects_2),
            [
                {
                    "code": "AUTH",
                    "project_bug__description": "Login crash",
                },
                {
                    "code": "AUTH",
                    "project_bug__description": "Minor alignment issue",
                },
            ],
        )

        project_3 = (
            Project.objects.filter(pk=project.pk)
            .alias(
                project_bug=project_bugs,
            )
            .order_by(
                "-project_bug__severity_level",
            )
            .values("code")
        )
        self.assertEqual(
            list(project_3),
            [
                {
                    "code": "AUTH",
                },
                {
                    "code": "AUTH",
                },
            ],
        )

    def test_composite_subquery_alias_preserves_distinct_select_list(self):
        organization = self.data.organizations.acme
        Post.objects.create(
            user=self.data.users.bob,
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

        self.assertEqual(
            list(organizations),
            [
                {
                    "slug": "acme",
                    "post_template__title": "Welcome",
                },
                {
                    "slug": "acme",
                    "post_template__title": "Welcome",
                },
            ],
        )

    def test_composite_subquery_alias_relabels_when_nested(self):
        project = self.data.projects.auth
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
        project = self.data.projects.auth
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
            Post.objects.filter(user=self.user1)
            .order_by("pk")
            .values("title", "body")[:1]
        )
        alias = User._meta.db_table
        profile = (
            User.objects.filter(pk=self.user1.pk)
            .alias(**{alias: first_post})
            .values(f"{alias}__title", f"{alias}__body")
        )

        sql = str(profile.query)
        self.assertEqual(sql.count(Post._meta.db_table), 1)

    def test_composite_subquery_alias_rejects_invalid_field(self):
        first_post = Post.objects.filter(user=self.user1).values("title", "body")[:1]

        with self.assertRaises(FieldError):
            User.objects.filter(pk=self.user1.pk).alias(first_post=first_post).values(
                "first_post__does_not_exist"
            )

    def test_composite_subquery_alias_preserves_normal_field_resolution(self):
        first_post = Post.objects.filter(user=self.user1).values("title", "body")[:1]
        profile = (
            User.objects.filter(pk=self.user1.pk)
            .alias(first_post=first_post)
            .annotate(organization_slug=F("organization__slug"))
            .values("name", "organization_slug")
        )

        self.assertEqual(
            list(profile),
            [{"name": "Ada", "organization_slug": "acme"}],
        )

    def test_composite_subquery_alias_preserves_grouped_select_list(self):
        organization = self.data.organizations.acme
        Task.objects.create(
            project=self.data.projects.auth,
            assignee=self.data.users.bob,
            name="Password reset",
            status="open",
        )
        Task.objects.create(
            project=self.data.projects.auth,
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

        self.assertEqual(
            list(organizations),
            [
                {
                    "slug": "acme",
                    "task_summary__status": "blocked",
                    "task_summary__total": 1,
                },
                {
                    "slug": "acme",
                    "task_summary__status": "open",
                    "task_summary__total": 2,
                },
            ],
        )

    def test_composite_subquery_alias_direct_nested_projected_field(self):
        post_info = Post.objects.filter(pk=self.data.posts.welcome.pk).values(
            "user__email", "title"
        )[:1]
        profile = (
            User.objects.filter(pk=self.user1.pk)
            .alias(post_info=post_info)
            .values("name", "post_info__user__email")
        )

        self.assertEqual(
            list(profile),
            [{"name": "Ada", "post_info__user__email": "ada@example.com"}],
        )

    def test_composite_subquery_alias_rejects_unprojected_relation_traversal(self):
        post_info = Post.objects.filter(pk=self.data.posts.welcome.pk).values(
            "user", "title"
        )[:1]

        with self.assertRaises(FieldError):
            User.objects.filter(pk=self.user1.pk).alias(post_info=post_info).values(
                "post_info__user__email"
            )

    def test_composite_subquery_alias_rejects_correlated_inner_query(self):
        priority_bug = BugReport.objects.filter(task__project=OuterRef("pk")).values(
            "description", "severity_level"
        )[:1]
        with self.assertRaisesMessage(
            NotSupportedError,
            "Correlated multi-column subquery aliases are not supported.",
        ):
            projects = Project.objects.alias(priority_bug=priority_bug).values(
                "code", "priority_bug__description"
            )
            list(projects)
