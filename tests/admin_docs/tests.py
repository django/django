from playwright_tests import AdminPlaywrightTestCase

from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase, modify_settings, override_settings


class TestDataMixin:
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username="super", password="secret", email="super@example.com"
        )


@override_settings(ROOT_URLCONF="admin_docs.urls")
@modify_settings(INSTALLED_APPS={"append": "django.contrib.admindocs"})
class AdminDocsSimpleTestCase(SimpleTestCase):
    pass


@override_settings(ROOT_URLCONF="admin_docs.urls")
@modify_settings(INSTALLED_APPS={"append": "django.contrib.admindocs"})
class AdminDocsTestCase(TestCase):
    pass


@override_settings(ROOT_URLCONF="admin_docs.urls")
@modify_settings(INSTALLED_APPS={"append": "django.contrib.admindocs"})
class AdminDocsPlaywrightTestCase(AdminPlaywrightTestCase):
    available_apps = ["admin_docs", "django.contrib.admindocs"] + (
        AdminPlaywrightTestCase.available_apps
    )

    def setUp(self):
        User.objects.create_superuser(
            username="super", password="secret", email="super@example.com"
        )
