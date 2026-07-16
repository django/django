from django.test import TestCase

from .models import BugReport, Post, Project, User
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
