from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Book


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

    def test_breadcrumbs_object_string_truncatechars_boundary(self):
        base_breadcrumbs = (
            '<ol class="breadcrumbs">'
            '<li><a href="/test_admin/admin/">Home</a></li>'
            '<li><a href="/test_admin/admin/admin_views/">Admin_Views</a></li>'
            '<li><a href="/test_admin/admin/admin_views/book/">Books</a></li>'
            '<li aria-current="page">%s</li></ol>'
        )
        cases = [
            (
                (
                    "The cat held the gold key tightly, "
                    "unaware it would unlock a door to real world."
                ),
                80,
                (
                    "The cat held the gold key tightly, "
                    "unaware it would unlock a door to real world."
                ),
            ),
            (
                (
                    "The lion held the gold key tightly, "
                    "unaware it would unlock a door to real world."
                ),
                81,
                (
                    "The lion held the gold key tightly, "
                    "unaware it would unlock a door to real worl…"
                ),
            ),
        ]
        for value, length, expected in cases:
            with self.subTest(length=length):
                book = Book.objects.create(name=value)
                url = reverse("admin:admin_views_book_change", args=(book.pk,))
                response = self.client.get(url)
                self.assertContains(response, base_breadcrumbs % expected, html=True)
