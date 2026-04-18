from unittest import mock

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import path, reverse


class Router:
    target_db = None

    def db_for_read(self, model, **hints):
        return self.target_db

    db_for_write = db_for_read

    def allow_relation(self, obj1, obj2, **hints):
        return True


site = admin.AdminSite(name="test_adminsite")
site.register(User, admin_class=UserAdmin)

urlpatterns = [
    path("admin/", site.urls),
]


@override_settings(ROOT_URLCONF=__name__, DATABASE_ROUTERS=["%s.Router" % __name__])
class MultiDatabaseTests(TestCase):
    databases = {"default", "other"}
    READ_ONLY_METHODS = {"get", "options", "head", "trace"}

    @classmethod
    def setUpTestData(cls):
        cls.superusers = {}
        for db in cls.databases:
            Router.target_db = db
            cls.superusers[db] = User.objects.create_superuser(
                username="admin",
                password="something",
                email="test@test.org",
            )

    def tearDown(self):
        # Reset the routers' state between each test.
        Router.target_db = None

    @mock.patch("django.contrib.auth.admin.transaction")
    def test_add_view(self, mock):
        for db in self.databases:
            with self.subTest(db_connection=db):
                Router.target_db = db
                self.client.force_login(self.superusers[db])
                response = self.client.post(
                    reverse("test_adminsite:auth_user_add"),
                    {
                        "username": "some_user",
                        "password1": "helloworld",
                        "password2": "helloworld",
                    },
                )
                self.assertEqual(response.status_code, 302)
                mock.atomic.assert_called_with(using=db)

    @mock.patch("django.contrib.auth.admin.transaction")
    def test_read_only_methods_add_view(self, mock):
        for db in self.databases:
            for method in self.READ_ONLY_METHODS:
                with self.subTest(db_connection=db, method=method):
                    mock.mock_reset()
                    Router.target_db = db
                    self.client.force_login(self.superusers[db])
                    response = getattr(self.client, method)(
                        reverse("test_adminsite:auth_user_add")
                    )
                    self.assertEqual(response.status_code, 200)
                    mock.atomic.assert_not_called()
