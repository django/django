from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import CoverLetter


@override_settings(ROOT_URLCONF="admin_views.urls")
class AdminBreadcrumbsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username="super",
            password="secret",
            email="super@example.com",
        )

    def setUp(self):
        self.client.force_login(self.superuser)

    def test_breadcrumbs_absent(self):
        response = self.client.get(reverse("admin:index"))
        self.assertNotContains(response, '<nav aria-label="Breadcrumbs">')

    def test_breadcrumbs_present(self):
        response = self.client.get(reverse("admin:auth_user_add"))
        self.assertContains(response, '<nav aria-label="Breadcrumbs">')
        response = self.client.get(
            reverse("admin:app_list", kwargs={"app_label": "auth"})
        )
        self.assertContains(response, '<nav aria-label="Breadcrumbs">')

    def test_module_name_for_changelist_breadcrumb(self):
        """
        Views that link to the changelist in breadcrumbs provide module_name,
        the capitalized verbose_name_plural. The changelist view keeps the
        uncapitalized name for the action-selection sentence.
        """
        cover_letter = CoverLetter.objects.create(author="Django")
        changelist_url = reverse("admin:admin_views_coverletter_changelist")
        breadcrumb = f'<a href="{changelist_url}">Cover letters</a>'
        cases = [
            reverse("admin:admin_views_coverletter_add"),
            reverse("admin:admin_views_coverletter_change", args=(cover_letter.pk,)),
            reverse("admin:admin_views_coverletter_delete", args=(cover_letter.pk,)),
            reverse("admin:admin_views_coverletter_history", args=(cover_letter.pk,)),
        ]
        for url in cases:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.context["module_name"], "Cover letters")
                self.assertContains(response, breadcrumb, html=True)

        response = self.client.post(
            changelist_url,
            {
                ACTION_CHECKBOX_NAME: [cover_letter.pk],
                "action": "delete_selected",
                "index": 0,
            },
        )
        self.assertEqual(response.context["module_name"], "Cover letters")
        self.assertContains(response, breadcrumb, html=True)

        response = self.client.get(
            reverse("admin:auth_user_password_change", args=(self.superuser.pk,))
        )
        user_changelist_url = reverse("admin:auth_user_changelist")
        self.assertEqual(response.context["module_name"], "Users")
        self.assertContains(
            response,
            f'<a href="{user_changelist_url}">Users</a>',
            html=True,
        )

        response = self.client.get(changelist_url)
        self.assertEqual(response.context["module_name"], "cover letters")
        self.assertContains(
            response,
            '<li aria-current="page">Cover letters</li>',
            html=True,
        )
