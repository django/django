from unittest import mock

from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponse
from django.test import TestCase, override_settings
from django.urls import path, reverse

from .models import Book


class Router:
    target_db = None

    def db_for_read(self, model, **hints):
        return self.target_db

    db_for_write = db_for_read

    def allow_relation(self, obj1, obj2, **hints):
        return True


site = admin.AdminSite(name="test_adminsite")
site.register(Book)


def book(request, book_id):
    b = Book.objects.get(id=book_id)
    return HttpResponse(b.title)


urlpatterns = [
    path("admin/", site.urls),
    path("books/<book_id>/", book),
]


@override_settings(ROOT_URLCONF=__name__, DATABASE_ROUTERS=["%s.Router" % __name__])
class MultiDatabaseTests(TestCase):
    databases = {"default", "other"}
    READ_ONLY_METHODS = {"get", "options", "head", "trace"}

    @classmethod
    def setUpTestData(cls):
        cls.superusers = {}
        cls.test_book_ids = {}
        for db in cls.databases:
            Router.target_db = db
            cls.superusers[db] = User.objects.create_superuser(
                username="admin",
                password="something",
                email="test@test.org",
            )
            b = Book(name="Test Book")
            b.save(using=db)
            cls.test_book_ids[db] = b.id

    def tearDown(self):
        # Reset the routers' state between each test.
        Router.target_db = None

    @mock.patch("django.contrib.admin.options.transaction")
    def test_add_view(self, mock):
        for db in self.databases:
            with self.subTest(db=db):
                mock.mock_reset()
                Router.target_db = db
                self.client.force_login(self.superusers[db])
                response = self.client.post(
                    reverse("test_adminsite:admin_views_book_add"),
                    {"name": "Foobar: 5th edition"},
                )
                self.assertEqual(response.status_code, 302)
                self.assertEqual(
                    response.url, reverse("test_adminsite:admin_views_book_changelist")
                )
                mock.atomic.assert_called_with(using=db)

    @mock.patch("django.contrib.admin.options.transaction")
    def test_read_only_methods_add_view(self, mock):
        for db in self.databases:
            for method in self.READ_ONLY_METHODS:
                with self.subTest(db=db, method=method):
                    mock.mock_reset()
                    Router.target_db = db
                    self.client.force_login(self.superusers[db])
                    response = getattr(self.client, method)(
                        reverse("test_adminsite:admin_views_book_add"),
                    )
                    self.assertEqual(response.status_code, 200)
                    mock.atomic.assert_not_called()

    @mock.patch("django.contrib.admin.options.transaction")
    def test_change_view(self, mock):
        for db in self.databases:
            with self.subTest(db=db):
                mock.mock_reset()
                Router.target_db = db
                self.client.force_login(self.superusers[db])
                response = self.client.post(
                    reverse(
                        "test_adminsite:admin_views_book_change",
                        args=[self.test_book_ids[db]],
                    ),
                    {"name": "Test Book 2: Test more"},
                )
                self.assertEqual(response.status_code, 302)
                self.assertEqual(
                    response.url, reverse("test_adminsite:admin_views_book_changelist")
                )
                mock.atomic.assert_called_with(using=db)

    @mock.patch("django.contrib.admin.options.transaction")
    def test_read_only_methods_change_view(self, mock):
        for db in self.databases:
            for method in self.READ_ONLY_METHODS:
                with self.subTest(db=db, method=method):
                    mock.mock_reset()
                    Router.target_db = db
                    self.client.force_login(self.superusers[db])
                    response = getattr(self.client, method)(
                        reverse(
                            "test_adminsite:admin_views_book_change",
                            args=[self.test_book_ids[db]],
                        ),
                        data={"name": "Test Book 2: Test more"},
                    )
                    self.assertEqual(response.status_code, 200)
                    mock.atomic.assert_not_called()

    @mock.patch("django.contrib.admin.options.transaction")
    def test_delete_view(self, mock):
        for db in self.databases:
            with self.subTest(db=db):
                mock.mock_reset()
                Router.target_db = db
                self.client.force_login(self.superusers[db])
                response = self.client.post(
                    reverse(
                        "test_adminsite:admin_views_book_delete",
                        args=[self.test_book_ids[db]],
                    ),
                    {"post": "yes"},
                )
                self.assertEqual(response.status_code, 302)
                self.assertEqual(
                    response.url, reverse("test_adminsite:admin_views_book_changelist")
                )
                mock.atomic.assert_called_with(using=db)

    @mock.patch("django.contrib.admin.options.transaction")
    def test_read_only_methods_delete_view(self, mock):
        for db in self.databases:
            for method in self.READ_ONLY_METHODS:
                with self.subTest(db=db, method=method):
                    mock.mock_reset()
                    Router.target_db = db
                    self.client.force_login(self.superusers[db])
                    response = getattr(self.client, method)(
                        reverse(
                            "test_adminsite:admin_views_book_delete",
                            args=[self.test_book_ids[db]],
                        )
                    )
                    self.assertEqual(response.status_code, 200)
                    mock.atomic.assert_not_called()


class ViewOnSiteRouter:
    def db_for_read(self, model, instance=None, **hints):
        if model._meta.app_label in {"auth", "sessions", "contenttypes"}:
            return "default"
        return "other"

    def db_for_write(self, model, **hints):
        if model._meta.app_label in {"auth", "sessions", "contenttypes"}:
            return "default"
        return "other"

    def allow_relation(self, obj1, obj2, **hints):
        return obj1._state.db in {"default", "other"} and obj2._state.db in {
            "default",
            "other",
        }

    def allow_migrate(self, db, app_label, **hints):
        return True


@override_settings(ROOT_URLCONF=__name__, DATABASE_ROUTERS=[ViewOnSiteRouter()])
class ViewOnSiteTests(TestCase):
    databases = {"default", "other"}

    def test_contenttype_in_separate_db(self):
        ContentType.objects.using("other").all().delete()
        book = Book.objects.using("other").create(name="other book")
        user = User.objects.create_superuser(
            username="super", password="secret", email="super@example.com"
        )

        book_type = ContentType.objects.get(app_label="admin_views", model="book")

        self.client.force_login(user)

        shortcut_url = reverse("admin:view_on_site", args=(book_type.pk, book.id))
        response = self.client.get(shortcut_url, follow=False)
        self.assertEqual(response.status_code, 302)
        self.assertRegex(
            response.url, f"http://(testserver|example.com)/books/{book.id}/"
        )
