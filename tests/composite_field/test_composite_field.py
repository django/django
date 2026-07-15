from django.test import TestCase

from .models import User
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
 
